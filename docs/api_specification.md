# API基本設計

文書版：1.3。[RDD](RDD.md)に基づき、Goの外部HTTP APIとPythonの業務処理・SQLModel・SQLiteを使用する。FastAPIは内部通信を担当する。React / TypeScriptからJSONで通信する。接頭辞は `/api`。現時点で `/v1` は付けない。本書は設計契約であり、エンドポイント・Swagger UIの実装は未完了。

## 1. 共通仕様

ローカル開発用の科目一覧は[バックエンドの構成](backend_architecture.md)に従い、GoがUUID検証・外部応答・業務エラーのHTTP変換を担当する。
Pythonは内部通信で結果またはエラーコードを返す。以下の学生向けAPIのURL・JSON契約は維持するが、認証・成績・卒業判定などは未実装。

IDはUUID文字列、日時はUTC ISO 8601、科目単位は正の整数。成績はS/A/B/C/D/X、未確定はresult_status=pendingかつgrade_code=null。卒業判定は `result: pass / fail`、条件別も同じ2値。エラーに成功resultを付けない。

未履修は履歴なし。未確定・不合格を修得へ加算しない。科目単位や換算規則を学生のリクエストから採用しない。本人は認証セッションから決定し、本人IDを自由に指定するパラメータは受け付けない。全個人データ・認証レスポンスにCache-Control: no-storeを返す。

### エラー形式

```json
{"detail": "選択した科目が見つかりません。科目一覧を再読み込みしてください。"}
```

画面はdetailの文字列を表示する。JSON・型・値・未知フィールドの検証失敗も日本語文字列へ正規化する。内部SQL・パスワード・他人の個人情報は出力しない。

| HTTP | 条件 |
|---|---|
| 400 | JSON構文不正、存在しない科目ID |
| 401 | 認証失敗・未認証・期限切れ。アカウントの存在を区別しない |
| 403 | 不正なOrigin・CSRF検証失敗、許可されないマスタ変更 |
| 404 | 結果IDがない、または他人の結果ID。存在を区別しない |
| 409 | 成績版競合、所属未設定、マスタ不足、未確認の換算・配分規則 |
| 415 | JSON更新のContent-Type不正 |
| 422 | フィールド・成績記号・数値・履修回次・フィルタの検証失敗 |
| 429 | 認証試行制限 |
| 500 | 予期しない障害 |
| 503 | DB・保存処理の利用不能 |

正常な成績0件は200、修得0・判定fail。設定・算入規則エラーをfailへ読み替えない。現在の設定不足であっても、保存済み過去結果を読める場合は当時の結果を返せる。

## 2. 認証・更新保護

サーバー保存型セッションを用いる。十分なランダム値のトークンをCookieに保存し、DBにはトークンのハッシュを保持する。公開時はHttpOnly・Secure・SameSite=Lax・Path=/、同一オリジンHTTPS。ローカル開発のHTTP用Cookie設定を公開設定と分離する。

セッションの期限・失効・アカウント利用状態を各要求で検証する。ログアウトで失効させ、パスワードは平文保存せずパスワード用ハッシュ方式を使用する。旧設計のArgon2idは提案を維持し、パラメータ・期限・試行制限の運用値はQ04で決定する。自己登録・事前発行方式も未決定である。

POST/PUT/PATCH/DELETEはOriginを検証する。ログイン以外の認証済み更新はセッションに紐づくX-CSRF-Tokenを要求する。ログインにもOrigin検証を適用する。Vite開発プロキシと公開プロキシで同一オリジンを基本とする。未保存変更を判定用データとして扱わない。

## 3. API一覧

以下には全て `/api` を付ける。ログイン以外は認証必須。公開共有API・学生向けJSONファイル入出力APIは設けない。

| メソッド | パス | 役割 |
|---|---|---|
| POST | /auth/login | ログイン |
| POST | /auth/logout | セッション終了 |
| GET | /auth/session | 認証・CSRF情報取得 |
| GET | /programs | 所属・カリキュラム選択肢 |
| GET | /me | 本人プロフィール・所属・data_revision |
| PUT | /me/program | 本人の所属・カリキュラム保存 |
| GET | /categories | 本人課程の科目区分・科目群・要件の一覧 |
| GET | /courses | 科目一覧・区分・学部／学科・学期絞り込み |
| GET | /me/grades | 本人成績の全集合・data_revision |
| PUT | /me/grades | 本人成績の全集合を原子的に保存・訂正・取消 |
| GET | /me/dashboard | 最新保存データの判定概要。履歴を作成しない |
| GET | /me/graduation-requirements | 最新保存データの条件別詳細とおすすめ |
| POST | /checks | 最新保存データを判定しスナップショット保存 |
| GET | /checks | 本人の履歴一覧 |
| GET | /checks/{id} | 本人の保存済み過去結果 |

開発者の科目・要件管理はJSONシードによるCLI投入を基本とし、学生用のPOST /coursesやPOST /importは設けない。通常の学生は既知科目を選んで成績を入力する。

## 4. 認証と所属

POST /auth/loginはlogin_nameとpasswordを受け取る。ログイン識別子の正式な書式はQ04/Q06で確認し、大学アカウントとの連携であると装わない。成功200はauthenticated、本人情報、csrf_token、expires_atを返す。パスワードを返さない。

GET /auth/sessionは認証有効なら200、無効なら401。POST /auth/logoutはCSRFを確認して200 `{"authenticated": false}`。Cookieも削除する。CSRFの再取得後の再試行はログアウトや保存を無制限に繰り返さない。

GET /programsは存在する所属階層と対象カリキュラム、整備状態を返す。未整備を利用可能と表示しない。GET /meは本人の課程とdata_revisionを返す。PUT /me/programはprogram_id、curriculum_id、expected_revisionを受け、有効な組合せを検証し、200で保存後の課程・data_revisionを返す。成績を黙って削除せず、新課程の対象範囲で再計算する。既存成績に未確認の規則が必要なら判定側で409とし、入力成績を失わせない。

## 5. 科目とフィルタ

GET /coursesのクエリはcategory_id、faculty_id、department_id、semester、q。複数指定はAND。faculty/departmentは科目の開講元、categoryは本人課程での分類・既知の他学部算入先、semesterは科目の開講学期であり学生の履修実績の学期ではない。未知フィルタや不正値は422。本人課程で未確認の算入先を推測して分類しない。

返却科目はcourse_id、code、name、credits、開講元、授業形態、開講学期、本人課程での区分・科目群・種別、適用確認状態を持つ。他学部の表示では開講元分類と本人の算入先を区別する。GET /categoriesは本人課程の階層と必要値を返す。所属が未設定なら409。

## 6. 成績の入力・保存

GET /me/gradesは全成績とdata_revisionを返す。PUTは全集合を置換する。省略した履歴は取消となるため、画面は全集合を取得・編集し、削除意図と未保存変更を確認して送る。

説明用リクエスト（科目IDはマスタに存在するUUIDを使用）：

```json
{
  "expected_revision": 2,
  "grades": [
    {"course_id": "00000000-0000-4000-8000-000000000001", "attempt_no": 1, "result_status": "finalized", "grade_code": "A", "academic_year": 2026, "term_code": "first"},
    {"course_id": "00000000-0000-4000-8000-000000000002", "attempt_no": 1, "result_status": "pending", "grade_code": null, "academic_year": 2026, "term_code": "second"}
  ]
}
```

成功200は保存したgradesと更新後data_revisionを返す。expected_revision不一致なら409で全体不変。未知科目なら400、不正成績・回次重複なら422で全体不変。自学部科目以外でも既知科目の入力は保存でき、卒業への算入可否は判定側が扱う。空gradesは本人の成績全取消で、画面は意図を確認してから送る。

## 7. 最新判定と保存判定

GET /me/dashboardとGET /me/graduation-requirementsは同じ判定関数を使用し、1回の要求内は同じ成績・規則スナップショット。別要求間の更新を確認できるようdata_revisionとcurriculum_revisionを含める。GETを開くだけでcheck_resultsを追加しない。

POST /checksは `{"expected_revision": 3}` を受け、画面が最後に保存・取得した成績版と一致することを確認する。成功201でresultとUUIDのid・created_at・当時の入力と結果を返す。成績版不一致は409、計算・保存失敗なら履歴を作らずエラー。履歴保存が成功してから201を返す。

共通判定結果のフィールド：

| フィールド | 内容 |
|---|---|
| result | pass/fail |
| evaluated_at, data_revision | 計算時刻と本人成績・所属版 |
| curriculum | 課程コード・名称・規則版・根拠情報 |
| total | required_credits, earned_credits, credited_credits, shortage, result |
| categories | 科目区分の必要・実単位・算入・不足・結果 |
| requirements | 全条件のcode・name・kind・親条件・必要・実単位・算入・不足・result |
| missing_required_courses | 未修得必修のID・名前・分類・単位 |
| allocations | 選択必修超過の実単位・群算入・超過・換算先・換算値 |
| cross_faculty_credits | 実単位・対象・共通上限・算入先・算入・非算入・理由 |
| recommendations | 未修得科目・開講期・不足条件コード・推薦理由 |

ダッシュボードは概要用にtotal・categories等を返し、詳細APIは上表全体を返す。保存するresult_jsonも上表の詳細を持ち、総修得と総算入を区別する。判定のpass/failはHTTPの成功・失敗ではない。未達成でもGET200／保存201。

## 8. 過去結果

GET /checksはcreated_at降順、同時刻はid順で本人履歴を返す。limitは1〜100、既定20、offsetは非負整数とする。各項目はid、created_at、課程名、規則版、result、総必要・実単位・算入・不足を持つ。取得時の一覧は過去スナップショットを要約する。

GET /checks/{id}は所有者を確認して当時のinputとresultを200で返す。現在の成績やマスタで再計算しない。他人のID／存在しないIDは同じ404。未認証は401。共有URLや認証不要の例外を作らない。

## 9. ドキュメントと検証

外部入力検証・日本語エラー文字列・HTTPステータスはGoのpresentationに集約する。PythonはPydanticで内部通信契約を検証し、SQLModelでDB処理を行う。外部APIのOpenAPIとSwagger UIは今後整備する。Python内部サービスの/docs・/openapi.jsonは公開しない。Goのtestingで外部HTTPと内部通信クライアントを、pytestでPythonの業務処理・DBとGo／Pythonの実プロセス結合を検証する。本人認可・原子的保存・履歴不変を含む学生向けケースは[テスト仕様](test_specification.md)、起動・初期化・シードの手順は[バックエンドの構成](backend_architecture.md)と[DB設計](database_design.md)を参照する。

関連：[DB](database_design.md)、[判定](graduation_requirement_logic.md)、[画面](screen_design/student_screen_design.md)、[テスト](test_specification.md)、[未確定事項](open_questions.md)。

## ローカル確認用の実装（2026年10月11日）

ユーザー確認に基づき、ログイン実装前にCS学部の科目マスタを閲覧できる開発用経路を追加した。
`GET /api/dev/subject-list/programs` は登録済みカリキュラムの確認用一覧、
`GET /api/dev/subject-list/{curriculum_id}` は課程別科目・分類階層・開講期・原文注記を返す。
未確認カリキュラムも確認用一覧に含める。適用入学年度・確認状態・出典・原文注記はAPIのデータとして保持するが、ローカル確認画面では適用入学年度の未確認表示・出典・便覧注記の展開を表示しない。[画面設計](screen_design/student_screen_design.md)に従い、非表示の情報を確認済みの値へ置き換えない。
本人課程の設定・成績保存・卒業判定・認証を代替する経路ではない。

Goの`-subject-list-preview`は既定falseで、無効時は404。ローカル確認時だけ有効にして
127.0.0.1へバインドする。GETのみ・no-store・DBからの読取のみで、学生データは扱わない。
公開環境にはこの設定を引き継がない。学生向けの `/api/courses` 等は引き続き認証必須として実装する。
