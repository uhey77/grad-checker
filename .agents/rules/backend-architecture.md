# バックエンドのアーキテクチャルール

対象は `backend/`。APIと業務モジュールを分け、各モジュール内で層の依存方向を守る。
外部HTTPはGo、業務処理とDBはPython、両者の接続はローカルのブリッジHTTPとする。GoがPythonを呼ぶこの通信を「ブリッジ通信」と呼び、Pythonの受け口は`/bridge/*`・`go_bridge_*.py`、Goの共通クライアントは`modules/shared/pythonbridge`とする。
科目一覧・アカウント認証・本人成績の保存をこの分担で実装する。学生向けの未実装機能を実装済みとは扱わない。
構成と通信契約は[バックエンドの構成](../../docs/backend_architecture.md)を参照する。

## 各層の責務

| 場所（backend/ 以下） | 責務 | 配置例 |
| --- | --- | --- |
| `modules/subjects/grad_checker_subjects/domain/` | Pythonの業務上の概念・区分・ルール | 科目区分、授業種別、課程の確認状態 |
| `modules/subjects/grad_checker_subjects/application/` | Pythonのユースケース・取得契約・業務エラー | 科目一覧の取得契約、シードデータの整合性検証 |
| `modules/subjects/grad_checker_subjects/infrastructure/` | PythonのDB・ファイルアクセス | SQLModel、リポジトリ |
| `modules/subjects/application/ports/`・`infrastructure/` | Goの取得契約とブリッジ通信の実装 | PythonへのHTTPクライアント |
| `api/presentation/`・`api/api_service/presentation/` | Goの外部HTTP、Pythonのブリッジアダプター | 入力検証、業務エラー変換、注入されたユースケースの呼出し |
| `modules/shared/pythonbridge/` | GoからPythonサービスを呼ぶ共通処理 | ブリッジ通信の包絡形式、タイムアウト・接続失敗・形式違反の区別 |
| `api/presentation/http.go` | Goの外部HTTPで共通の検証と応答 | メソッド・セッション・CSRF・JSON本文の検証、共通の業務エラー変換 |
| `modules/shared/grad_checker_shared/` | Pythonの業務モジュールで共通の業務エラー基底とUnit of Work | `BusinessError`、`UnitOfWork`、`SqlUnitOfWork` |
| `api/api_service/presentation/go_bridge_call.py`・`dependencies.py` | Pythonのブリッジアダプターで共通の包絡形式・呼出し契約・本人確認 | `respond`、`SessionCall`、`current_identity` |
| `api/main.go`・`api/api_service/main.py`・`api/api_service/composition.py` | 設定・起動・終了と依存関係の組立て | ハンドラー注入、DB起動終了 |
| `config/settings.py` | Pythonの環境設定 | DB接続URL |
| `scripts/seed_subjects.py` | 開発者向けCLIの入口 | 引数処理、投入処理の呼出し、終了コード |

## パッケージと依存管理

- Pythonの依存定義・ロック・Pythonバージョン・仮想環境は`backend/pyproject.toml`・`backend/uv.lock`・`backend/.python-version`・`backend/.venv`に統一する。`api/`・`modules/`・`config/`に重複して置かない。
- `api/`・`modules/`・`config/`・`scripts/`は共通環境にインストールするPythonパッケージとする。業務ごとのコード配置と層の依存方向は維持する。
- 科目モジュールはAPI・設定を参照しない。APIとCLIが設定値と具体実装を組み合わせる。
- 通常の起動はリポジトリルートのTask / Makeを使用する。画面は127.0.0.1:5173、Go外部APIは127.0.0.1:8000、Pythonサービスは127.0.0.1:8001に統一する。Python単独起動は`backend-python-dev`を使用し、直接起動する場合も`--host 127.0.0.1 --port 8001`を明示する。CLIは`backend/`から`python -m scripts.seed_subjects`で起動する。詳細は[起動と確認](../../docs/backend_architecture.md#起動と確認)を参照する。
- 業務処理・HTTP・設定と開発ツールの第三者依存はすべて`backend/pyproject.toml`に宣言し、一つのロックで解決する。
- Goの`go.mod`は`backend/`直下の一つに統一する。配下に別の`go.mod`を作らず、API・科目・テストを共通モジュールから検証する。ローカル`require`・`replace`は不要。
- 新しい業務モジュールは`modules/<機能>/`に配置し、必要になった利用側からのみ参照する。Python依存はバックエンドルートに追加する。

## 依存方向

- `domain` は他のアプリ層、FastAPI、SQLModel、DB、HTTPに依存させない。
- `application` は `domain` を参照できる。`infrastructure`・`presentation` の具体実装は参照しない。
- Pythonの業務モジュールではDomainを含めdataclassを使用しない。Applicationの入出力DTOはPydantic、Domainの値オブジェクトはPydanticの`BaseModel`・`RootModel`で表し、原則`strict=True`・`frozen=True`・`extra="forbid"`とする。Domain内で完結する制約をvalidatorに置き、DB・認可・外部処理は持ち込まない。Goの取得契約には既存科目モデルに従うJSONデータを使用できる。ブリッジ通信の包絡形式はGoの`infrastructure`とPythonのブリッジアダプターに閉じ込める。
- `infrastructure` は `application` の契約を実装し、`domain` の概念を利用できる。`presentation` は参照しない。
- `presentation` はユースケースを呼び出す。業務判断やSQLクエリをルーターへ追加しない。
- PythonのAPI・他モジュールは各業務パッケージの`public.py`から業務契約を参照する。公開窓口はdomain・applicationのみを公開し、ORM・SQL・具体的なリポジトリを公開しない。共有SQLiteの横断参照は既存infrastructureに限り、domain・applicationへ広げない。
- 認証・判定・履歴の現在時刻はABCの`Clock`を注入する。UTCの`SystemClock`はComposition Rootで選択する。UseCase・UoWは呼出しごと、Sessionはread/writeごとに生成し、並行する要求でUoWを共有しない。
- Goは`api/main.go`、Pythonは`api/api_service/main.py`・`composition.py`とCLIの入口で具体的な依存関係を組み立てる。
- Pythonのブリッジアダプターは`Depends`で操作別UseCaseを受け取り、`execute`を呼んで結果または業務エラーコードを返す。`presentation`から設定・DB・`infrastructure`を参照しない。具体的な生成はComposition Rootに集約する。
- Goの外部ハンドラーは`application`の取得契約を使用する。具体的なPython HTTPクライアントは参照しない。
- 各モジュールのGoの`infrastructure`は`modules/shared/pythonbridge`でブリッジ通信を行い、包絡形式の解析を重複させない。`pythonbridge`は業務モジュールを参照しない。業務エラー型への変換と応答内容の検証は各モジュールで行う。
- Goの外部ハンドラーは`api/presentation/http.go`の共通関数で検証・エラー応答を行い、同じ失敗を画面ごとに異なるステータス・文言で返さない。
- Pythonの業務エラーは`grad_checker_shared`の`BusinessError`を継承し、コードを持たせる。`grad_checker_shared`は業務モジュール・API・設定を参照せず、DB例外から業務エラーへの変換関数は呼出し側のモジュールが渡す。
- Pythonのトランザクション境界は`application`のユースケースがUnit of Workの`read`・`write`で決める。各モジュールは`application`に`UnitOfWork`を継承した契約（使うリポジトリを抽象プロパティで宣言）を定義し、`infrastructure`で`SqlUnitOfWork`とその契約を継承して実装する。リポジトリはトランザクションの開始・commit・ロールバックを行わず、ブロック外で使用しない。BEGIN・commit・ロールバック・DB例外の変換を重複させない。
- Pythonのブリッジアダプターは`go_bridge_call.py`の`respond`で包絡形式を返し、予期しない例外は`internal_error`としてログに残す。本人セッションの確認は`current_identity`、変更操作はCSRFトークンを渡して照合する。

## 実装ルール

- PythonのApplication直下は`__init__.py`だけにし、入出力を`dto/`、ABCのRepository・UoW・外部機能を`ports/`、共有する手順と検証・DTO組立てを`services/`、エラーを`errors/`へ整理する。DTOとPortからUseCase・サービスへ逆依存させない。使わない役割の空ディレクトリや旧パスの互換用再exportは作らない。GoのGateway契約は`application/ports/`（package ports）にまとめる。
- 公開操作は `application/use_cases/<操作>.py` の1操作1クラスの`*UseCase`にし、公開実行メソッドを`execute`に統一する。処理本体とトランザクション境界をそのUseCaseへ置き、複数操作を持つServiceで代用したり、そのServiceへの委譲だけのUseCaseを増やしたりしない。UseCase同士の直接呼出しを避け、共有する段取りはApplication Serviceへ切り出す。API・CLIは公開窓口のUseCaseを呼ぶ。
- ユースケースの手順と取得・保存契約は `application` に置く。業務上の不変条件・計算・判断は `domain`、DB処理は `infrastructure` に置く。DomainのエラーはApplicationで公開用の業務エラーへ変換する。
- Pythonの`application`の取得・保存契約（リポジトリ・Unit of Work・外部処理）はABCの抽象メソッドで定義する。`infrastructure`の実装とテストのFakeは契約を継承し、実装する契約を明示する。
- SQLModelのテーブルモデルを、そのまま業務契約として他の層へ広げない。リポジトリで入出力モデルへ変換する。
- Pythonの業務エラーは`application/errors/`に定義する。DBライブラリの例外は`infrastructure`で業務エラーへ変換する。外部HTTPステータスと日本語`detail`への変換はGoの`presentation`で行う。Pythonのブリッジアダプターには外部APIのメッセージ・ヘッダー・ステータスの判断を置かない。
- SessionはUnit of Workの`read`・`write`のブロックごとに開閉する。`write`は正常終了でcommitし、一連の処理が失敗した場合は全体をロールバックする。`read`は変更を残さない。ブロック外やリクエスト終了時に自動commitしない。
- Unit of Workの範囲は、部分的な成功が業務上許されるかで決める。全部成功か全部失敗かが必要な書込みは一つの`write`にまとめる。入力検証・パスワードハッシュ・判定計算など書込みに不要な処理はブロックの外で行い、ロックの保持を短くする。失敗しても残す記録（認証の試行回数など）は独立した`write`に分ける。ブロック外で読んだ値に依存して書き込む場合は、版や条件付きUPDATEで競合を検出する。
- 複数クエリで一つの結果を組み立てる場合は、読取りの一貫性を保つ。
- 科目の同一性と、課程ごとの分類・必修区分は分ける。適用入学年度などの未確認情報は、推測で確定しない。出典・注記・確認状態を保持する。
- Pythonの設定は`config/settings.py`の`Settings`、Goの設定は`api/main.go`の起動引数に集約し、業務処理内で環境変数を直接読まない。
- 開発用科目一覧APIはGoの起動引数で明示的に有効化し、既定では無効とする。Pythonサービスはループバックで起動し、外部`/api`ルートを作らない。学生向けAPIを追加するときは開発用APIと役割・契約を分ける。
- GoへDBモデル・SQLクエリ・卒業判定・推薦ルールを複製しない。Pythonはブリッジ通信の形を防御的に検証するが、外部入力の日本語エラー変換はGoに集約する。
- 集約・値オブジェクト・共通基底クラスは、対応する業務処理や共通責務が必要になった時点で導入する。
- ユースケースのトランザクション範囲は、メモリ上のリポジトリを持つFakeのUnit of Workでcommitとロールバックを検証する。DBの制約・ロック・並行処理は一時SQLiteで検証する。
- Python・Goのテストは`backend/tests/`に配置する。`api/`・`modules/`の実装層にGoの`*_test.go`を置かない。Goのテストは対象パッケージをimportし、公開契約から検証する。

認証はアプリ専用のユーザー名とパスワードを使用し、メールアドレス・大学ドメイン制限・SMTPを導入しない。ユーザー名は半角英数字・アンダースコアの3〜32文字を小文字に正規化する。復旧コードはハッシュのみをDB保存し、再設定時のコード更新・パスワード更新・全セッション失効は一つのトランザクションで行う。本人のデータは変更されないアカウントIDに紐づける。

## 変更後の確認

コマンドはリポジトリルートで実行する。TaskとMakeのどちらも利用できる。

| 確認 | Task | Make |
| --- | --- | --- |
| lint・整形状態・型 | `task backend-check` | `make backend-check` |
| Python・実プロセス結合・Goテスト | `task backend-test` | `make backend-test` |
| Goテスト（競合検出付き） | `task go-api-test` | `make go-api-test` |

処理を変更した場合は、該当するユースケース・DB・APIのテストで正常系と失敗時の振る舞いを確認する。
`backend-check`はPythonとGoの両方を検証する。実プロセス結合テストにはGoとローカルポートの利用が必要。
GoがPATHにない場合は結合テストがスキップされるため、完全な確認として報告しない。
確認のために通常の開発DBへデータを投入せず、テスト用DBを使う。
文書だけの変更では、リンク・配置例・コマンドと実装の整合性を確認する。

## 関連文書

- [要件定義](../../docs/RDD.md)
- [API仕様](../../docs/api_specification.md)
- [DB設計](../../docs/database_design.md)
- [卒業要件判定ロジック](../../docs/graduation_requirement_logic.md)
- [シードデータの説明](../../backend/seeds/README.md)

設計文書に記載された機能がすべて実装済みであるとは扱わない。
