# 開発・リリースフロー

`main` は本番公開用、`dev` は日常開発の統合用。devはPR #78マージ後のmain `9a1ea611374597e27766d934d34311708ecbd9d7` から作成した。
GitHubの既定ブランチはmainを維持するため、PR作成時には明示的に `--base dev` を指定する。

1. `git fetch origin` 後、`git switch -c feature/<名前> origin/dev` または `fix/<名前>` で作業する。
2. 実装・テスト・commit・push後にdev向けPRを作成する。PRではBackend・Frontend・ContainerのCIを実行する。
3. レビュー・CI成功後にdevへ統合する。devへのpushでも同じCheckを実行し、隔離PostgreSQL、Go/Python結合、フロント、コンテナを検証する。本番Secret・production environmentは使用しない。
4. 複数変更をまとめてdev上で確認し、`gh pr create --base main --head dev` でリリースPRを作成する。最新HEADのレビュー・CIを確認してmainへマージする。
5. mainではProduction deployment内の再利用CIが走る。公開jobはmain限定かつ既存の `PRODUCTION_DEPLOY_ENABLED == true`、production承認を必要とする。現状フラグは未設定で、マージだけでは公開しない。
6. 有効化はユーザーの最終承認後に判断する。承認ゲート、Cloud Run更新、Vercel stage検証、rollbackの確認が必要。手順は[本番デプロイ](production-deployment.md)を参照する。

緊急時はmainから `hotfix/*` を作成し、CIとレビューを経てmainへ反映した後、devへ同期する。通常開発はdevへ集約する。既存の `feat/*` ブランチは一律改名・削除せず、通常PRのbaseをdevへ変更し差分・競合・CIを再確認する。

CheckはPRのbase変更（edited）でも再実行する。benchmarkは既存のPR差分条件と手動実行を維持する。dev pushではCheckが常に全体の統合検証を行い、Production deploymentは起動しない。Vercel Git自動公開無効とmain限定WIFも維持する。

本番DB・SQLite・バックアップをCIの検証対象として書き換えない。AGENTS.mdの共有リンクとアーキテクチャルールは既存構成を維持する。
