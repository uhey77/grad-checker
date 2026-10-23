# grad-checker

東京工科大学の学生が、所属課程の卒業・修了要件と不足条件を確認するためのWebアプリケーション用リポジトリです。

## セットアップ

Task を使用する場合：

```sh
task setup
```

Make を使用する場合：

```sh
make setup
```

## タスクランナーのコマンド

利用できるコマンドと説明は、リポジトリのルートで `task` または `make` を実行して確認してください。
コマンドの定義は [Taskfile.yml](Taskfile.yml) または [Makefile](Makefile) を参照してください。

SQLiteからNeon PostgreSQLへの接続・データ移行・検証は、[移行手順](backend/migrations/README.md)を参照してください。本番への切替は自動では行いません。

Cloud Run / Vercel / GitHub Actionsの構成、承認、初回公開と運用については[本番デプロイ手順](docs/production-deployment.md)を参照してください。
