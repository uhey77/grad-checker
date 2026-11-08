# 開発・リリースフロー

`main` は本番公開用、`dev` は日常開発の統合用。devはPR #78マージ後のmain `9a1ea611374597e27766d934d34311708ecbd9d7` から作成した。
GitHubの既定ブランチはmainを維持するため、PR作成時には明示的に `--base dev` を指定する。

1. `git fetch origin` 後、`git switch -c feature/<名前> origin/dev` または `fix/<名前>` で作業する。
2. 実装・テスト・commit・push後にdev向けPRを作成する。PRではBackend・Frontend・ContainerのCIを実行する。
3. レビュー・CI成功後にdevへ統合する。devへのpushでも同じCheckを実行し、隔離PostgreSQL、Go/Python結合、フロント、コンテナを検証する。本番Secret・production environmentは使用しない。
4. 複数変更をまとめてdev上で確認し、`gh pr create --base main --head dev` でリリースPRを作成する。最新HEADのレビュー・CIを確認し、ユーザーの承認を得てmainへマージする。マージ後は[Release Please](#リリース履歴)がリリースPRを作成・更新する。
5. mainではProduction deployment内の再利用CIが走る。公開jobはmain限定かつ `PRODUCTION_DEPLOY_ENABLED == true` を必要とする。production環境のRequired reviewersを外した後は、mainへのpushでCIが成功すると本番公開へ自動的に進む。
6. 公開可能なbranchはmainだけとする。Cloud Run更新、Vercel stage検証後に本番へ反映する。失敗時は後続処理を停止し、必要なrollbackは承認を受けて実行する。手順は[本番デプロイ](production-deployment.md)を参照する。

緊急時はmainから `hotfix/*` を作成し、CIとレビューを経てmainへ反映した後、devへ同期する。通常開発はdevへ集約する。既存の `feat/*` ブランチは一律改名・削除せず、通常PRのbaseをdevへ変更し差分・競合・CIを再確認する。

CheckはPRのbase変更（edited）でも再実行する。benchmarkは既存のPR差分条件と手動実行を維持する。dev pushではCheckが常に全体の統合検証を行い、Production deploymentは起動しない。Vercel Git自動公開無効とmain限定WIFも維持する。

GitHub Actionsの依存関係は `.github/workflows/actions.lock` で管理する。ワークフローの追加や `uses:` の変更後は、認証済みのGitHub CLIで `gh extension install github/gh-actions-lock --pin v0.4.1` を初回に実行し、リポジトリ直下で `gh actions-lock` を実行して生成された差分を確認する。ロックファイルは手編集せず、変更したワークフローと一緒にコミットする。PRとdevへのpushでは `gh actions-lock --verify` で整合性と依存先を検証する。ロック対象外の再利用ワークフローやコンテナイメージは別途確認する。

本番DB・SQLite・バックアップをCIの検証対象として書き換えない。AGENTS.mdの共有リンクとアーキテクチャルールは既存構成を維持する。

## リリース履歴

mainへのpushで `Release Please` が動き、前回のリリース以降のコミットをまとめたリリースPRをmain向けに作成・更新する。ユーザーがPRのバージョン・変更一覧・CIを確認してマージすると、タグとGitHub Releaseが作成される。dev→mainは個々のコミット履歴を残すmerge commit方式でマージする。最初のリリースは `v1.0.0`、以降はConventional Commitに従い `feat:` はminor、`fix:` はpatch、`feat!:` や本文の `BREAKING CHANGE:` はmajorを上げる。ドキュメントやCIだけの変更では新しいリリースが作成されない場合がある。コミットメッセージの記載漏れは検出できないため、PRレビュー時に変更内容を確認する。

リリースPRが更新する `CHANGELOG.md`、`.release-please-manifest.json`、`version.txt` だけのmainへのpushでは、同じアプリを二重に本番デプロイしない。これ以外のファイルが同じpushに含まれる場合は通常のProduction deploymentを実行する。タグとGitHub Releaseはコードのリリース記録であり、本番デプロイの成功を示さない。対象SHAのProduction deploymentを別に確認する。初回の変更一覧は、準備時のmain `f536e4e76c939456939512d13660bcbf6e8decab` の次からを対象とし、それ以前の履歴へタグを付けない。

Release Please専用のGitHub Appをこのリポジトリだけにインストールし、Contents、Issues、Pull requestsの各Read and writeを付与する。AppのClient IDをrepository variable `RELEASE_APP_CLIENT_ID`、秘密鍵をrepository secret `RELEASE_APP_PRIVATE_KEY` に登録する。Appの認証情報がない場合はRelease Pleaseが失敗するため、mainへの導入前に設定する。短命のインストールトークンはジョブ終了時に失効し、PRのCIを手動承認なしで実行できる。

手動の本番監査・接続確認・復旧試験もproduction承認なしで実行する。復旧試験は過去の正常版・設定を前提とするため、実行前に現在の本番状態と内容を照合し、影響する本番変更についてユーザーの承認を得る。初回構築用の手動ワークフローは廃止する。
