# grad-checker

東京工科大学の学生が、所属課程の卒業単位要件と不足条件を確認するためのWebアプリケーションを開発するリポジトリです。

VS Codeでは [grad-checker.code-workspace](grad-checker.code-workspace) を開くと、ルート・バックエンド・フロントエンドをまとめて扱えます。

## セットアップ

リポジトリのルートで、Task または Make のどちらかを使って依存関係をセットアップしてください。

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
