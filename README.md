# grad-checker

## タスクランナーのコマンド

以下のコマンドはリポジトリのルートで実行してください。Go Task
（`Taskfile.yml`）または Make（`Makefile`）を使用できます。どちらも同じ操作に対応しています。

| 操作 | Task | Make |
| --- | --- | --- |
| コマンド一覧を表示 | `task` | `make` |
| バックエンド・フロントのlint・整形状態・型を検証 | `task check` | `make check` |
| バックエンド・フロントの自動修正・整形 | `task format` | `make format` |
| バックエンドだけのlint・整形状態・型を検証 | `task backend-check` | `make backend-check` |
| フロントだけのlint・整形状態・型を検証 | `task frontend-check` | `make frontend-check` |
| すべての依存関係をインストール | `task setup` | `make setup` |
| フロントエンドの依存関係をインストール | `task frontend-install` | `make frontend-install` |
| バックエンドの依存関係をインストール | `task backend-install` | `make backend-install` |
| CS学部の科目データを投入 | `task backend-seed` | `make backend-seed` |
| バックエンドを起動 | `task backend-dev` | `make backend-dev` |
| ローカル確認用の科目一覧APIを起動 | `task backend-catalog` | `make backend-catalog` |
| バックエンドのテスト | `task backend-test` | `make backend-test` |
| Ruffのlint・整形状態を検証 | `task backend-lint` | `make backend-lint` |
| Ruffの自動修正・整形 | `task backend-format` | `make backend-format` |
| tyで型を検証 | `task backend-typecheck` | `make backend-typecheck` |
| コミット時のフックを登録 | `task pre-commit-install` | `make pre-commit-install` |
| 全ファイルにpre-commitを実行 | `task pre-commit` | `make pre-commit` |
| フロントエンドと科目一覧APIを同時に起動 | `task dev` | `make dev` |
| フロントエンドだけを起動 | `task frontend-dev` | `make frontend-dev` |
| フロントのlint・整形状態を検証 | `task frontend-lint` | `make frontend-lint` |
| フロントの自動修正・整形 | `task frontend-format` | `make frontend-format` |
| フロントの型を検証 | `task frontend-typecheck` | `make frontend-typecheck` |
| フロントエンドをビルド | `task build` | `make build` |
| フロントエンドのビルド結果をプレビュー | `task preview` | `make preview` |

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

`setup` はpre-commitのGitフックも登録します。セットアップ済みの場合は
`task backend-install` と `task pre-commit-install`（Makeも同名）を実行してください。
コミット時は `scripts/run-tasks.mjs` がTask（未インストールならMake）を選び、
`format` → `check` の順に両方のコードを自動修正・整形・検証します。
Task／Makeはどちらか一方のインストールで動作します。
自動修正された場合は差分を確認し、再度ステージしてコミットしてください。
Ruff・tyは `backend/uv.lock` のバージョンを使用します。
Ruffは `A`・`B`・`E`・`F`・`I`・`N`・`W`・`PL`・`UP` のルールを有効にし、
無視する7ルールは `backend/pyproject.toml` に明記しています。

フロントの依存は `frontend/package-lock.json` で管理します。
ESLintはTypeScriptとReact Hooksのルールを検証し、整形はPrettierに任せます。
TypeScriptはtypescript-eslintの対応範囲に合わせて6.0系を使用します。
フロントの依存を更新した場合は `task frontend-install`（Makeも同名）を実行してください。

両方をまとめて検証する場合は `task check` または `make check` を実行してください。
Ruff・ESLintのlint、Ruff・Prettierの整形状態、ty・TypeScriptの型チェックを行います。
片方だけを検証する場合は `backend-check` または `frontend-check` を使ってください。
整形を適用する場合は `format`、片方だけの場合は `backend-format`・`frontend-format` を使ってください。

開発サーバーの URL はターミナルに表示されます（通常は
http://127.0.0.1:5173）。`Ctrl+C` で両方のサーバーを終了します。
片方の起動失敗・終了時も、もう片方を停止します。

Windows PowerShell でも、リポジトリのルートから上記の Task / Make コマンドを使用してください。
補足として、npm を直接実行する際に実行ポリシーによって `npm.ps1` がブロックされる場合は、
`npm` の代わりに `npm.cmd` を使用してください。

## CI

プルリクエストの作成・追加コミット・再オープン時に、GitHub Actionsで
`make check` を実行します。バックエンドとフロントエンドのlint・整形状態・型を検証します。
設定は [チェック用ワークフロー](.github/workflows/check.yml) を参照してください。

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

参考：[Vite 入門ガイド](https://vite.dev/guide/)

## バックエンドの初期化・起動

```sh
task backend-install
task backend-seed
task backend-dev
```

Makeの場合は同名のターゲットを `make` で実行してください。
Swagger UIは `http://127.0.0.1:8000/docs`、ヘルスチェックは
`http://127.0.0.1:8000/api/health` です。

起動時とシード投入時に、SQLiteファイルと実装済みのマスタ6テーブルを
作成します。既存テーブルの削除・変更は行いません。スキーマ変更の
マイグレーションは今後追加します。
既定の保存先は `backend/data/grad_checker.db`。
環境変数 `DATABASE_URL` で別のSQLiteファイルを指定できます。

任意のJSONシードを投入する場合は、`backend/` で実行してください。

```sh
uv run python -m app.seed --file seeds/cs_2026.json
uv run pytest
```

JSONの全件検証と追加投入を1トランザクションで行います。同じ内容の再投入は
追加0件で完了し、入力から省略した既存マスタは削除しません。既存IDの内容変更、
コード重複、不正な単位数、分類循環・課程不一致は拒否します。
1件でも不正または保存失敗があれば、全件の変更を取り消して終了コード1を返します。
既存マスタの改訂は、今後の版管理・移行手順で扱います。

## 現在の実装範囲

FastAPI起動、ヘルスチェック、SQLite接続・セッション管理、課程・カリキュラム・
分類・科目・開講期・課程別科目のモデル、JSONシードCLIを実装しています。
ローカル確認用の科目一覧APIとReact / TypeScriptの閲覧画面も実装済みです。
学生向けの認証付き科目一覧API、ログイン・成績保存・卒業判定のAPIは今後実装します。

2026年度学生便覧から、先進情報専攻の情報基盤・人間情報・人工知能の3コースと
社会情報専攻の計4課程を転記しました。科目131件、分類68件、開講期161件、
課程別科目498件です。入学年度への適用範囲は未確認のため、カリキュラムは
`unverified` として保持します。卒業要件・換算規則は今回のシードには含みません。
転記元・内部コード・注記の扱いは [シードの説明](backend/seeds/README.md) を参照してください。

## ローカルで科目一覧を確認する

リポジトリのルートで依存関係とマスタを準備してください。

```sh
task setup
task backend-seed
```

1つのターミナルで両方を起動します。

```sh
task dev
# または make dev
```

表示されたURL（`http://127.0.0.1:5173/`）を開いてください。
ポート8000または5173で開発サーバーを起動済みなら、先に終了してください。
個別に起動する場合は `backend-catalog` と `frontend-dev` を使えます。

4課程を選択し、科目名・科目区分・必修区分・前期／後期・開講学部をAND条件で絞り込めます。
科目はSQLiteから取得し、便覧順・科目名順・単位数順・開講学年と学期順で並べ替えられます。
課程切替は確認対象だけを変更し、学生の所属・成績を保存しません。

ユーザー確認に基づく認証なしのローカル閲覧用で、APIは `/api/dev/course-catalog/programs` と
`/api/dev/course-catalog/{curriculum_id}` のGETのみです。通常起動では無効（404）。
`dev` と `backend-catalog` は `ENABLE_CATALOG_PREVIEW=true` を設定して127.0.0.1だけで起動します。
この設定を公開環境へ持ち込まず、学生用の認証APIは別途実装します。
Viteの開発・プレビューサーバーは `/api` を `http://127.0.0.1:8000` へプロキシします。

フロントの検証は `task build` / `make build`（TypeScript型検証＋Viteビルド）、
バックエンドは `task backend-test` / `make backend-test` を実行してください。
