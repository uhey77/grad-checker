# grad-checker

東京工科大学の学生が、所属課程の卒業単位要件と不足条件を確認するためのWebアプリケーションを開発するリポジトリです。

## セットアップ

リポジトリのルートから、Task または Make のどちらかで実行してください。

Task を使用する場合：

```sh
task setup
task backend-seed
task dev
```

Make を使用する場合：

```sh
make setup
make backend-seed
make dev
```

依存関係のセットアップと科目データの投入は初回に実行してください。次回からは `task dev` または `make dev` だけで両方を起動できます。

## タスクランナーのコマンド

利用できるコマンドと説明は、リポジトリのルートで `task` または `make` を実行して確認してください。
コマンドの定義は [Taskfile.yml](Taskfile.yml) または [Makefile](Makefile) を参照してください。
