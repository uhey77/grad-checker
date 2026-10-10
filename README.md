# grad-checker

## タスクランナーのコマンド

以下のコマンドはリポジトリのルートで実行してください。Go Task
（`Taskfile.yml`）または Make（`Makefile`）を使用できます。どちらも同じ操作に対応しています。

| 操作 | Task | Make |
| --- | --- | --- |
| コマンド一覧を表示 | `task` | `make` |
| すべての依存関係をインストール | `task setup` | `make setup` |
| フロントエンドの依存関係をインストール | `task frontend-install` | `make frontend-install` |
| バックエンドの依存関係をインストール | `task backend-install` | `make backend-install` |
| フロントエンドの開発サーバーを起動 | `task dev` | `make dev` |
| フロントエンドをビルド | `task build` | `make build` |
| フロントエンドのビルド結果をプレビュー | `task preview` | `make preview` |

開発やビルドを始める前に依存関係をインストールし、`preview` の前に `build`
を実行してください。バックエンドのセットアップには uv が必要です。
`task backend-install` または `make backend-install` で、`backend/uv.lock` に基づく依存関係をインストールします。
バックエンドのサーバー起動とテストのコマンドは、エントリーポイントとテストの実装後に追加予定です。

## フロントエンドの開発環境

フロントエンドでは、HTML・CSS・JavaScript の開発に Vite を使用しています。
UI フレームワーク、画面、アプリケーションのロジック、API 連携は未実装です。
HTML のエントリーポイントは意図的に空にしています。

### 前提条件

- Node.js：20.x 系では 20.19 以上、または 22.12 以上（Vite の要件）。
- npm：ロックファイルの生成には 11.12.1 を使用しています。
- ローカルでは Node.js 25.9.0 と npm 11.12.1 で動作確認済みです。

### セットアップ

リポジトリのルートから、Task または Make のどちらかで実行してください。

Task を使用する場合：

```sh
task frontend-install
task dev
```

Make を使用する場合：

```sh
make frontend-install
make dev
```

バックエンドも含めてセットアップする場合は、`task setup` または `make setup` を使用してください。

開発サーバーの URL はターミナルに表示されます（通常は
http://127.0.0.1:5173）。実装を始めるまでは空のページが表示されます。

Windows PowerShell でも、リポジトリのルートから上記の Task / Make コマンドを使用してください。
補足として、npm を直接実行する際に実行ポリシーによって `npm.ps1` がブロックされる場合は、
`npm` の代わりに `npm.cmd` を使用してください。

### ビルドとプレビュー

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

ビルド成果物は `frontend/dist/` に出力され、Git の管理対象から除外されます。
依存関係を更新した際は `frontend/package-lock.json` をコミットしてください。
インストールするバージョンを再現するには、`task frontend-install` または `make frontend-install` を使用します。

参考：[Vite 入門ガイド](https://vite.dev/guide/)
