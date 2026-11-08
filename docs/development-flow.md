# 開発・リリースフロー

`main` は本番公開用、`dev` は日常開発の統合用。devはPR #78マージ後のmain `9a1ea611374597e27766d934d34311708ecbd9d7` から作成した。
GitHubの既定ブランチはmainを維持するため、PR作成時には明示的に `--base dev` を指定する。

1. `git fetch origin` 後、`git switch -c feature/<名前> origin/dev` または `fix/<名前>` で作業する。
2. 実装・テスト・commit・push後にdev向けPRを作成する。PRではBackend・Frontend・ContainerのCIを実行する。
3. レビュー・CI成功後にdevへ統合する。devへのpushでも同じCheckを実行し、隔離PostgreSQL、Go/Python結合、フロント、コンテナを検証する。本番Secret・production environmentは使用しない。
4. 複数変更をまとめてdev上で確認し、`gh pr create --base main --head dev` でリリースPRを作成する。最新HEADのレビュー・CIを確認し、ユーザーの承認を得てmainへマージする。マージ後は[リリース履歴](#リリース履歴)を自動で記録する。
5. mainではProduction deployment内の再利用CIが走る。公開jobはmain限定かつ `PRODUCTION_DEPLOY_ENABLED == true` を必要とする。production環境のRequired reviewersを外した後は、mainへのpushでCIが成功すると本番公開へ自動的に進む。
6. 公開可能なbranchはmainだけとする。Cloud Run更新、Vercel stage検証後に本番へ反映する。失敗時は後続処理を停止し、必要なrollbackは承認を受けて実行する。手順は[本番デプロイ](production-deployment.md)を参照する。

緊急時はmainから `hotfix/*` を作成し、CIとレビューを経てmainへ反映した後、devへ同期する。通常開発はdevへ集約する。既存の `feat/*` ブランチは一律改名・削除せず、通常PRのbaseをdevへ変更し差分・競合・CIを再確認する。

CheckはPRのbase変更（edited）でも再実行する。benchmarkは既存のPR差分条件と手動実行を維持する。dev pushではCheckが常に全体の統合検証を行い、Production deploymentは起動しない。Vercel Git自動公開無効とmain限定WIFも維持する。

本番DB・SQLite・バックアップをCIの検証対象として書き換えない。AGENTS.mdの共有リンクとアーキテクチャルールは既存構成を維持する。

## リリース履歴

mainへのpushで `Release history` が起動し、対象コミットに注釈付きタグを付け、GitHub Releasesに変更一覧を自動公開する。通常は複数のPRをまとめたdev→mainのリリースPRをマージすることで起動する。緊急修正のmainへのマージも対象とする。タグはマージ済みのコードの記録であり、CIや本番デプロイの成功を示さない。本番への反映状況は同じSHAの `Production deployment` の結果で別に確認する。タグのpushはmainへのpushではなく、本番デプロイを起動しない。

バージョンは `vMAJOR.MINOR.PATCH` 形式で、最初の自動リリースは `v1.0.0` とする。以降は前回のタグから対象コミットまでの全コミットメッセージを確認し、優先順位の高い変更に合わせる。

- `feat!:` や `feat(api)!:` のような `!`、件名の `feat: BREAKING CHANGE: ...`、または本文の `BREAKING CHANGE:` / `BREAKING-CHANGE:` がある場合はMAJORを上げる。件名に記載する方法は、このリポジトリの1行コミット規則にも従う。
- それ以外で `feat:` / `feat(api):` がある場合はMINORを上げる。
- それ以外の修正、文書、設定などはPATCHを上げる。

自動判定はコミットメッセージに依存する。特に破壊的変更の記載漏れは検出できないため、PRレビュー時に内容とメッセージを確認する。複数変更がある場合は最も大きい変更に合わせ、バージョンを一度だけ上げる。

同時期のmain更新により未処理の実行が飛ばされた場合、次の実行は既存の最新タグからmainの第一親履歴をたどり、未記録のコミットを古い順に処理する。タグは作成済みでReleaseだけ失敗した場合も再実行で補完する。自動生成の変更一覧はGitHub側の抽出結果に依存するため、初回を含め必要に応じてGitHub上で確認・編集する。公開済みタグは移動・上書きせず、修正は新しいバージョンで記録する。失敗した場合は `Release history` のログを確認し、原因を解消して該当実行を再実行する。自動リリース開始前の過去のmain履歴は遡ってタグを付けない。

手動の本番監査・接続確認・復旧試験もproduction承認なしで実行する。復旧試験は過去の正常版・設定を前提とするため、実行前に現在の本番状態と内容を照合し、影響する本番変更についてユーザーの承認を得る。初回構築用の手動ワークフローは廃止する。
