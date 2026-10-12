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

## メール認証をローカルで試す

```sh
task auth-dev
# または
make auth-dev
```

画面は `http://127.0.0.1:5173`、確認メールの開発用受信箱は `http://127.0.0.1:8025` です。`@edu.teu.ac.jp` のアドレスで新規登録し、受信箱の確認リンクからパスワードを設定してログインします。このコマンドはメールを外部へ送りません。

実メール送信の設定と確認範囲は[メール認証の開発手順](docs/auth_development.md)を参照してください。
