# DB基本設計

文書版：1.4（2026年10月15日更新）。[RDD](RDD.md)に基づき、SQLModel / SQLiteを採用する。2026年10月11日に課程・カリキュラム・分類・科目・開講期・課程別科目の6テーブルとシードを実装した。認証用4テーブルと、空の旧メール認証DB向けの移行処理も実装した。2026年10月16日に成績の`grade_attempts`を追加した。同日に卒業要件・算入規則の5テーブルとCS4課程のシードを追加した。判定履歴モデルと、既存メール認証アカウントを保持する移行は今後の対象とする。全課程のマスタが既に投入済みという意味ではない。

## 1. 型と共通制約

IDは安定したUUIDをSQLiteではTEXTとして保存する。科目単位数はINTEGERかつ正の整数、要件・上限はINTEGERかつ非負。SQLModel/Pydantic側でも小数・真偽値等を整数へ暗黙変換せず検証する。SQLiteではINTEGER宣言だけに頼らず `typeof(credits) = 'integer' AND credits > 0` 相当のCHECKを実装する。

日時はUTC ISO 8601のTEXT、JSONはTEXTとして保存しアプリ側で構造検証する。外部キーを各接続で有効化する。マスタ参照の削除は原則RESTRICT。本人の成績は更新・取消可能、保存済み判定結果は通常更新しない。

## 2. テーブルと主要列

| テーブル | 主な列・制約 |
|---|---|
| academic_programs | id, code一意, faculty_name, department_name?, specialization_name?, course_name?。存在しない階層はnull |
| curricula | id, program_id FK, code一意, name, revision正整数, admission_year_from?, admission_year_to?, source_document, source_pages, verification_status（unverified/verified） |
| classifications | id, curriculum_id FK, code, name, parent_id?, level, display_order。課程内code一意、親は同課程 |
| courses | id, code一意, name, credits正整数, offering_program_id FK, teaching_type（lecture/exercise/practice/experiment/other）, teaching_type_label（原文） |
| course_offerings | id UUID PK, course_id FK, term_code, semester_order, academic_year?, source_note?。科目・学期・学年列・暦年で一意、暦年nullにも一意性を適用 |
| curriculum_courses | curriculum_id FK, course_id FK, classification_id FK, course_type（required/selective/elective）, display_order。課程・科目で一意 |
| graduation_requirements | id, curriculum_id FK, code, name, kind, required_credits, classification_id?, parent_id?, display_order, source_document, source_pages |
| requirement_scopes | id UUID PK, curriculum_id, requirement_id FK, classification_id?またはcourse_id?。対象集合を表し、片方だけを指定。課程と要件・分類・課程別科目への複合FK |
| credit_rules | id, curriculum_id FK, code, kind（selective_overflow / other_faculty）, verification_status, source_document, source_pages, source_note, unresolved_reason?, revision。同区分超過換算や他学部算入を定義 |
| credit_rule_courses | curriculum_id, rule_id FK, course_id FK, target_classification_id FK。PK(rule_id, course_id)。課程と規則・算入先への複合FK。対象科目と本人課程の算入先を明示 |
| credit_rule_limits | id, rule_id FK, limit_group_code, max_credits非負整数。複数算入先に共通の上限を1つのグループで定義 |
| students | id, login_name一意, program_id?, curriculum_id?, admission_year?, name?, data_revision非負整数, created_at |
| student_credentials | student_id PK/FK, password_hash, recovery_code_hash?, is_active, password_updated_at |
| grade_attempts | id, student_id FK, course_id FK RESTRICT, attempt_no正整数, result_status（finalized/pending）, grade_code?（S/A/B/C/D/X）, academic_year?正整数, term_code?（first/second）, updated_at。UQ(student_id, course_id, attempt_no) |
| check_results | id UUID PK, student_id FK, input_json, result_json, curriculum_code, curriculum_revision, data_revision, created_at |
| auth_sessions | id, student_id FK, token_hash一意, csrf_token_hash, created_at, last_seen_at, expires_at, revoked_at? |
| auth_attempts | key PK（操作とIP／正規化ユーザー名のハッシュ）, window_started_at, count |

`?` はnullable。login_nameは半角英数字・アンダースコアの3〜32文字を小文字に正規化したアプリ専用ユーザー名であり、大学の学籍番号やメールアドレスではない。自己登録時にstudents／student_credentialsを原子的に作成する。復旧コード原値は保存せずSHA-256ハッシュのみ保存する。コード使用時はパスワードとコードを更新し、全セッションを同じトランザクションで失効させる。新規登録では復旧コードを必ず設定する。nullable列はスキーマ移行のために許容する。旧DBの移行条件は[認証の開発手順](auth_development.md)を参照。所属未設定でもログインは可能だが、判定前に有効な課程選択が必要。

## 3. 分類と規則

科目の開講元と、本人課程での分類・種別・算入先を別管理する。科目名だけで同一視しない。分類階層は公式資料に従い、全学部へ3大分類を強制しない。課程内code、必修集合、要件集合、規則版を整合して投入する。

graduation_requirements.kindはtotal / classification_total / required_courses / selective_group / subminimum / elective_totalを基本とする。全課程の根拠照合で不足する条件種別は未確定事項として追加設計し、任意コードの実行や未知条件の無視は行わない。必要値0は個別最低値がないことを表せるが、表示のために架空の最低値を追加しない。

他学部科目の対象集合・算入先は資料照合で明示し、共通上限は合計に適用する。上限値がnull・未確認なら無制限とみなさない。超過換算と内訳最低を独立判定する。他学部の取得順・同時期の配分は `credit_rules.allocation_policy=chronological_best_fit_v1` で明示し、大学規則の確認状態とは分離する。

要件集合は、総単位→区分合計→必修／選択必修／選択、選択必修→内訳最低の親子構造とする。同一課程の親・分類参照、対象分類／科目の片方指定、非負整数、規則の確認状態と未確認理由の対応をDBでも強制する。必修集合と単位の一致・群の重複・算入先の整合性は投入時に検証する。出典と集合の意味は[要件マスタ](../backend/seeds/requirements.md)を参照。

## 4. 本人成績と保存単位

UQ(student_id, course_id, attempt_no)。grade_attempts.course_idはcoursesへ参照し、本人課程のcurriculum_coursesへの必須FKにはしない。他学部の成績を保存できるようにする。判定時は本人課程の算入規則で資格を確認する。

finalizedはgrade_codeがS/A/B/C/D/Xのいずれか、pendingはnullというCHECK。記録がない科目は未履修。成績入力を訂正・取り消せるが、単位数や分類を学生が変える列は設けない。

同じ科目の回次は1から連番で、確定した不合格（D・X）の後にだけ次の回次を置ける。この並びの検証はアプリ側の業務ルールで行い、DBでは記号・状態・回次の値域を強制する。

`PUT /api/me/grades` は本人の全成績集合の置換で、リクエストに含まれない履歴は取消となる。置換は(course_id, attempt_no)単位の差分で行い、変更した回次だけupdated_atを更新する。検証・置換・data_revision加算を1トランザクションで実行し、1件でも不正なら全体を保存しない。古いrevisionでの更新は409として再取得を要求する。所属変更も同じdata_revisionを使用し、古い画面が新所属を上書きしないようにする。

## 5. 判定スナップショット

check_resultsは本人の入力と計算済み結果を保存する。input_jsonには本人の課程・適用カリキュラム・全成績を、result_jsonには条件・必要値・科目名・分類・実単位・算入・不足・pass/fail・換算・おすすめ・根拠版を含める。

チェックは整合した成績・マスタ版から計算して入力と結果を保存し、作成後は不変とする。現在の科目・成績へのFKだけで過去表示を再構成しない。公開トークン・共有URL・第三者閲覧テーブルは設けない。UUIDを知ることは閲覧権限ではない。

## 6. 索引・読取・認可

本人データは認証したstudent_idで限定する。履歴は(student_id, created_at, id)、成績はUQ(student_id, course_id, attempt_no)、課程科目は(curriculum_id, classification_id, display_order)、開講期は(term_code, course_id)を主な索引候補とする。PK/UQと重複する索引は作らない。

ダッシュボードは保存済み成績・規則を同じ読取スナップショットで集計し、読取で履歴は作成しない。チェックの計算と保存は版の一貫性を確保するトランザクションで行う。長時間処理やSQLite競合時は成功結果を先に返さず、競合・障害を通知する。

パスワードハッシュとセッション原値はレスポンスへ出さない。セッション原値をDBに保存せずハッシュで管理する。学生は本人の所属・成績を書き込めるが、他人の成績・マスタは変更できない。

## 7. 初期投入と現在の状態

JSONシードを課程→カリキュラム→分類→科目・開講期→課程別科目→要件・規則→テストアカウントの順でコマンド1つで投入する。科目種別・授業形態・各課程の必要値・対象他学部集合・共通上限を検証し、重複投入で同一マスタを増やさない。全データ消去は通常の再投入と分けた明示的な初期化操作とする。

現在はマスタ6テーブルと追加投入CLIを実装済み。コンピュータサイエンス学部の4課程の科目131件・課程別科目498件を便覧の表から転記した。入学年度への適用は未確認のためunverified、適用年度はnullで保持する。学生・認証・復旧コード・試行制限のモデルと、本人所属の取得・保存を実装。所属保存は既存students列を使い、課程との組合せ検証とrevision条件付き更新を同一トランザクションで行う。成績は`grade_attempts`へ保存し、未知科目・版・回次の検証と差分置換・data_revision加算を同一トランザクションで行う。卒業要件・規則の5テーブルとCS4課程の要件80件・対象集合492件・規則16件・換算対象265件・共通上限4件のシードを実装。入学年度への適用は未確認。Q02は原本再確認で解決、Q09はアプリの配分方針を合意した。判定処理は実装済み、履歴モデルは未実装。

通常シードは全件の形式・参照・階層を検証し、1トランザクションで追加する。同じ内容はスキップし、既存IDの変更は拒否する。省略した既存データを削除しない。分類循環・階層levelの整合性は投入時に検証し、同課程の親／分類参照・単位数・一意性・削除RESTRICTはDBでも強制する。要件スキーマ初期化時にallocation_policy列を追加し、旧CS2026の8規則と全フィールドが一致する行だけをrevision 2へ更新する。独自に編集された行・成績・本人所属・data_revisionは変更しない。改訂後のシードは再投入できる。

セットアップはリポジトリルートの`task setup` / `make setup`を使用する。起動は[バックエンドの構成](backend_architecture.md)、投入は[転記とコードの説明](../backend/seeds/README.md)、検証は[テスト仕様](test_specification.md)を参照する。通常の起動・投入・確認にはTask / Makeを使用する。添付便覧は手動確認元とし、自動取得機能は作らない。

関連：[API](api_specification.md)、[判定](graduation_requirement_logic.md)、[テスト](test_specification.md)、[未確定事項](open_questions.md)。
