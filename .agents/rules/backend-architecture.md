# バックエンドのアーキテクチャルール

対象は `backend/`。FastAPI・Pydantic・SQLModelによる現在の層構成を維持する。

## 各層の責務

| 場所（backend/app 以下） | 責務 | 配置例 |
| --- | --- | --- |
| `domain/` | 業務上の概念・区分・ルール | 科目区分、授業種別、課程の確認状態 |
| `application/` | ユースケース、取得・保存の契約、入力・出力モデル、業務エラー | 科目一覧の取得契約、シードデータの整合性検証 |
| `infrastructure/` | DB・ファイルなど外部資源へのアクセスと変換 | SQLModelのテーブル、リポジトリ実装、JSON読込・投入 |
| `presentation/` | HTTP入力・応答、依存解決、エラーのHTTPへの変換 | FastAPIルーター、リクエスト単位のSession管理 |
| `main.py`・`config.py` | アプリ生成、起動・終了処理、設定 | エンジンの生成・破棄、ルーター登録、環境変数 |
| `seed.py` | 開発者向けCLIの入口と依存関係の組み立て | 引数処理、投入処理の呼出し、終了コード |

## 依存方向

- `domain` は他のアプリ層、FastAPI、SQLModel、DB、HTTPに依存させない。
- `application` は `domain` を参照できる。`infrastructure`・`presentation` の具体実装は参照しない。
- `application` の入出力契約には、既存実装に合わせてPydanticを使用できる。
- `infrastructure` は `application` の契約を実装し、`domain` の概念を利用できる。`presentation` は参照しない。
- `presentation` はユースケースを呼び出す。業務判断やSQLクエリをルーターへ追加しない。
- `main.py` とCLIの入口で具体的な依存関係を組み立てる。
- 現在の科目一覧ルーターは、リクエストのSessionから具体的なリポジトリを生成する。この組み立てとDB例外のHTTP変換に限り、`presentation` から `infrastructure`・DBライブラリを参照できる。依存解決は `presentation/dependencies.py` にも配置できる。

## 実装ルール

- 新しい業務処理は `application` に置き、必要な取得・保存の契約をそこで定義する。DB処理は `infrastructure` に実装する。
- SQLModelのテーブルモデルを、そのまま業務契約として他の層へ広げない。リポジトリで入出力モデルへ変換する。
- 業務エラーは `application/errors/` に定義し、HTTPステータスやCLIの終了コードへの変換は入口で行う。
- Sessionは処理単位で管理する。書込みのトランザクション境界を明示し、一連の処理が失敗した場合は全体をロールバックする。リクエスト終了時に自動commitしない。
- 複数クエリで一つの結果を組み立てる場合は、読取りの一貫性を保つ。
- 科目の同一性と、課程ごとの分類・必修区分は分ける。適用入学年度などの未確認情報は、推測で確定しない。出典・注記・確認状態を保持する。
- 設定は `config.py` の `Settings` に集約し、業務処理内で環境変数を直接読まない。
- 開発用科目一覧APIの有効化条件を維持する。学生向けAPIを追加するときは、開発用APIと役割・契約を分ける。
- 集約・値オブジェクト・共通基底クラスは、対応する業務処理や共通責務が必要になった時点で導入する。

## 変更後の確認

コマンドはリポジトリルートで実行する。TaskとMakeのどちらも利用できる。

| 確認 | Task | Make |
| --- | --- | --- |
| lint・整形状態・型 | `task backend-check` | `make backend-check` |
| テスト | `task backend-test` | `make backend-test` |

処理を変更した場合は、該当するユースケース・DB・APIのテストで正常系と失敗時の振る舞いを確認する。
確認のために通常の開発DBへデータを投入せず、テスト用DBを使う。
文書だけの変更では、リンク・配置例・コマンドと実装の整合性を確認する。

## 関連文書

- [要件定義](../../docs/RDD.md)
- [API仕様](../../docs/api_specification.md)
- [DB設計](../../docs/database_design.md)
- [卒業要件判定ロジック](../../docs/graduation_requirement_logic.md)
- [シードデータの説明](../../backend/seeds/README.md)

設計文書に記載された機能がすべて実装済みであるとは扱わない。
