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

## 登録・ログインをローカルで試す

```sh
task dev
# または
make dev
```

画面は `http://127.0.0.1:5173`。ユーザー名とアプリ専用パスワードで新規登録し、表示された復旧コードを保管してからログインします。メールアドレス・メール送信サービスは使用しません。`auth-dev` は `dev` と同じ起動構成です。

設定・復旧・旧DBの扱いは[認証の開発手順](docs/auth_development.md)を参照してください。
