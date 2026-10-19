# バックエンドの構成

`backend/api/`にHTTPの入口、`backend/modules/subjects/`に科目の業務処理を配置する。
Pythonの依存管理は`backend/`直下に統一し、共通設定は`backend/config/`に置く。Goの`go.mod`も`backend/`直下の一つに統一する。
Goが外部HTTPの入力検証・レスポンス・業務エラーのHTTP変換を担当し、Pythonが業務処理とDBを担当する。
現在は開発用科目一覧、ユーザー名による自己登録・復旧・ログイン、本人所属の取得・保存、学生向け科目一覧・分類、本人成績の取得・保存を実装。Pythonの卒業単位判定関数・判定API・結果画面まで実装済み。他学部の配分は明示的な科目対応表と合意した方針がある場合に対応する。判定履歴の保存と本人の履歴一覧・過去結果取得、履歴を増やさないダッシュボード概要も実装済み。対象他学部科目の転記・推薦は未完了。

卒業要件マスタは `modules/requirements/grad_checker_requirements/` に配置する。domainは条件・規則の種類、applicationはPydanticの投入契約・集合検証と追加投入のユースケース（`seed_import.py`）、infrastructureは5テーブルと投入済みデータの読取り・追加を担当する。科目マスタの契約・DBを参照できるが、科目モジュールから要件モジュールへは依存させない。`scripts/seed_requirements.py` が設定と具体実装を組み立てる。判定APIは以下の読取り専用経路を使用する。

判定も同モジュールのapplicationに置く。`evaluation_models.py`が入力スナップショットと結果の
Pydantic契約、`evaluation_context.py`がマスタ・所属・成績の検証と対象集合の展開、
`evaluation.py`が単位計算と全条件判定を担当する。科目・成績モジュールのapplication/domainを
参照できるが、DB・HTTP・設定を参照せず、既存モジュールから判定へ逆依存させない。
`EvaluationService`がUnit of Workの`read`で`SqliteEvaluationRepository`から入力を取得し、トランザクションを閉じてから判定と日時の付与を行う。
Goの`/api/me/graduation-requirements`からPythonの`/bridge/graduation-requirements`を呼び、本人はセッションからのみ決定する。概要は`GET /api/me/dashboard` → `POST /bridge/dashboard` → `EvaluationService.dashboard`。同じ取得・判定処理を使い、Pythonで総単位・区分合計・版・成績件数を要約する。Goは`EvaluationGateway`の契約と共通のHTTP検証・エラー変換を使い、概要の単位計算を持たない。
判定履歴は同モジュールの`application/check_results.py`（`CheckService`、成績版の照合と履歴の組立て）と`infrastructure/check_results.py`・`check_models.py`（`check_results`テーブル）に置く。`CheckService`がUnit of Workの一つの`write`で、`SqliteEvaluationRepository`からの入力取得、成績版の照合、判定、`SqliteCheckRepository`への保存を行う。一覧は`CheckService.list_checks`が一つの`read`で件数とページを読み、`SqliteCheckRepository`は結果JSONから要約の項目だけを取り出す。Goの`POST /api/checks`・`GET /api/checks`・`GET /api/checks/{id}`（`api/presentation/checks.go`）からPythonの`/bridge/checks`（`operation: create`とCSRF・`expected_revision`、`operation: list`と`page`の`limit`・`offset`、`operation: get`と`check_id`）を呼ぶ。
具体的な対応範囲と未確認規則の扱いは[判定ロジック](graduation_requirement_logic.md)を参照。

おすすめ科目は `application/recommendations.py` で候補・寄与条件・理由・開講期を組み立てる。`evaluation.py` は同じ計算処理で1科目修得時の算入を試算し、未確認規則や暫定配分に依存する候補を除く。DB・外部HTTPには依存しない。推薦は `EvaluationResult` の一部として履歴JSONに保存し、取得時には再生成しない。Goは推薦応答の形だけを検証する。

```text
React / Vite :5173
  → Go presentation :8000
    → applicationの取得契約
      → infrastructureのPython HTTPクライアント
        → Pythonのブリッジアダプター :8001
          → Python application → infrastructure → SQLite
```

GoがPythonの業務処理を呼ぶローカルHTTPを「ブリッジ通信」と呼ぶ。Pythonの受け口は`/bridge/*`で、`api/api_service/presentation/go_bridge_*.py`（ブリッジアダプター）に置く。Goの共通クライアントは`modules/shared/pythonbridge`。画面・外部には公開しない。

ブリッジ通信は言語間の接続手段。層の依存方向は次のように保つ。

- Goのpresentationはapplicationの取得契約に依存し、具体的なHTTPクライアントは参照しない。
- Goのinfrastructureが取得契約を実装する。`api/main.go`で両者を組み立てる。
- Pythonのapplication・domainはGo・ブリッジHTTP・外部HTTPに依存しない。
- PythonのブリッジアダプターはSessionとリポジトリを組み立て、ユースケースを呼ぶ。
- SQLModelのモデルとSQLはPythonのinfrastructureに保持する。

## 配置

```text
backend/
├── pyproject.toml / uv.lock / .python-version / .venv/  # Python共通環境
├── go.mod                            # Go共通モジュール
├── api/
│   ├── main.go               # Goの起動・依存関係の組立て
│   ├── presentation/subject_list.go   # 外部HTTPハンドラー
│   └── api_service/
│       ├── main.py                    # Pythonサービスの起動
│       └── presentation/              # ブリッジHTTPとSession管理
├── config/settings.py                # 共有設定。独立パッケージにはしない
├── modules/
│   └── subjects/
│       ├── application/subject_list.go
│       ├── infrastructure/subject_list_client.go
│       └── grad_checker_subjects/
│           ├── domain/                # 科目区分など
│           ├── application/           # ユースケース・取得契約・業務エラー
│           └── infrastructure/        # DB・JSON読み込み
├── scripts/seed_subjects.py           # 設定と科目モジュールを使うCLI
├── seeds/                            # 便覧データ
└── tests/                            # Python・Go・実プロセス結合テスト
```

Python・Goのテストは`backend/tests/`に集約する。
Goのテストは`tests`パッケージから対象パッケージの公開契約を検証する。
`subject_list_client_test.go`はブリッジ通信取得先、`subject_list_test.go`は外部HTTPハンドラーを検証する。
取得結果のモデルはPythonの既存Pydanticモデルを使用し、GoではそのJSONを取得契約で受け取る。
現在は外部成功JSONと科目モデルの形が同じため、GoのDTOを重複定義しない。
ブリッジ通信の`data`・`error`包絡形式はGoのinfrastructureで取り除き、外部には返さない。

## 依存管理

Pythonの`pyproject.toml`・`uv.lock`・`.python-version`・`.venv`は`backend/`直下の一組だけを使用する。
API・科目・共通設定の依存と開発ツールをこの共通環境で解決する。配下に個別のPythonプロジェクトやロックは作らない。
`backend-install`は`uv sync --locked --project backend`を一度実行する。

コードはAPI・業務モジュール・設定に分け、依存方向を維持する。
PythonのAPIは`api.api_service`、科目は`modules.subjects.grad_checker_subjects`、共通設定は`config`として参照する。

```text
Python: API → subjects / config
        CLI → subjects / config
Go:     API → subjects
        tests → API / subjects
```

通常の起動はリポジトリルートからTask / Makeで行う。Pythonサービスだけを起動する場合は`task backend-python-dev` / `make backend-python-dev`を使用する（127.0.0.1:8001）。
投入はリポジトリルートの`task backend-seed` / `make backend-seed`を使用する。CLIを直接実行する場合は`backend/`から`uv run --locked python -m scripts.seed_subjects --file seeds/cs_2026.json`で起動する。
APIと科目モジュールはコードの責務を分離するが、Pythonの依存バージョンや仮想環境は分離しない。

Goは`backend/go.mod`一つでAPI・科目・テストを管理する。
バックエンド直下で`go vet ./...`・`go test -race ./...`を実行でき、ローカル`require`・`replace`は不要。
現在は標準ライブラリのみのため`go.sum`は生成されない。

## 外部APIとブリッジ通信

| 外部API（Go） | Pythonへのブリッジ呼出し |
| --- | --- |
| `GET /api/health` | 呼び出さない。Goプロセスの稼働確認のみ |
| `GET /api/dev/subject-list/programs` | `POST /bridge/subject-list`、`operation: list_programs` |
| `GET /api/dev/subject-list/{curriculum_id}` | 同上、`operation: get_subject_list`と正規化済みUUID |

Goは外部UUIDを検証し、不正ならPythonを呼ばず422を返す。
既存のUUID表記（標準・ハイフンなし・波括弧付き・URN）を小文字の標準形に正規化する。
PythonのUUID型検証はブリッジ通信の契約違反を検出するためのもので、外部向けエラー仕様は持たない。

ブリッジ通信の成功はHTTP 200と`{"data": ...}`、業務エラーはHTTP 200と`{"error":{"code":"..."}}`。
これはPythonの処理結果を伝える契約で、外部向けHTTPステータスを表すものではない。
ブリッジ要求の必須引数・操作名・未知フィールドの不一致は`invalid_request`を返す。
Goは予期しないブリッジ応答のステータス・JSON・成功結果の形を502として扱う。

| Pythonの業務エラーコード | Goの外部HTTP |
| --- | --- |
| `curriculum_not_found` | 404 |
| `classification_inconsistent` | 409 |
| `subject_list_unavailable` | 503 |
| `internal_error` | 500 |
| ブリッジの契約違反・未知のコード・不正応答 | 502 |
| Pythonへの接続失敗 | 502 |
| Pythonの応答が5秒を超過 | 504 |

外部エラーの日本語`detail`、`Content-Type`、`Cache-Control: no-store`はGoが設定する。
DB例外はPythonのinfrastructureで業務エラーへ変換し、Pythonのブリッジアダプターは安定したコードだけを返す。
外部APIにはPythonのエラー文・SQL・ブリッジ通信のヘッダーを転送しない。
Goで通信を中断しても、Pythonで既に実行中のDB処理が直ちに停止することは保証しない。

## 起動と確認

Go 1.22以上の`go`・`gofmt`をPATHに用意する。Goは標準ライブラリのみを使用する。
通常の`task setup` / `make setup`後、リポジトリルートで次を実行する。

ローカル開発の待受は次の構成に統一する。

| プロセス | 待受 | 接続先 |
| --- | --- | --- |
| React / Vite | `127.0.0.1:5173` | `/api`をGoの`http://127.0.0.1:8000`へプロキシ |
| Go外部API | `127.0.0.1:8000` | Pythonの`http://127.0.0.1:8001`へブリッジHTTPで接続 |
| Pythonサービス | `127.0.0.1:8001` | SQLite。画面から直接呼び出さない |

通常の画面確認には`task dev` / `make dev`を使用する。バックエンドだけの確認には、科目一覧を無効にする`backend-dev`か、有効にする`backend-subject-list`を選ぶ。

| 用途 | Task | Make |
| --- | --- | --- |
| 画面＋Go外部API＋Pythonサービス | `task dev` | `make dev` |
| バックエンドのみ（科目一覧は無効） | `task backend-dev` | `make backend-dev` |
| バックエンドのみ（科目一覧を有効化） | `task backend-subject-list` | `make backend-subject-list` |
| Pythonサービスのみ | `task backend-python-dev` | `make backend-python-dev` |
| Go外部APIのみ（科目一覧有効） | `task go-api-dev` | `make go-api-dev` |
| Swagger UI付き画面＋Go＋Python | `task api-docs` | `make api-docs` |
| Go公開OpenAPIの再生成 | `task api-docs-build` | `make api-docs-build` |
| OpenAPI・公開契約の照合 | `task api-docs-check` | `make api-docs-check` |
| Python・Goのlint・整形状態・型 | `task backend-check` | `make backend-check` |
| Python・実プロセス結合・Goテスト | `task backend-test` | `make backend-test` |
| Goテスト（競合検出付き） | `task go-api-test` | `make go-api-test` |

`dev-go`は`dev`と同じ構成で起動する互換コマンド。
画面は http://127.0.0.1:5173 、外部APIは http://127.0.0.1:8000 。Ctrl+Cで一括終了する。
通常の`dev`は科目一覧を有効にする。Go単体の既定は無効で、`-subject-list-preview`で有効化する。
Goの設定例は、`backend/`で`go run ./api -listen 127.0.0.1:8000 -python-url http://127.0.0.1:8001 -subject-list-preview`。
単独起動の`backend-python-dev`と`go-api-dev`は別々のターミナルで実行する。片方のコマンドからもう片方のサービスは起動しない。
Pythonを直接起動して確認する場合も、`backend/`で`uv run --locked uvicorn api.api_service.main:app --host 127.0.0.1 --port 8001`と待受を明示する。ポートを省略すると8000になり、Goの待受と競合する。
Pythonサービスは127.0.0.1:8001で起動し、外部には公開しない。
Pythonの`/api`・Swagger UIは削除しており、画面はGoを介して取得する。
Goの`-api-docs`（既定false）は、埋め込んだ公開OpenAPI 3.1とSwagger UIを`/openapi.json`・`/docs`で配信する。
`api-docs`コマンドではViteがこれらの経路もGoへプロキシするため、`http://127.0.0.1:5173/docs`から通常のCookie・Origin・CSRF制約を保って操作できる。
Goの通常起動とPythonの同名経路は404。ブリッジのOpenAPIは生成・公開しない。
Swagger UIのJS/CSSは固定バージョンのCDNを利用し、仕様の外部バリデーター送信・認証情報の永続化は無効。
生成・認証操作の詳細は[README](../README.md#go公開apiのopenapiとswagger-ui)を参照する。

起動時にデータは自動投入しない。初回の卒業判定前には`backend-seed`、続けて`backend-requirements-seed`の両方を実行する。科目マスタだけでは科目表示・成績保存はできても、卒業判定は設定不足エラーになる。

卒業要件・算入規則は科目投入後に `task backend-requirements-seed` / `make backend-requirements-seed` で追加する。JSONの再生成は `backend-requirements-build`。起動時の `create_requirement_schema` はテーブル生成と既知の旧規則の改訂を行うが、空の要件テーブルへの投入はしない。[要件シード](../backend/seeds/requirements.md)も参照。
結合テストは一時DBへ投入し、Go・Pythonを実プロセスで起動して検証する。GoがPATHにない場合はスキップされる。
科目一覧URLと起動方法の変更に合わせ、フロントエンド・Task・Make・関連設計も更新する。

## 移動・削除したPythonの責務

以前の`presentation/subject_list.py`と`health.py`を削除した。
外部のUUID検証、日本語HTTPException、開発用表示の有効化判定、外部ルーター登録をGoへ移動した。
Pythonにはブリッジ通信の受付、型検証、Session管理、ユースケース実行、結果・エラーコードのシリアライズが残る。
Pythonサービスのプロセスは引き続き必要。言語を分けたことによる性能向上は未検証。

## 2026-10-11の分割後の検証

- `backend/`直下の共通Python環境を`uv sync --locked`で同期。
- Pythonの46テストが成功。科目モジュールの逆依存検査、共有設定の保存先検証、共通環境を使う実プロセス結合テスト3件を含む。
- 科目モジュールがAPI・設定・FastAPI・uvicornをimportしないことを確認。
- Goの共通モジュールの静的解析、共通テストの競合検出付き実行が成功。
- TaskとMakeのバックエンドチェックが成功。両方の共通環境同期、`task check`、フロントエンド6テスト、`task build`も成功。
- 通常の`dev`でVite → Go → Python → 一時SQLiteの4課程・科目一覧が一致（126・126・126・120科目）。422・404の応答とCtrl+Cによる3サーバー終了・ポート解放も確認。

通常の開発DBは検証に使用していない。ブラウザー操作・画面の見た目と外部OpenAPI/Swagger UIは未検証。

## アカウント認証の追加（2026-10-11）

認証モジュールは `modules/accounts/`。バックエンドは `application/auth.go` と `infrastructure/auth_client.go`、Pythonは `grad_checker_accounts/{domain,application,infrastructure}/` に配置する。外部HTTPとCookieは `api/presentation/auth.go`、ブリッジアダプターは `go_bridge_auth.py`。画面は `pages/accounts/AuthGate.tsx`、入力部品は `components/accounts/AuthForm.tsx`、状態管理は `hooks/accounts/useAuth.ts`。通信はaccountsモジュール内の取得契約を通し、アプリのcompositionで組み立てる。Pythonの入力・出力契約はPydanticを用い、dataclassは使用しない。

再現手順と認証設定は[認証の開発手順](auth_development.md)を参照する。

## 本人所属の保存

`accounts` のapplication/profile.pyにPydantic契約・リポジトリ契約・ユースケースを置き、infrastructure/profile.pyで既存students列と課程マスタを扱う。DB例外はapplication/errors/profile.pyの業務エラーへ変換する。
Python `/bridge/profile` は認証サービスでセッションを検証し、そこから得た本人IDだけをユースケースへ渡す。更新はCSRFを検証した上で、BEGIN IMMEDIATEによる組合せ検証とrevision付きUPDATEを一つのトランザクションで行う。
Goのpresentation/profile.goが学生向け `/api/programs`・`/api/me`・`/api/me/program` の入力・Origin・HTTP応答を担当し、accounts/applicationの契約を通してブリッジクライアントを呼ぶ。ブリッジのprofile包絡は外部応答で取り除く。

## 学生向け科目一覧と本人成績（2026-10-16）

| 外部API（Go） | Pythonへのブリッジ呼出し |
| --- | --- |
| `GET /api/courses` | `POST /bridge/courses`、`operation: courses`と絞り込み条件 |
| `GET /api/categories` | 同上、`operation: categories` |
| `GET /api/me/grades` | `POST /bridge/grades`、`operation: get` |
| `PUT /api/me/grades` | 同上、`operation: save`とCSRF・成績の全集合 |

科目一覧は`modules/subjects`に操作を追加した。application/course_catalog.pyが本人課程から見た科目・分類の契約と絞り込み、infrastructure/course_catalog.pyが一つの読取スナップショットでの取得を担う。科目モジュールはaccounts・gradesを参照せず、`go_bridge_courses.py`がセッションと本人所属から課程IDを決めて渡す。所属未設定は`program_not_selected`。

成績は新しい`modules/grades/`に置く。Pythonは`grad_checker_grades/{domain,application,infrastructure}/`、Goは`application/grades.go`と`infrastructure/grade_client.go`。domainが成績記号・確定状態と回次の並び、applicationがPydantic契約と全集合の検証、infrastructureが`grade_attempts`の版確認・差分置換・`students.data_revision`の加算を担う。`GradeService`が回次を検証してから、これらをUnit of WorkのBEGIN IMMEDIATEによる一つの書込みで行う。科目・学生テーブルの参照に限りinfrastructureから他モジュールのSQLModelを参照する。

Goのpresentation/courses.goとgrades.goが外部入力（クエリ・重複キー・未知フィールド・型・範囲・記号と状態の整合）を検証し、不正ならPythonを呼ばず422等を返す。回次の重複・連番・再履修の条件はPythonの業務ルールで判定し、業務エラーコードをGoが日本語detailへ変換する。

## ブリッジ通信と外部HTTPの共通化（2026-10-16）

GoからPythonを呼ぶ5つのブリッジクライアントは `modules/shared/pythonbridge` を使い、包絡形式 `{"data": ...}` / `{"error": {"code": ...}}` の解析、応答本文の上限、タイムアウト・接続失敗・形式違反の区別を共通化した。業務エラー型への変換と `data` の業務上の検証は各モジュールのinfrastructureに残す。
Goの外部ハンドラーは `api/presentation/http.go` の共通関数で、メソッド・セッションCookie・クエリ・Origin／CSRF・JSON本文を検証する。JSON更新のContent-Type不正は415、本文の上限超過は413で揃えた（所属保存は従来422だった）。成績・所属・科目で共通の業務エラーコード（未認証・CSRF不一致・更新版の競合・利用不可）は同じステータスと文言に変換する。

Pythonも同じ責務で共通化した。`modules/shared/grad_checker_shared/` に業務エラーの基底 `BusinessError` と、Unit of Work（[後述](#unit-of-workによるトランザクション境界2026-10-18)）を置く。各モジュールの業務エラーはこれを継承し、DB例外から業務エラーへの変換関数を自モジュールで渡す。共通パッケージは業務モジュール・API・設定を参照しない。
ブリッジアダプターは `go_bridge_call.py` の `respond` で `{"data": ...}` / `{"error": {"code": ...}}` を組み立て、予期しない例外は全操作で `internal_error` を返す（従来は開発用科目一覧のみで、他はFastAPIの500をGoが502として扱っていた。Goの外部ステータスは変わらない）。本人セッションの確認は `dependencies.py` の `current_identity` に集約し、変更操作のCSRF照合はaccountsの `AuthService.authorize` で行う。所属未設定（`program_not_selected`）の判定は `ProfileService.selected_curriculum` へ移した。科目分類の経路の辿り方は `grad_checker_subjects/infrastructure/classification_path.py` で開発用科目一覧と学生向け科目一覧が共有する。

## Unit of Workによるトランザクション境界（2026-10-18）

従来はリポジトリの各メソッドが`read_snapshot`・`write_transaction`でトランザクションを開いていた。Unit of Work（UoW）を導入し、トランザクション境界をapplicationのユースケースへ移した。単一のSQLiteを前提とする。

| 場所 | 責務 |
| --- | --- |
| `grad_checker_shared/application/unit_of_work.py` | `UnitOfWork`契約。`read()`は一つの読取スナップショットで変更を残さず、`write()`は正常終了でcommit・例外でロールバックする |
| `grad_checker_shared/infrastructure/unit_of_work.py` | `SqlUnitOfWork`。ブロックごとにSessionを開閉し、`read`は`BEGIN`、`write`は`BEGIN IMMEDIATE`で始める。DB例外は各モジュールが渡す関数で業務エラーへ変換する。ブロックの外でのリポジトリ利用と入れ子は`RuntimeError`にする |
| 各モジュールの`application` | `UnitOfWork`（ABC）を継承した契約で、使うリポジトリを抽象プロパティとして宣言する。ユースケースが`with uow.read():`・`with uow.write():`で範囲を決める |
| 各モジュールの`infrastructure` | `SqlUnitOfWork`と自モジュールの契約を継承し、ブロック中のSessionからリポジトリを生成する。リポジトリも契約（ABC）を継承し、commit・ロールバックを行わない |
| ブリッジアダプター・CLI | DBエンジンからUoWを生成してユースケースへ渡す |

範囲は、部分的な成功が業務上許されるかで決める。

- **広げる**: 判定履歴の作成は、所属・成績・マスタの読取り、成績版の照合、判定、保存を一つの`write`で行う。復旧コードによる再設定は、認証情報の更新と全セッションの失効を一つの`write`で行う。
- **狭める**: 成績回次の検証、パスワードのハッシュと照合、卒業判定の計算（判定履歴を除く）はブロックの外で行う。ログインは認証情報を`read`で読んでから照合し、セッション保存の`write`ではパスワードハッシュの一致を条件にして、間に行われた再設定を検出する。
- **分ける**: 認証の試行回数は操作本体と別の`write`でcommitし、後続の検証や登録が失敗しても回数を残す。

ユースケースの範囲は、メモリ上のリポジトリを持つFakeのUoWで、commitとロールバックの有無を検証する。ロック・制約・並行処理は一時SQLiteで検証する。

## 2026年10月19日の全課程・修了判定拡張

2026年度全課程の修了規則はrequirementsモジュールのapplication/completion_policy.py、大学院判定はapplication/graduate_evaluation.pyで定義する。DBモデルとJSON列はinfrastructure/models.py、本人課程へ絞るSQL読取はinfrastructure/evaluation.pyに置く。Goは回答形式・応答形・エラー変換を担当し、単位・本人申告の業務判定はPythonに保持する。出典・整備状況は[2026年度対応表](curriculum_coverage_2026.md)。
