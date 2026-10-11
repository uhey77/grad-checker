# grad-checker

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

利用できるコマンドと説明は、リポジトリのルートで次のコマンドを実行して確認してください。

Task を使用する場合：

```sh
task
```

Make を使用する場合：

```sh
make
```

コマンドの定義は [Taskfile.yml](Taskfile.yml) または [Makefile](Makefile) を参照してください。

## ビルドとプレビュー

リポジトリのルートから実行してください。

Task を使用する場合：

```sh
task build
task preview
```

Make を使用する場合：

```sh
make build
make preview
```
