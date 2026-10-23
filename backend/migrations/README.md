# SQLiteからNeon PostgreSQLへの移行

既存SQLModel / SQLAlchemy、テーブル名とID、認証情報のハッシュ、セッション、成績回次、版番号、保存済み判定JSONを維持する。Neon Authへの移行は行わない。通常アクセスには`DATABASE_URL`、独立した移行処理には直接接続の`DIRECT_DATABASE_URL`を使う。接続情報は環境変数で渡し、ログ・コード・コマンド履歴へ実値を記録しない。

## 事前確認

1. 本番への実行はユーザー承認後に限る。まずNeonの隔離ブランチでリハーサルする。
2. SQLiteへの書込みを停止し、SQLite backup API等で整合したバックアップを作成する。稼働中のDBファイルだけをコピーするとWALの変更を取りこぼすため使用しない。
3. 元DB・バックアップは保持する。移行元は必ずバックアップを指定する。
4. テーブル・カラムは現行定義との一致を必要とする。旧形式の場合はバックアップのコピーで既存改訂手順を検証し、元DBを自動変更しない。
5. 移行先の接続はNeon ConsoleのSSL設定を保持する。poolerホストは移行コマンドで拒否する。

コマンドは`backend/`から実行する。Pythonは環境ファイルを自動ロードしないため、実行環境の方法でGit管理外の設定を読み込んでおく。

## スキーマ作成（データ移行・Seedと独立）

```sh
uv sync --locked
uv run --locked python -m migrations.schema --sql > /tmp/grad-checker-schema.sql
```

このDDL出力は接続不要で、テーブル・制約・インデックス・判定履歴更新拒否トリガーをレビューできる。SQLに認証情報や業務データは含まれない。

`DIRECT_DATABASE_URL`を設定して移行先の空状態を読み取り確認する：

```sh
uv run --locked python -m migrations.schema
```

DDLの影響・バックアップ・復元手順をレビューして承認を受けた後だけ、以下を実行する：

```sh
uv run --locked python -m migrations.schema --apply
```

既存テーブル・ビューのあるスキーマは拒否する。`--apply`のないコマンドはDDLを実行しない。スキーマ作成は一つのトランザクションで行い、失敗時は取り消す。既存スキーマへの再実行は変更せず失敗する。今後の既存スキーマ改訂には個別のマイグレーションを追加し、この初期化処理で既存テーブルを上書きしない。

## SQLiteのデータコピー

スキーマ作成済み・全テーブル空の移行先に対して、まず読み取り確認を行う。`BACKUP_PATH`はバックアップのパスを設定した環境変数。

```sh
uv run --locked python -m migrations.postgres --source "$BACKUP_PATH"
```

対象テーブル・カラム・外部キー整合性を確認し、テーブル別件数を出力する。移行元はSQLiteの`mode=ro`で開き、一つの読取りスナップショットを使用する。移行先も読み取り専用トランザクションを使う。現行スキーマと異なる移行元、移行先に既存行がある場合は拒否する。

データ移行の承認後：

```sh
uv run --locked python -m migrations.postgres --source "$BACKUP_PATH" --apply
```

親子参照の順にコピーし、全テーブルの全カラムを型復元後に照合してからcommitする。JSON文字列は文字列として保持し、JSONカラム・日時・Booleanは型を揃えて比較する。既存の規則改訂・Seedは呼ばない。途中失敗時はデータコピー全体をrollbackし、作成済みスキーマと元SQLiteを維持する。移行済みDBへの再実行は既存データを変更せず失敗する。

全件をメモリに保持して照合するため、本番前のリハーサルで時間・メモリを確認する。失敗時は件数と接続・スキーマ・元DBの形式を確認し、空の検証先で再試行する。CLIはエラーのSQL・DETAIL・接続情報をそのままログへ出力しない。

## 接続・切替・復旧

移行先の`DATABASE_URL`を設定して、書込みなしで確認する：

```sh
uv run --locked python -m scripts.check_database
```

成功時：`DB connection OK; schema OK (read only)`。接続だけを確認する場合は`--connection-only`を付ける。PostgreSQLの通常起動は不足テーブル・カラム・更新拒否トリガーを検出して停止し、自動DDL・自動データ改訂を実行しない。

隔離環境で登録・ログイン・復旧・所属・成績・判定・履歴・他ユーザーのアクセス拒否を確認する。本番切替後にPostgreSQLへ書込みがあった場合は、その差分を保全する前にSQLiteへ戻さない。復旧時にもDB削除・スキーマ初期化を行わず、保管したバックアップやNeonの復元機能を別環境で検証してから承認を受けて切り替える。

## 自動検証

ローカルPostgreSQLの接続を`TEST_POSTGRES_URL`へ設定する。テストは各ケースの専用スキーマだけを作成・削除し、リモートホストを拒否する。未設定時はskipされるため、PostgreSQL検証済みとは扱わない。

リポジトリルート：

```sh
uv run --locked --project backend pytest backend/tests/integration/test_postgres.py backend/tests/e2e/test_postgres_http.py
```

本番Secret Managerの権限・初回公開・運用・承認ゲートは[本番運用手順](../../docs/production-deployment.md)を参照する。
