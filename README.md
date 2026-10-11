# grad-checker

東京工科大学の学生が、所属課程の卒業単位要件と不足条件を確認するためのWebアプリケーションを開発するリポジトリです。

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

## 起動と構成

Go 1.22以上の`go`コマンドをPATHに用意してください。
`task dev`または`make dev`で、画面・Go外部API・Python内部サービスを起動します。
HTTP入力検証と外部応答はGo、業務処理とDBアクセスはPythonが担当します。
バックエンドは`api/`・`modules/subjects/`ごとに依存定義・ロック・仮想環境を分けています。共通設定は`backend/config/`に置きます。`backend-install`で各環境を個別に同期します。層の配置・内部通信・確認手順は[バックエンドの構成](docs/backend_architecture.md)を参照してください。
