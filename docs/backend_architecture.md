# バックエンドの構成

`backend/api/`にHTTPの入口、`backend/modules/subjects/`に科目の業務処理を配置する。
Pythonの依存管理は`backend/`直下に統一し、共通設定は`backend/config/`に置く。Goの`go.mod`も`backend/`直下の一つに統一する。
Goが外部HTTPの入力検証・レスポンス・業務エラーのHTTP変換を担当し、Pythonが業務処理とDBを担当する。
現在は開発用科目一覧、ユーザー名による自己登録・復旧・ログイン、本人所属の取得・保存、学生向け科目一覧・分類、本人成績の取得・保存を実装。卒業判定・推薦は未実装。

```text
React / Vite :5173
  → Go presentation :8000
    → applicationの取得契約
      → infrastructureのPython HTTPクライアント
        → Python内部通信アダプター :8001
          → Python application → infrastructure → SQLite
```

内部HTTPは言語間の接続手段。層の依存方向は次のように保つ。

- Goのpresentationはapplicationの取得契約に依存し、具体的なHTTPクライアントは参照しない。
- Goのinfrastructureが取得契約を実装する。`api/main.go`で両者を組み立てる。
- Pythonのapplication・domainはGo・内部HTTP・外部HTTPに依存しない。
- Pythonの内部アダプターはSessionとリポジトリを組み立て、ユースケースを呼ぶ。
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
│       ├── main.py                    # Python内部サービスの起動
│       └── presentation/              # 内部HTTPとSession管理
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
`subject_list_client_test.go`は内部通信取得先、`subject_list_test.go`は外部HTTPハンドラーを検証する。
取得結果のモデルはPythonの既存Pydanticモデルを使用し、GoではそのJSONを取得契約で受け取る。
現在は外部成功JSONと科目モデルの形が同じため、GoのDTOを重複定義しない。
内部通信の`data`・`error`包絡形式はGoのinfrastructureで取り除き、外部には返さない。

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

通常の起動はリポジトリルートからTask / Makeで行う。Python内部サービスだけを起動する場合は`task backend-python-dev` / `make backend-python-dev`を使用する（127.0.0.1:8001）。
投入はリポジトリルートの`task backend-seed` / `make backend-seed`を使用する。CLIを直接実行する場合は`backend/`から`uv run --locked python -m scripts.seed_subjects --file seeds/cs_2026.json`で起動する。
APIと科目モジュールはコードの責務を分離するが、Pythonの依存バージョンや仮想環境は分離しない。

Goは`backend/go.mod`一つでAPI・科目・テストを管理する。
バックエンド直下で`go vet ./...`・`go test -race ./...`を実行でき、ローカル`require`・`replace`は不要。
現在は標準ライブラリのみのため`go.sum`は生成されない。

## 外部APIと内部通信

| 外部API（Go） | Pythonへの内部呼出し |
| --- | --- |
| `GET /api/health` | 呼び出さない。Goプロセスの稼働確認のみ |
| `GET /api/dev/subject-list/programs` | `POST /internal/subject-list`、`operation: list_programs` |
| `GET /api/dev/subject-list/{curriculum_id}` | 同上、`operation: get_subject_list`と正規化済みUUID |

Goは外部UUIDを検証し、不正ならPythonを呼ばず422を返す。
既存のUUID表記（標準・ハイフンなし・波括弧付き・URN）を小文字の標準形に正規化する。
PythonのUUID型検証は内部通信の契約違反を検出するためのもので、外部向けエラー仕様は持たない。

内部通信の成功はHTTP 200と`{"data": ...}`、業務エラーはHTTP 200と`{"error":{"code":"..."}}`。
これは内部処理の結果を伝える契約で、外部向けHTTPステータスを表すものではない。
内部リクエストの必須引数・操作名・未知フィールドの不一致は`invalid_request`を返す。
Goは予期しない内部ステータス・JSON・成功結果の形を502として扱う。

| Pythonの業務エラーコード | Goの外部HTTP |
| --- | --- |
| `curriculum_not_found` | 404 |
| `classification_inconsistent` | 409 |
| `subject_list_unavailable` | 503 |
| `internal_error` | 500 |
| 内部契約違反・未知のコード・不正応答 | 502 |
| Pythonへの接続失敗 | 502 |
| Pythonの応答が5秒を超過 | 504 |

外部エラーの日本語`detail`、`Content-Type`、`Cache-Control: no-store`はGoが設定する。
DB例外はPythonのinfrastructureで業務エラーへ変換し、Pythonの内部アダプターは安定したコードだけを返す。
外部APIには内部エラー文・SQL・内部通信のヘッダーを転送しない。
Goで通信を中断しても、Pythonで既に実行中のDB処理が直ちに停止することは保証しない。

## 起動と確認

Go 1.22以上の`go`・`gofmt`をPATHに用意する。Goは標準ライブラリのみを使用する。
通常の`task setup` / `make setup`後、リポジトリルートで次を実行する。

ローカル開発の待受は次の構成に統一する。

| プロセス | 待受 | 接続先 |
| --- | --- | --- |
| React / Vite | `127.0.0.1:5173` | `/api`をGoの`http://127.0.0.1:8000`へプロキシ |
| Go外部API | `127.0.0.1:8000` | Pythonの`http://127.0.0.1:8001`へ内部HTTPで接続 |
| Python内部サービス | `127.0.0.1:8001` | SQLite。画面から直接呼び出さない |

通常の画面確認には`task dev` / `make dev`を使用する。バックエンドだけの確認には、科目一覧を無効にする`backend-dev`か、有効にする`backend-subject-list`を選ぶ。

| 用途 | Task | Make |
| --- | --- | --- |
| 画面＋Go外部API＋Python内部サービス | `task dev` | `make dev` |
| バックエンドのみ（科目一覧は無効） | `task backend-dev` | `make backend-dev` |
| バックエンドのみ（科目一覧を有効化） | `task backend-subject-list` | `make backend-subject-list` |
| Python内部サービスのみ | `task backend-python-dev` | `make backend-python-dev` |
| Go外部APIのみ（科目一覧有効） | `task go-api-dev` | `make go-api-dev` |
| Python・Goのlint・整形状態・型 | `task backend-check` | `make backend-check` |
| Python・実プロセス結合・Goテスト | `task backend-test` | `make backend-test` |
| Goテスト（競合検出付き） | `task go-api-test` | `make go-api-test` |

`dev-go`は`dev`と同じ構成で起動する互換コマンド。
画面は http://127.0.0.1:5173 、外部APIは http://127.0.0.1:8000 。Ctrl+Cで一括終了する。
通常の`dev`は科目一覧を有効にする。Go単体の既定は無効で、`-subject-list-preview`で有効化する。
Goの設定例は、`backend/`で`go run ./api -listen 127.0.0.1:8000 -python-url http://127.0.0.1:8001 -subject-list-preview`。
単独起動の`backend-python-dev`と`go-api-dev`は別々のターミナルで実行する。片方のコマンドからもう片方のサービスは起動しない。
Pythonを直接起動して確認する場合も、`backend/`で`uv run --locked uvicorn api.api_service.main:app --host 127.0.0.1 --port 8001`と待受を明示する。ポートを省略すると8000になり、Goの待受と競合する。
Python内部サービスは127.0.0.1:8001で起動し、外部には公開しない。
Pythonの`/api`・Swagger UIは削除しており、画面はGoを介して取得する。外部OpenAPI/Swagger UIの整備は今後実施する。

起動時にデータは自動投入しない。必要な場合だけ`backend-seed`を実行する。
結合テストは一時DBへ投入し、Go・Pythonを実プロセスで起動して検証する。GoがPATHにない場合はスキップされる。
科目一覧URLと起動方法の変更に合わせ、フロントエンド・Task・Make・関連設計も更新する。

## 移動・削除したPythonの責務

以前の`presentation/subject_list.py`と`health.py`を削除した。
外部のUUID検証、日本語HTTPException、開発用表示の有効化判定、外部ルーター登録をGoへ移動した。
Pythonには内部通信の受付、型検証、Session管理、ユースケース実行、結果・エラーコードのシリアライズが残る。
Pythonの内部HTTPプロセスは引き続き必要。言語を分けたことによる性能向上は未検証。

## 2026-10-11の分割後の検証

- `backend/`直下の共通Python環境を`uv sync --locked`で同期。
- Pythonの46テストが成功。科目モジュールの逆依存検査、共有設定の保存先検証、共通環境を使う実プロセス結合テスト3件を含む。
- 科目モジュールがAPI・設定・FastAPI・uvicornをimportしないことを確認。
- Goの共通モジュールの静的解析、共通テストの競合検出付き実行が成功。
- TaskとMakeのバックエンドチェックが成功。両方の共通環境同期、`task check`、フロントエンド6テスト、`task build`も成功。
- 通常の`dev`でVite → Go → Python → 一時SQLiteの4課程・科目一覧が一致（126・126・126・120科目）。422・404の応答とCtrl+Cによる3サーバー終了・ポート解放も確認。

通常の開発DBは検証に使用していない。ブラウザー操作・画面の見た目と外部OpenAPI/Swagger UIは未検証。

## アカウント認証の追加（2026-10-11）

認証モジュールは `modules/accounts/`。バックエンドは `application/auth.go` と `infrastructure/auth_client.go`、Pythonは `grad_checker_accounts/{domain,application,infrastructure}/` に配置する。外部HTTPとCookieは `api/presentation/auth.go`、内部アダプターは `internal_auth.py`。画面は `pages/accounts/AuthGate.tsx`、入力部品は `components/accounts/AuthForm.tsx`、状態管理は `hooks/accounts/useAuth.ts`。通信はaccountsモジュール内の取得契約を通し、アプリのcompositionで組み立てる。Pythonの入力・出力契約はPydanticを用い、dataclassは使用しない。

再現手順と認証設定は[認証の開発手順](auth_development.md)を参照する。

## 本人所属の保存

`accounts` のapplication/profile.pyにPydantic契約・リポジトリ契約・ユースケースを置き、infrastructure/profile.pyで既存students列と課程マスタを扱う。DB例外はapplication/errors/profile.pyの業務エラーへ変換する。
Python `/internal/profile` は認証サービスでセッションを検証し、そこから得た本人IDだけをユースケースへ渡す。更新はCSRFを検証した上で、BEGIN IMMEDIATEによる組合せ検証とrevision付きUPDATEを一つのトランザクションで行う。
Goのpresentation/profile.goが学生向け `/api/programs`・`/api/me`・`/api/me/program` の入力・Origin・HTTP応答を担当し、accounts/applicationの契約を通して内部クライアントを呼ぶ。内部のprofile包絡は外部応答で取り除く。

## 学生向け科目一覧と本人成績（2026-10-16）

| 外部API（Go） | Pythonへの内部呼出し |
| --- | --- |
| `GET /api/courses` | `POST /internal/courses`、`operation: courses`と絞り込み条件 |
| `GET /api/categories` | 同上、`operation: categories` |
| `GET /api/me/grades` | `POST /internal/grades`、`operation: get` |
| `PUT /api/me/grades` | 同上、`operation: save`とCSRF・成績の全集合 |

科目一覧は`modules/subjects`に操作を追加した。application/course_catalog.pyが本人課程から見た科目・分類の契約と絞り込み、infrastructure/course_catalog.pyが一つの読取スナップショットでの取得を担う。科目モジュールはaccounts・gradesを参照せず、`internal_courses.py`がセッションと本人所属から課程IDを決めて渡す。所属未設定は`program_not_selected`。

成績は新しい`modules/grades/`に置く。Pythonは`grad_checker_grades/{domain,application,infrastructure}/`、Goは`application/grades.go`と`infrastructure/grade_client.go`。domainが成績記号・確定状態と回次の並び、applicationがPydantic契約と全集合の検証、infrastructureが`grade_attempts`とBEGIN IMMEDIATEによる版確認・差分置換・`students.data_revision`の加算を担う。科目・学生テーブルの参照に限りinfrastructureから他モジュールのSQLModelを参照する。

Goのpresentation/courses.goとgrades.goが外部入力（クエリ・重複キー・未知フィールド・型・範囲・記号と状態の整合）を検証し、不正ならPythonを呼ばず422等を返す。回次の重複・連番・再履修の条件はPythonの業務ルールで判定し、業務エラーコードをGoが日本語detailへ変換する。

## 内部通信と外部HTTPの共通化（2026-10-16）

GoからPythonを呼ぶ5つの内部クライアントは `modules/shared/internalhttp` を使い、包絡形式 `{"data": ...}` / `{"error": {"code": ...}}` の解析、応答本文の上限、タイムアウト・接続失敗・形式違反の区別を共通化した。業務エラー型への変換と `data` の業務上の検証は各モジュールのinfrastructureに残す。
Goの外部ハンドラーは `api/presentation/http.go` の共通関数で、メソッド・セッションCookie・クエリ・Origin／CSRF・JSON本文を検証する。JSON更新のContent-Type不正は415、本文の上限超過は413で揃えた（所属保存は従来422だった）。成績・所属・科目で共通の業務エラーコード（未認証・CSRF不一致・更新版の競合・利用不可）は同じステータスと文言に変換する。

