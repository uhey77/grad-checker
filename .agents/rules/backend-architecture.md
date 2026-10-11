# バックエンドのアーキテクチャルール

対象は `backend/`。APIと業務モジュールを分け、各モジュール内で層の依存方向を守る。
外部HTTPはGo、業務処理とDBはPython、両者の接続はローカル内部HTTPとする。
現在の科目一覧をこの分担で実装する。学生向けの未実装機能を実装済みとは扱わない。
構成と通信契約は[バックエンドの構成](../../docs/backend_architecture.md)を参照する。

## 各層の責務

| 場所（backend/ 以下） | 責務 | 配置例 |
| --- | --- | --- |
| `modules/subjects/grad_checker_subjects/domain/` | Pythonの業務上の概念・区分・ルール | 科目区分、授業種別、課程の確認状態 |
| `modules/subjects/grad_checker_subjects/application/` | Pythonのユースケース・取得契約・業務エラー | 科目一覧の取得契約、シードデータの整合性検証 |
| `modules/subjects/grad_checker_subjects/infrastructure/` | PythonのDB・ファイルアクセス | SQLModel、リポジトリ |
| `modules/subjects/application/`・`infrastructure/` | Goの取得契約と内部通信の実装 | PythonへのHTTPクライアント |
| `api/presentation/`・`api/api_service/presentation/` | Goの外部HTTP、Pythonの内部通信アダプター | 入力検証、業務エラー変換、Session管理 |
| `api/main.go`・`api/api_service/main.py` | 設定・起動・終了と依存関係の組立て | ハンドラー注入、DB起動終了 |
| `config/settings.py` | Pythonの環境設定 | DB接続URL |
| `scripts/seed_subjects.py` | 開発者向けCLIの入口 | 引数処理、投入処理の呼出し、終了コード |

## パッケージと依存管理

- Pythonの依存定義・ロック・Pythonバージョン・仮想環境は`backend/pyproject.toml`・`backend/uv.lock`・`backend/.python-version`・`backend/.venv`に統一する。`api/`・`modules/`・`config/`に重複して置かない。
- `api/`・`modules/`・`config/`・`scripts/`は共通環境にインストールするPythonパッケージとする。業務ごとのコード配置と層の依存方向は維持する。
- 科目モジュールはAPI・設定を参照しない。APIとCLIが設定値と具体実装を組み合わせる。
- 通常の起動はリポジトリルートのTask / Makeを使用する。画面は127.0.0.1:5173、Go外部APIは127.0.0.1:8000、Python内部サービスは127.0.0.1:8001に統一する。Python単独起動は`backend-python-dev`を使用し、直接起動する場合も`--host 127.0.0.1 --port 8001`を明示する。CLIは`backend/`から`python -m scripts.seed_subjects`で起動する。詳細は[起動と確認](../../docs/backend_architecture.md#起動と確認)を参照する。
- 業務処理・HTTP・設定と開発ツールの第三者依存はすべて`backend/pyproject.toml`に宣言し、一つのロックで解決する。
- Goの`go.mod`は`backend/`直下の一つに統一する。配下に別の`go.mod`を作らず、API・科目・テストを共通モジュールから検証する。ローカル`require`・`replace`は不要。
- 新しい業務モジュールは`modules/<機能>/`に配置し、必要になった利用側からのみ参照する。Python依存はバックエンドルートに追加する。

## 依存方向

- `domain` は他のアプリ層、FastAPI、SQLModel、DB、HTTPに依存させない。
- `application` は `domain` を参照できる。`infrastructure`・`presentation` の具体実装は参照しない。
- Pythonの`application`の入出力契約にはPydanticを使用できる。Goの取得契約には既存科目モデルに従うJSONデータを使用できる。内部通信の包絡形式はGoの`infrastructure`とPythonの内部アダプターに閉じ込める。
- `infrastructure` は `application` の契約を実装し、`domain` の概念を利用できる。`presentation` は参照しない。
- `presentation` はユースケースを呼び出す。業務判断やSQLクエリをルーターへ追加しない。
- Goは`api/main.go`、Pythonは`api/api_service/main.py`とCLIの入口で具体的な依存関係を組み立てる。
- Pythonの内部アダプターはSessionからリポジトリを生成してユースケースを呼び、結果または業務エラーコードを返す。この依存解決に限り`presentation`から`infrastructure`を参照できる。
- Goの外部ハンドラーは`application`の取得契約を使用する。具体的なPython HTTPクライアントは参照しない。

## 実装ルール

- 新しい業務処理は `application` に置き、必要な取得・保存の契約をそこで定義する。DB処理は `infrastructure` に実装する。
- SQLModelのテーブルモデルを、そのまま業務契約として他の層へ広げない。リポジトリで入出力モデルへ変換する。
- Pythonの業務エラーは`application/errors/`に定義する。DBライブラリの例外は`infrastructure`で業務エラーへ変換する。外部HTTPステータスと日本語`detail`への変換はGoの`presentation`で行う。Pythonの内部アダプターには外部APIのメッセージ・ヘッダー・ステータスの判断を置かない。
- Sessionは処理単位で管理する。書込みのトランザクション境界を明示し、一連の処理が失敗した場合は全体をロールバックする。リクエスト終了時に自動commitしない。
- 複数クエリで一つの結果を組み立てる場合は、読取りの一貫性を保つ。
- 科目の同一性と、課程ごとの分類・必修区分は分ける。適用入学年度などの未確認情報は、推測で確定しない。出典・注記・確認状態を保持する。
- Pythonの設定は`config/settings.py`の`Settings`、Goの設定は`api/main.go`の起動引数に集約し、業務処理内で環境変数を直接読まない。
- 開発用科目一覧APIはGoの起動引数で明示的に有効化し、既定では無効とする。Python内部サービスはループバックで起動し、外部`/api`ルートを作らない。学生向けAPIを追加するときは開発用APIと役割・契約を分ける。
- GoへDBモデル・SQLクエリ・卒業判定・推薦ルールを複製しない。Pythonは内部通信の形を防御的に検証するが、外部入力の日本語エラー変換はGoに集約する。
- 集約・値オブジェクト・共通基底クラスは、対応する業務処理や共通責務が必要になった時点で導入する。
- Python・Goのテストは`backend/tests/`に配置する。`api/`・`modules/`の実装層にGoの`*_test.go`を置かない。Goのテストは対象パッケージをimportし、公開契約から検証する。

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
