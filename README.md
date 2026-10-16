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

ログイン後は所属設定から課程・カリキュラムを保存し、成績入力から本人の成績を入力・保存できます。選択肢が空の場合は `task backend-seed` または `make backend-seed` で科目マスタを投入してください。CS学部4課程の適用入学年度は未確認です。

CS学部4課程の卒業要件・算入規則マスタは、科目マスタ投入後に `task backend-requirements-seed` / `make backend-requirements-seed` で追加できます。再生成は `backend-requirements-build`。出典と未確認規則は[卒業要件マスタ](backend/seeds/requirements.md)を参照してください。判定処理・判定画面はまだ実装していません。

設定・復旧・旧DBの扱いは[認証の開発手順](docs/auth_development.md)を参照してください。
