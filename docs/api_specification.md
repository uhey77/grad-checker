# API基本設計

## 1. 共通仕様

REST、JSON、接頭辞 `/api/v1`。実装コード・OpenAPI生成は次フェーズとする。全データ取得は認証セッションのstudent_idから本人を決定し、学生IDを指定するパス・クエリ・ボディを受け付けない。S00〜S03に必要なAPIだけを設け、学生向け成績更新API、管理者API、履歴詳細APIは作らない。

成功レスポンスの日時はUTCのISO 8601、IDはUUID、単位はJSON number。 `met / unmet / indeterminate` は達成/未達成/判定不能、 `earned / not_earned / pending / not_taken` は修得済み/未修得/成績未確定/未履修。course_typeはrequired/selective/elective。数値不明はnullであり0ではない。label/nameは画面表示用で、判定はcodeで行う。

S01/S03は同一の判定関数から結果を生成する。各リクエスト内は同一DBスナップショット、画面を切り替えた別リクエストはその時点の最新状態として再取得する。 `evaluated_at` は計算時刻、 `curriculum_revision` はDB版。異なる画面間の原子的スナップショット保存や自動ポーリングはMVPに追加しない。全認証関連・個人データに `Cache-Control: no-store` を返す。

### 共通エラー

```json
{
  "error": {
    "code": "SESSION_EXPIRED",
    "message": "セッションの有効期限が切れました。再度ログインしてください。",
    "details": []
  }
}
```

| HTTP | code | 使用場面 |
|---|---|---|
| 400 | INVALID_JSON | JSON構文不正 |
| 401 | INVALID_CREDENTIALS | ログイン失敗。存在しない学籍番号・誤パスワード・無効アカウントを区別しない |
| 401 | UNAUTHENTICATED / SESSION_EXPIRED | セッションなし・期限切れ・失効 |
| 403 | INVALID_ORIGIN / CSRF_FAILED | 不正なOrigin、ログアウトのCSRF失敗 |
| 404 | NOT_FOUND | 未定義のパス。他学生の存在は返さない |
| 405 | METHOD_NOT_ALLOWED | 本人用読取パスへの更新メソッド |
| 409 | DATA_INCONSISTENT | S02で安全に全科目の表示を生成できないマスタ/成績不整合 |
| 415 | UNSUPPORTED_MEDIA_TYPE | POSTのContent-Typeがapplication/json以外 |
| 422 | VALIDATION_ERROR | 型・長さ・未知のパラメータ（student_id等）の検証失敗 |
| 429 | RATE_LIMITED | ログイン試行制限。Retry-Afterを返す |
| 500 | INTERNAL_ERROR | 予期しない障害。内部詳細は返さない |
| 503 | DATABASE_UNAVAILABLE | DB接続・スナップショット取得失敗 |

detailsは公開可能なfield/codeだけ。パスワード、SQL、ハッシュ、内部例外、他学生情報を含めない。以下の各APIの「エラー」はこの形式で返す。

## 2. セッション・入力・通信の提案

ブラウザには256bit以上の暗号学的ランダムトークンをCookieで渡し、DBにはそのSHA-256だけを保存する。毎回期限・失効・アカウント利用状態を確認する。ログイン成功ごとに新しいトークンを生成し、既存Cookieのセッションがあれば失効する。提案値はアイドル30分、絶対8時間（Q04）。期限切れ、ログアウト、アカウント無効化、パスワード変更で失効させる。

公開環境は同一オリジンHTTPSを前提に `__Host-grad_session` を `HttpOnly; Secure; SameSite=Lax; Path=/`、Domainなしで設定する。ローカルHTTPのみ別名 `grad_session_dev` とSecureなしを許す。公開設定でSecureを外さない。localStorageに認証トークンを保存しない。

POSTはapplication/jsonに限定し、Originを許可したフロントエンドの完全一致で検証する（提案方式）。ログアウトではセッションに結びついたランダムCSRFトークンを `X-CSRF-Token` に送る。ログインは未認証のためCSRFトークン不要だがOrigin検証を行う。SameSite単独でCSRF防御を完結させない。GETは成績・マスタを変更しないが、セッション確認によるlast_seen更新やCSRF再発行を許す。

学籍番号は文字列、1〜32文字、前後空白除去後にASCII英数字のみ（公式書式の追加制限はQ06）。パスワードは1〜128文字、空白を含め原値を検証し切り詰めない。フィールドは学籍番号とpasswordのみ、型変換・未知フィールドを許さない。クエリは下記にないものを422で拒否する。SQLはパラメータ化し、HTMLを文字列連結で生成しない。

パスワードはArgon2id（salt自動生成、提案下限19MiB/反復2/並列1）で保存し、実測後にパラメータを確定する。不存在の学籍番号でもダミーハッシュ照合を行い、ログインエラーを統一する。試行制限はIPと学籍番号の両方で提案5回/分、実環境値はQ04で決める。

開発はVite→バックエンドへの同一オリジンプロキシを提案し、公開は同一オリジンのリバースプロキシとする。別オリジンが必要なら許可オリジン固定・credentials有効・ワイルドカード禁止を前提にQ05で確定する。プロキシ設定の実装は今回行わない。

参考：[OWASP Session Management](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html)、[OWASP Password Storage](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html)。期限・制限回数等は本設計の提案値である。

## 3. API一覧

| メソッド | パス | 概要・画面 | 認証 |
|---|---|---|---|
| POST | /auth/login | 学籍番号・パスワード認証、S00 | 不要、Origin検証 |
| POST | /auth/logout | セッション失効、共通 | 必須、CSRF検証 |
| GET | /auth/session | 認証状態・CSRF再取得、共通 | セッションを確認 |
| GET | /me | 本人プロフィール、共通 | 必須 |
| GET | /me/courses | 全科目と代表成績、S02 | 必須 |
| GET | /me/dashboard | 判定概要、S01 | 必須 |
| GET | /me/graduation-requirements | 判定詳細、S03 | 必須 |

上表のパスには全て `/api/v1` を付ける。以下の例の学生・科目コードは説明用の架空コードであり、正式学籍番号や公式科目コードではない。

## 4. POST /auth/login

リクエストボディ:

```json
{"student_number": "TEST2026001", "password": "example-only-password"}
```

200とSet-Cookieを返す。レスポンスstudentの全項目はGET /meと同じ。

```json
{
  "authenticated": true,
  "student": {
    "student_number": "TEST2026001", "name": "テスト学生A",
    "faculty": "コンピュータサイエンス学部", "specialization": "先進情報専攻",
    "course": "人工知能コース", "admission_year": 2026,
    "curriculum": {"code": "cs_ai_2026", "name": "2026年度先進情報・人工知能", "revision": 1}
  },
  "csrf_token": "example-csrf-token",
  "expires_at": "2026-10-09T17:00:00Z"
}
```

エラー: 400/403/415/422/429/500/503、認証失敗401 INVALID_CREDENTIALS。失敗時セッションを発行しない。パスワードをレスポンス・ログへ出力しない。

## 5. POST /auth/logout

認証と `X-CSRF-Token` 必須、ボディなし。200、サーバーのセッションを失効し、Cookieを同じPath属性で削除する。JSONは次のとおり。

```json
{"authenticated": false}
```

エラー: 401/403/500/503。未認証・期限切れは401としてCookieを削除し、UIはS00へ移動する。POSTにボディを送る場合はapplication/jsonの空オブジェクトのみ許可する（未知フィールドは422、構文不正400、形式不正415）。

## 6. GET /auth/session

リクエストパラメータなし。セッション有効なら200。CSRFトークンを再発行してセッション内のハッシュを更新する。既存トークン失効時のログアウト403は本APIで最新を取得して1度再試行できる。

```json
{
  "authenticated": true,
  "student_number": "TEST2026001",
  "csrf_token": "example-new-csrf-token",
  "expires_at": "2026-10-09T17:00:00Z"
}
```

セッションなし・失効・期限切れは401（共通エラー）であり、authenticated=falseの200は返さない。Cookieを削除する。エラー: 401/422/500/503。学生氏名・成績を未認証のまま返さない。

## 7. GET /me

認証必須、パラメータなし。200。

```json
{
  "student_number": "TEST2026001", "name": "テスト学生A",
  "faculty": "コンピュータサイエンス学部", "specialization": "先進情報専攻",
  "course": "人工知能コース", "admission_year": 2026,
  "curriculum": {"code": "cs_ai_2026", "name": "2026年度先進情報・人工知能", "revision": 1}
}
```

エラー: 401/422/500/503。所属・課程が不正なら409 DATA_INCONSISTENT。DBはstudents→academic_programs/curriculaを結合する。内部学生ID、パスワードハッシュは返さない。

## 8. GET /me/courses

認証必須、パラメータなし。検索・ページング・履歴詳細は追加しない。全課程科目を返す。200の例は4件の説明用カリキュラムであり、本番シードは便覧の全科目を返す。

```json
{
  "curriculum_code": "cs_ai_2026", "curriculum_revision": 1,
  "evaluated_at": "2026-10-09T09:00:00Z", "record_count": 3,
  "warnings": [],
  "courses": [
    {
      "course_id": "00000000-0000-4000-8000-000000000001", "course_code": "EX001",
      "name": "人工知能", "major": {"code": "specialized", "name": "専門教育科目"},
      "group": {"code": "core", "name": "コア科目"}, "subcategory": null,
      "course_type": "selective", "credits": 2, "grade_code": "A", "grade_display": "A",
      "earned_status": "earned", "earned_credits": 2,
      "academic_year": 2026, "term": "first", "attempt_no": 1
    },
    {
      "course_id": "00000000-0000-4000-8000-000000000002", "course_code": "EX002",
      "name": "データベース", "major": {"code": "specialized", "name": "専門教育科目"},
      "group": {"code": "core", "name": "コア科目"}, "subcategory": null,
      "course_type": "selective", "credits": 2, "grade_code": "X", "grade_display": "X",
      "earned_status": "not_earned", "earned_credits": 0,
      "academic_year": 2026, "term": "first", "attempt_no": 1
    },
    {
      "course_id": "00000000-0000-4000-8000-000000000003", "course_code": "EX003",
      "name": "自然言語処理", "major": {"code": "specialized", "name": "専門教育科目"},
      "group": {"code": "core", "name": "コア科目"}, "subcategory": null,
      "course_type": "selective", "credits": 2, "grade_code": null, "grade_display": "未確定",
      "earned_status": "pending", "earned_credits": 0,
      "academic_year": 2026, "term": "second", "attempt_no": 1
    },
    {
      "course_id": "00000000-0000-4000-8000-000000000004", "course_code": "EX004",
      "name": "データサイエンス", "major": {"code": "specialized", "name": "専門教育科目"},
      "group": {"code": "core", "name": "コア科目"}, "subcategory": null,
      "course_type": "selective", "credits": 2, "grade_code": null, "grade_display": "未履修",
      "earned_status": "not_taken", "earned_credits": 0,
      "academic_year": null, "term": null, "attempt_no": null
    }
  ]
}
```

record_countは本人の履歴レコード数（科目数とは異なる）。成績0件でもcoursesは全科目を含む。Dはgrade_code/displayがD、not_earned、earned_credits=0。Xの説明は確認済みの画面表示規則から付ける。代表履歴は[判定ロジック](graduation_requirement_logic.md)第4章に従う。

エラー: 401/409/422/500/503。Rや不正履歴は409にして黙って未履修扱いしない。S01/S03では同じ不整合を判定不能として返す。DBはcurriculum_courses→courses/classificationsを起点に本人のgrade_attemptsを対応付ける。

## 9. GET /me/dashboard

認証必須、パラメータなし。200。以下は全条件達成例（外国語の超過2を実学基礎の選択へ換算し、直接選択は6）。

```json
{
  "curriculum_code": "cs_ai_2026", "curriculum_revision": 1,
  "evaluated_at": "2026-10-09T09:00:00Z", "overall_status": "met",
  "total": {"required_credits": 124, "earned_credits": 124, "deficit_credits": 0, "status": "met"},
  "majors": [
    {"code": "practical", "kind": "elective_total", "major_code": "practical", "parent_code": null, "name": "実学基礎科目", "required_credits": 38, "earned_credits": 38, "deficit_credits": 0, "status": "met", "required_status": "met", "selective_status": "met", "elective_status": "met"},
    {"code": "foundation", "kind": "elective_total", "major_code": "foundation", "parent_code": null, "name": "専門基礎教育科目", "required_credits": 42, "earned_credits": 42, "deficit_credits": 0, "status": "met", "required_status": "met", "selective_status": "met", "elective_status": "met"},
    {"code": "specialized", "kind": "elective_total", "major_code": "specialized", "parent_code": null, "name": "専門教育科目", "required_credits": 44, "earned_credits": 44, "deficit_credits": 0, "status": "met", "required_status": "met", "selective_status": "met", "elective_status": "met"}
  ],
  "warnings": [], "issues": []
}
```

majors.statusは合計だけでなく所属する必修・選択必修・内訳・選択を全て含む判定、selective_statusには人文・社会の内訳も含める。total.statusは総単位条件だけでありoverall_statusと同一とは限らない。エラー: 401/422/500/503。マスタ/成績不整合は200でoverall_status=indeterminate、totalの数値null、majorsは取得可能な分類の枠だけ返し各数値null。取得できない枠は空配列、issuesに理由を入れる。DB障害は503であり0単位を返さない。

## 10. GET /me/graduation-requirements

認証必須、パラメータなし。200。以下は前節と同じ達成例。requirementsは常に投入された全20条件を返す。

```json
{
  "curriculum_code": "cs_ai_2026", "curriculum_revision": 1,
  "evaluated_at": "2026-10-09T09:00:00Z", "overall_status": "met",
  "requirements": [
    {"code": "total", "kind": "total", "major_code": null, "parent_code": null, "name": "総単位", "required_credits": 124, "earned_credits": 124, "credited_credits": 124, "deficit_credits": 0, "status": "met"},
    {"code": "practical_total", "kind": "major_total", "major_code": "practical", "parent_code": null, "name": "実学基礎合計", "required_credits": 38, "earned_credits": 38, "credited_credits": 38, "deficit_credits": 0, "status": "met"},
    {"code": "foundation_total", "kind": "major_total", "major_code": "foundation", "parent_code": null, "name": "専門基礎教育合計", "required_credits": 42, "earned_credits": 42, "credited_credits": 42, "deficit_credits": 0, "status": "met"},
    {"code": "specialized_total", "kind": "major_total", "major_code": "specialized", "parent_code": null, "name": "専門教育合計", "required_credits": 44, "earned_credits": 44, "credited_credits": 44, "deficit_credits": 0, "status": "met"},
    {"code": "practical_required", "kind": "required_courses", "major_code": "practical", "parent_code": null, "name": "実学基礎必修", "required_credits": 16, "earned_credits": 16, "credited_credits": 16, "deficit_credits": 0, "status": "met"},
    {"code": "foundation_required", "kind": "required_courses", "major_code": "foundation", "parent_code": null, "name": "専門基礎教育必修", "required_credits": 21, "earned_credits": 21, "credited_credits": 21, "deficit_credits": 0, "status": "met"},
    {"code": "specialized_required", "kind": "required_courses", "major_code": "specialized", "parent_code": null, "name": "専門教育必修", "required_credits": 21, "earned_credits": 21, "credited_credits": 21, "deficit_credits": 0, "status": "met"},
    {"code": "liberal_selective", "kind": "selective_group", "major_code": "practical", "parent_code": null, "name": "総合等選択必修", "required_credits": 10, "earned_credits": 10, "credited_credits": 10, "deficit_credits": 0, "status": "met"},
    {"code": "foreign_selective", "kind": "selective_group", "major_code": "practical", "parent_code": null, "name": "外国語選択必修", "required_credits": 2, "earned_credits": 4, "credited_credits": 2, "deficit_credits": 0, "status": "met"},
    {"code": "information_selective", "kind": "selective_group", "major_code": "practical", "parent_code": null, "name": "情報・数理選択必修", "required_credits": 2, "earned_credits": 2, "credited_credits": 2, "deficit_credits": 0, "status": "met"},
    {"code": "math_selective", "kind": "selective_group", "major_code": "foundation", "parent_code": null, "name": "数理選択必修", "required_credits": 4, "earned_credits": 4, "credited_credits": 4, "deficit_credits": 0, "status": "met"},
    {"code": "management_selective", "kind": "selective_group", "major_code": "foundation", "parent_code": null, "name": "マネジメント選択必修", "required_credits": 2, "earned_credits": 2, "credited_credits": 2, "deficit_credits": 0, "status": "met"},
    {"code": "computing_selective", "kind": "selective_group", "major_code": "foundation", "parent_code": null, "name": "コンピュータ・ビジネス選択必修", "required_credits": 12, "earned_credits": 12, "credited_credits": 12, "deficit_credits": 0, "status": "met"},
    {"code": "core_selective", "kind": "selective_group", "major_code": "specialized", "parent_code": null, "name": "コア選択必修", "required_credits": 12, "earned_credits": 12, "credited_credits": 12, "deficit_credits": 0, "status": "met"},
    {"code": "seminar_selective", "kind": "selective_group", "major_code": "specialized", "parent_code": null, "name": "知能専門演習選択必修", "required_credits": 3, "earned_credits": 3, "credited_credits": 3, "deficit_credits": 0, "status": "met"},
    {"code": "humanities_min", "kind": "subminimum", "major_code": "practical", "parent_code": "liberal_selective", "name": "人文内訳", "required_credits": 2, "earned_credits": 2, "credited_credits": 2, "deficit_credits": 0, "status": "met"},
    {"code": "society_min", "kind": "subminimum", "major_code": "practical", "parent_code": "liberal_selective", "name": "社会内訳", "required_credits": 2, "earned_credits": 2, "credited_credits": 2, "deficit_credits": 0, "status": "met"},
    {"code": "practical_elective", "kind": "elective_total", "major_code": "practical", "parent_code": null, "name": "実学基礎選択算入", "required_credits": 8, "earned_credits": 6, "credited_credits": 8, "deficit_credits": 0, "status": "met"},
    {"code": "foundation_elective", "kind": "elective_total", "major_code": "foundation", "parent_code": null, "name": "専門基礎教育選択算入", "required_credits": 3, "earned_credits": 3, "credited_credits": 3, "deficit_credits": 0, "status": "met"},
    {"code": "specialized_elective", "kind": "elective_total", "major_code": "specialized", "parent_code": null, "name": "専門教育選択算入", "required_credits": 8, "earned_credits": 8, "credited_credits": 8, "deficit_credits": 0, "status": "met"}
  ],
  "missing_required_courses": [],
  "allocations": [
    {"group_code": "liberal_selective", "major_code": "practical", "raw_credits": 10, "allocated_credits": 10, "excess_candidate_credits": 0, "converted_credits": 0},
    {"group_code": "foreign_selective", "major_code": "practical", "raw_credits": 4, "allocated_credits": 2, "excess_candidate_credits": 2, "converted_credits": 2},
    {"group_code": "information_selective", "major_code": "practical", "raw_credits": 2, "allocated_credits": 2, "excess_candidate_credits": 0, "converted_credits": 0},
    {"group_code": "math_selective", "major_code": "foundation", "raw_credits": 4, "allocated_credits": 4, "excess_candidate_credits": 0, "converted_credits": 0},
    {"group_code": "management_selective", "major_code": "foundation", "raw_credits": 2, "allocated_credits": 2, "excess_candidate_credits": 0, "converted_credits": 0},
    {"group_code": "computing_selective", "major_code": "foundation", "raw_credits": 12, "allocated_credits": 12, "excess_candidate_credits": 0, "converted_credits": 0},
    {"group_code": "core_selective", "major_code": "specialized", "raw_credits": 12, "allocated_credits": 12, "excess_candidate_credits": 0, "converted_credits": 0},
    {"group_code": "seminar_selective", "major_code": "specialized", "raw_credits": 3, "allocated_credits": 3, "excess_candidate_credits": 0, "converted_credits": 0}
  ],
  "unmet_requirement_codes": [], "warnings": [], "issues": []
}
```

各条件のearned_creditsはその対象の実単位（elective_totalでは直接選択のみ）、credited_creditsは配分後に条件へ算入した単位。合計行や内訳行を足し合わせない。 `kind`、 `major_code`（totalではnull）、 `parent_code`（内訳以外はnull）は同じ20コードのDBマスタから生成する。未修得必修はcourse_id、name、credits、major_codeを持つオブジェクト配列とする。

Q02の例ではliberal_selective.converted_credits=null、practical_elective.credited_credits/deficit_credits=null、status=indeterminate、humanities_minはunmet、unmet_requirement_codesにhumanities_minを含める。issuesは次の形式とする（HTTPエラーではない）。

```json
{"code": "UNRESOLVED_CONVERSION", "requirement_code": "liberal_selective", "message": "内訳未達成時の超過換算は確認が必要です。"}
```

マスタ不整合は計算結果の数値をnull、overall_status=indeterminateとし、取得できた条件だけをstatus=indeterminateで返す。欠落条件はissuesで明示し、空の必修一覧を「全必修達成」と解釈しない。エラー: 401/422/500/503。不正なマスタへの依存を表すissueはMASTER_INCONSISTENT、対象外RはUNSUPPORTED_GRADE、不正履歴はGRADE_INCONSISTENT。warningsは非致命的な表示上の注意のみで、issuesをwarningsに格下げしない。

## 11. DBと画面の対応

| データ | DB取得元・計算 | 表示 |
|---|---|---|
| 学籍番号・氏名・入学年度 | students | 共通・S01 |
| 所属・適用課程 | academic_programs、curricula | 共通・S01 |
| 全科目・科目単位 | curriculum_courses、courses | S02 |
| 大分類・科目群・小分類・種別 | classificationsの祖先、curriculum_courses | S02 |
| 成績・修得状態・年度学期 | grade_attemptsの代表履歴と算入規則 | S02 |
| 必要値・範囲・親子条件 | graduation_requirements、requirement_scopes | S03 |
| 集計・不足・換算・未修得必修 | 共通判定関数、派生値でありDB列なし | S01/S03 |

関連：[画面](screen_design/student_screen_design.md)、[DB](database_design.md)、[判定](graduation_requirement_logic.md)、[テスト](test_specification.md)、[未確定事項](open_questions.md)。
