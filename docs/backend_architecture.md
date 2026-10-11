# バックエンドの構成

`backend/api/`にHTTPの入口、`backend/modules/subjects/`に科目の業務処理を配置する。
Pythonの依存管理は`backend/`直下に統一し、共通設定は`backend/config/`に置く。GoもAPI・科目・テストごとにモジュールを分ける。
Goが外部HTTPの入力検証・レスポンス・業務エラーのHTTP変換を担当し、Pythonが業務処理とDBを担当する。
現在の実装対象は開発用の科目一覧。卒業判定・推薦・認証・成績保存は未実装。

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
├── api/
│   ├── go.mod / main.go               # Goの起動・依存関係の組立て
│   ├── presentation/subject_list.go   # 外部HTTPハンドラー
│   └── api_service/
│       ├── main.py                    # Python内部サービスの起動
│       └── presentation/              # 内部HTTPとSession管理
├── config/settings.py                # 共有設定。独立パッケージにはしない
├── modules/
│   └── subjects/
│       ├── go.mod
│       ├── application/subject_list.go
│       ├── infrastructure/subject_list_client.go
│       └── grad_checker_subjects/
│           ├── domain/                # 科目区分など
│           ├── application/           # ユースケース・取得契約・業務エラー
│           └── infrastructure/        # DB・JSON読み込み
├── scripts/seed_subjects.py           # 設定と科目モジュールを使うCLI
├── seeds/                            # 便覧データ
└── tests/                            # Python・Go・実プロセス結合テスト
    └── go.mod                        # APIと科目を検証する独立モジュール
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

Python内部サービスは`backend/`から`uv run --locked uvicorn api.api_service.main:app`で起動する。
投入CLIは同じ場所から`uv run --locked python -m scripts.seed_subjects --file seeds/cs_2026.json`で起動する。
APIと科目モジュールはコードの責務を分離するが、Pythonの依存バージョンや仮想環境は分離しない。

Goは引き続きAPI・科目・テストごとの`go.mod`を持ち、ローカル`replace`で参照先を指定する。
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

| 用途 | Task | Make |
| --- | --- | --- |
| 画面＋Go外部API＋Python内部サービス | `task dev` | `make dev` |
| バックエンドのみ（科目一覧は無効） | `task backend-dev` | `make backend-dev` |
| バックエンドのみ（科目一覧を有効化） | `task backend-subject-list` | `make backend-subject-list` |
| Python内部サービスのみ | `task backend-python-dev` | `make backend-python-dev` |
| Go外部APIのみ（科目一覧有効） | `task go-api-dev` | `make go-api-dev` |
| Python・Goのlint・整形状態・型 | `task backend-check` | `make backend-check` |
| Python・実プロセス結合テスト | `task backend-test` | `make backend-test` |
| Goテスト（競合検出付き） | `task go-api-test` | `make go-api-test` |

`dev-go`は`dev`と同じ構成で起動する互換コマンド。
画面は http://127.0.0.1:5173 、外部APIは http://127.0.0.1:8000 。Ctrl+Cで一括終了する。
通常の`dev`は科目一覧を有効にする。Go単体の既定は無効で、`-subject-list-preview`で有効化する。
Goの設定例は、`backend/api/`で`go run . -listen 127.0.0.1:8000 -python-url http://127.0.0.1:8001 -subject-list-preview`。
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
- Goの各モジュールの静的解析、共通テストの競合検出付き実行が成功。
- TaskとMakeのバックエンドチェックが成功。両方の共通環境同期、`task check`、フロントエンド6テスト、`task build`も成功。
- 通常の`dev`でVite → Go → Python → 一時SQLiteの4課程・科目一覧が一致（126・126・126・120科目）。422・404の応答とCtrl+Cによる3サーバー終了・ポート解放も確認。

通常の開発DBは検証に使用していない。ブラウザー操作・画面の見た目と外部OpenAPI/Swagger UIは未検証。
