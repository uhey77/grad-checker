# SQLiteからNeon PostgreSQLへの移行

SQLModel / SQLAlchemy・既存テーブル名とID・ユーザー名認証・パスワードと復旧コードのハッシュ・セッション・成績回次・版番号・卒業要件と保存済み判定JSONを維持する。Neon Authには移行しない。API契約・画面の変更は不要。

## 接続先の調査結果

2026-10-23にNeon公式プラグインで読み取り確認した結果：

- プロジェクト：`grad-checker`（`plain-smoke-97118898`）
- ブランチ：`production`（`br-calm-water-a1uug5fd`）
- データベース：`grad-checker`（既定の`neondb`とは異なる）
- リージョン：`aws-ap-southeast-1`、PostgreSQL 18.6
- 接続先のpublicスキーマのテーブル：0件

これは調査時点の状態。本番への投入・切替は実施していない。

## 実装上の対応

| SQLite固有の処理 | PostgreSQLでの対応 |
| --- | --- |
| sqlite3接続、外部キーPRAGMA | 同期psycopg 3、PostgreSQLの外部キー制約 |
| BEGINによる複数SELECTの一貫性 | REPEATABLE READ |
| BEGIN IMMEDIATEによる書込み直列化 | READ COMMITTEDと共通のpg_advisory_xact_lock |
| 認証試行のSQLite UPSERT | PostgreSQLのON CONFLICT DO NOTHING |
| typeofによる整数検査 | INTEGERカラムと下限CHECK（SQLiteのtypeof検査も維持） |
| json_valid、複数パスのjson_extract | JSONへのCASTによる検査とJSON要約抽出 |
| 判定履歴の更新拒否トリガー | 同じ更新拒否をPL/pgSQLトリガーで実装 |
| 日時の保存 | 両DBともUTCに正規化したTIMESTAMP WITHOUT TIME ZONE |

プーリング利用時のセッション状態に依存しない。psycopgの自動prepared statementは無効化し、pool_pre_pingで切断済み接続を確認する。書込み直列化は従来の整合性を優先した方式で、書込み並列度の改善は別途設計する。既存の`Sqlite*`実装クラス名は呼出し元との互換性のため維持している。

## 接続設定

実値はプロセス環境に設定する。接続URLをソース、コマンド履歴、Git、報告へ貼らない。環境ファイルを使う場合はGit管理外の`.env.local`等に保管し、実行環境の方法で読み込む（Pythonは環境ファイルを自動ロードしない）。

| 環境変数 | 用途 |
| --- | --- |
| `DATABASE_URL` | 通常のアプリ接続。Neonのpooled URLを使用 |
| `DATABASE_URL_UNPOOLED` | 移行先の直接接続。poolerホストは移行コマンドで拒否 |
| `TEST_POSTGRES_URL` | 自動テスト用のローカルPostgreSQL。リモートホストは拒否 |

Neon Consoleが提供するSSL設定を保持する。通常の`postgresql://`形式はエンジン生成時に`postgresql+psycopg`へ変換する。未設定時のローカルSQLite既定値は維持するため、本番では`DATABASE_URL`の注入を必ず確認する。

## 実行手順

最初にNeonの隔離した検証用ブランチでリハーサルする。本番への実行前にはSQLiteの書込みを停止し、SQLite backup API等で整合したバックアップを作る。稼働中DBの単純なファイルコピーはWAL等を取りこぼすため使用しない。元DBとバックアップは切替後の確認が終わるまで保持する。

以下は`backend/`から実行する。`BACKUP_PATH`にはバックアップのパスを設定し、`DATABASE_URL_UNPOOLED`には検証先の直接接続を設定しておく。

```sh
uv sync --locked
uv run --locked python -m migrations.postgres --source "$BACKUP_PATH"
```

既定は読み取り確認のみ。移行元をSQLiteの`mode=ro`で開き、一つのスナップショットで読む。テーブル・カラムが現行定義と一致しない旧DB、外部キー違反、既存テーブル・ビューのある移行先は拒否する。旧DBの改訂が必要な場合は元データを自動変更せず、バックアップのコピーで既存改訂手順を検証してから再度確認する。

```sh
uv run --locked python -m migrations.postgres --source "$BACKUP_PATH" --apply
```

`--apply`のみが書込みを有効にする。テーブル・制約・インデックス・更新拒否トリガーを作り、親子参照順に全件コピーする。全テーブルの全カラムを型復元後に照合し、一致した場合だけcommitする。途中失敗時はPostgreSQLのDDLも含めてrollbackする。件数だけを出力し、認証情報・成績・判定JSONは出力しない。再実行時も既存テーブルを上書きしない。元SQLiteの既知規則を改訂する処理は移行中に実行しない。

現行の移行処理は全件をメモリ上に保持して照合する。大規模DBでは本番前のリハーサルで所要時間とメモリ使用量を確認する。

移行した接続先の`DATABASE_URL`を設定し、書込みなしで接続とスキーマを確認する：

```sh
uv run --locked python -m scripts.check_database
```

成功時は`DB connection OK; schema OK (read only)`。PostgreSQLの通常起動は不足テーブル・カラム・履歴トリガーを検出して停止し、自動作成・自動改訂を行わない。

検証用ブランチで登録・ログイン・復旧・所属選択・成績保存・卒業判定・履歴取得を確認してから、本番用のバックアップと空の移行先で同じ手順を行う。元DBの書込みを停止したまま、アプリの`DATABASE_URL`を切り替えて確認する。切替後にPostgreSQLへ新しい書込みがあった場合、SQLiteへ戻す前に差分の保全・反映方針を決める。新規データがある状態で単純にURLを戻さない。

## ローカル検証

ローカルPostgreSQL 18を用意し、`TEST_POSTGRES_URL`へ接続を設定してリポジトリルートから実行する。各ケースがランダムな専用スキーマを作り、終了時にそのスキーマだけを削除する。リモートホストは拒否するため、Neonの本番接続を指定しない。未設定時のPostgreSQLテストはskipとなり、検証済みとは扱わない。

```sh
uv run --locked --project backend pytest backend/tests/integration/test_postgres.py backend/tests/e2e/test_postgres_http.py
make backend-check
make backend-test
npm --prefix frontend run build
```

接続確認スクリプトとNeonプラグイン経由の読み取りSQLは別の検証である。ローカルのドライバー・移行・API検証が成功しても、Neonへのデータ移行や本番アプリの切替が完了したことは意味しない。

参考：[Neon SQLAlchemy](https://neon.com/docs/guides/sqlalchemy)、[Neon connection pooling](https://neon.com/docs/connect/connection-pooling)、[SQLAlchemy psycopg](https://docs.sqlalchemy.org/en/20/dialects/postgresql.html#module-sqlalchemy.dialects.postgresql.psycopg)。
