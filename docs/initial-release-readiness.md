# 初回公開の準備と承認対象（2026-10-26）

Phase 1・2の実測結果と、Phase 3へ進む条件を管理する。本番DDL・SQLite移行・シードは再実行しない。旧SQLiteへの書込み再開は禁止。mainマージ、Cloud Run作成・公開、Vercel昇格、デプロイ有効化は未実施。

## 現在の判定

| 項目 | 結果 |
| --- | --- |
| PR #75 | 準備開始時のhead `8e580cfc0916fcc10a58b5512e80e04b075e81cb`はMERGEABLE/CLEAN、通常CI全成功。手動vercel-auditは仕様どおりskip。今回の準備コード追加後のCIは別途確認する |
| production承認 | reviewer `uhey77`、mainのbranch 1件のみ、管理者bypass無効、Prevent self-review無効。実APIと既存ポリシースクリプトで再確認 |
| Neon本番 | project `plain-smoke-97118898` / production `br-calm-water-a1uug5fd` / DB `grad-checker`。全18テーブルをSELECTで再集計し、[移行記録](production-neon-migration-2026-10-26.md)の各件数・合計1,738行と一致 |
| Neon接続 | 公式接続機能で取得した資格情報を画面・ログ・ファイルへ保存せず検査。直接/pooledともTLS・スキーマ・18テーブル/1,738行を確認。GitHub/Secret Managerに保存された接続値の証明とは区別する |
| GitHub Secrets | DATABASE_URL / DIRECT_DATABASE_URL / VERCEL_TOKENは登録済み。production environment secretsに上書きはない。値はREST APIで取得できず、保存値の接続先は未実証 |
| GCP | この実行環境にgcloud・GCP認証がない。2026-10-23の認証済みCloud Shell監査実績は保持するが、現在のmetadata/IAM/Secret値・WIF実認証を確認済みとしない |
| Vercel公式接続 | チーム認可をユーザーが完了し、同じ接続で対象Project/production deploymentのGETが成功。以前の403は解消 |
| Vercel固定対象 | CLI/APIでProject `prj_QgFMi1xMYgrYLGPI1Yi9h0kdkNzW` / Team `team_tZDGBnNdyZxvlZvkV86h6SGv`、Root frontend、Node 24.x、Vite、build `npm run build` / install `npm ci`を確認。Git linkなし、自動deploy無効 |
| 実API rewrite | ソースと回帰テストでAPI優先・SPA除外・no-storeを確認。現在の公開画面は旧初期deploymentで、実Cloud Runへのrewrite/readinessは未成立。初回サービスの実URL取得後に生成ビルド出力とstageで検証する |
| 公開フラグ | PRODUCTION_DEPLOY_ENABLEDは未設定を維持。初回操作を既存deploy.ymlの一括処理で代用しない |

[GitHubのSecret取得API](https://docs.github.com/en/rest/actions/secrets#get-a-repository-secret)は値を返さない。main限定のproduction environmentを緩和せず、マージ前にそのmain用workflowから既存GitHub Secretsを検証することはできない。したがって「Secret照合完了後に初めてmainマージ」という順序は現在の保護設定と両立しない。別途承認されたmainマージ後に公開フラグを未設定のまま読取り監査を行うか、既存の同等に保護された監査経路を用意する必要がある。今回、例外としてマージしたり保護を緩めたりしていない。

## ローカル暗号化バックアップ

ユーザー指定により今回はローカルコピーまでとし、外部転送しない。

- 暗号化アーカイブ: `/root/.local/share/grad-checker/backups/production-20261026/migration-backup.tar.gz.enc`
- 鍵: `/root/.local/share/grad-checker/backup-keys/production-20261026.key`。鍵の値は記録しない。
- manifest: 同バックアップディレクトリの`manifest.json`。
- AES-256-CBC、saltあり、PBKDF2-SHA256 / 600,000 iterations。ディレクトリ0700、鍵・暗号化アーカイブ・manifestは0600。
- アーカイブSHA-256: `871998ca861807fea861f83d9b7d536cedd0f9da3da2384faf30b770c7baf3e6`。
- source-latest / migration-source / seed-validationの3DB、DDL、既存の移行証跡を含む。接続ファイルは含まない。別の非公開一時ディレクトリへ復号し、全メンバーのSHA-256一致を確認後、一時平文を削除した。
- 原本・既存バックアップは不変。鍵と暗号文は同一ホスト上の別ディレクトリなので、ホスト全体の喪失への保護にはならない。
- 保持期間は未指定。手動保管を継続し、自動削除を設定しない。90日以上を案とし、削除前には保持期間・切替後の正常性・別の復旧可能なバックアップを確認して個別承認する。

復号は`openssl enc -d -aes-256-cbc -pbkdf2 -iter 600000 -md sha256 -pass file:<鍵ファイル> -in <暗号文> -out <0700の一時ディレクトリ内のファイル>`を使う。鍵の値を引数へ埋め込まない。復号先をGit管理下に置かず、検査時も元DBへ書き戻さない。

## 認証済みCloud Shellでの読取り監査

ユーザーはCloud Shellでの監査を選択済み。PRの今回の準備コミットをレビューし、提示された40桁SHAをcheckoutして実行する。マージ・リソース作成・IAM変更を伴わない。

```sh
# REVIEWED_SHAには今回の準備コミットの完全SHAを指定する。
AUDIT_DIR="$(mktemp -d "$HOME/grad-checker-preflight.XXXXXX")"
git clone --single-branch --branch feat/production-deployment https://github.com/uhey77/grad-checker.git "$AUDIT_DIR/repo"
cd "$AUDIT_DIR/repo"
git checkout --detach "$REVIEWED_SHA"
test "$(git rev-parse HEAD)" = "$REVIEWED_SHA"
python3 scripts/deployment/audit-gcp-initial.py
uv run --locked --project backend python -m scripts.check_release_database --secret-manager
```

uvがなければ既存の方法で`uv==0.13.1`を用意する。Python 3.15はuvが解決する。2つの監査結果だけを共有し、gcloudのSecretアクセスを単独実行して出力を貼り付けない。

- GCP metadata監査は既存Registry、Runtime/Deployer SA、main限定WIF、Deployerのrun.developer / Registry writer / Runtime SAのserviceAccountUser / WIF IAM、通常SecretのRuntime Accessor、両Secret version 1のenabled、Cloud Run未作成を確認する。
- Secret Manager監査は通常/directの固定Secret version 1をgcloud subprocessのstdoutからメモリ内だけで読み取り、同じ本番endpoint/DB/public schema・TLS・全テーブル件数を検査する。SQLはREPEATABLE READの読取り専用トランザクションで実行し、DB初期化・移行・Seedを呼ばない。
- Direct Secretを読む主体は権限を持つ監査用の管理者とする。今回の検査のためにRuntime/DeployerへDirect Secret権限を追加しない。
- 上位階層からのDirect Secret権限継承とallUsersを許す組織ポリシーはmetadata監査の自動判定対象外。公開前に管理者が有効権限と組織ポリシーを確認する。
- 出力は合否・集計だけ。失敗時は例外・SQL・接続URL・gcloud stdout/stderrを抑制する。失敗は未確認のまま停止して扱う。

`check_release_database`の1,738行検査は初回受入の書込み開始前専用。公開後は認証試行・セッション・成績・履歴の増加が正常に起きるため、通常監視の固定件数判定には使用しない。

## 承認済みmainでのGitHub SecretsとWIF監査

追加した`production-preflight.yml`は手動のみ、repository/main/入力完全SHAの一致とproduction承認を必須にする。通常PR・workflow_callでは実行しない。

1. GitHubの通常/direct Secretsを上記と同じ固定endpoint/DB・TLS・18テーブル/1,738行の検査に通す。Secret値はログ・artifactへ出さない。DB監査jobにid-token権限を渡さない。
2. 成功後、別runner・production再承認でWIF実認証を行い、固定の既存RegistryとCloud Run inventoryを読む。DB SecretをWIF jobへ渡さない。
3. image push、サービス作成、公開IAM、Vercel deploy/promote、有効化フラグ変更は行わない。

Cloud ShellのSecret Manager監査とActionsのGitHub Secrets監査が両方成功して初めて、保存された接続先の一致を確認済みとする。現時点では両方の実行結果待ち。

## 初回作成・公開の確定手順（未実行）

### 個別承認A: mainマージと読取り監査

最新CI・差分を再確認したPR #75をmainへマージする。PRODUCTION_DEPLOY_ENABLEDは未設定を維持し、公開しない。マージ後の完全SHAを固定し、`production-preflight.yml`へexpected_shaを指定して手動実行する。現在のPhase 1の順序からこの手順を先行させる場合は、その例外も明示承認に含める。

### 個別承認B: イメージpush・Cloud Run初回作成・公開IAM

- 対象はGCP `grad-checker-512505` / `asia-northeast1` / Registry `grad-checker` / Cloud Run `grad-checker-api`。
- イメージ名は`asia-northeast1-docker.pkg.dev/grad-checker-512505/grad-checker/api:<承認済みmainの40桁SHA>`。既存Dockerfileを使ってビルド・pushし、Registryのdigestを実行記録へ保存する。現時点ではmain SHAとpush後digestは未確定。DB・バックアップ・環境ファイルは.dockerignoreで除外する。
- `DEPLOY_IMAGE`に上記のタグを指定し、`python scripts/deployment/render_cloud_run.py`でマニフェストを生成、レビューする。`gcloud run services replace`による初回作成は非公開。Runtime SAは`grad-checker-runtime`、通常DB Secret version 1のみを注入する。
- 設定は1CPU / 512MiB / min 0 / max 1 / concurrency 4 / request-based / startup boost無効。livenessは/api/health、startup/readinessは/api/ready。PUBLIC_ORIGINは`https://grad-checker-chi.vercel.app`。
- 既存SAでの作成にはCloud Run Developer、Runtime SAのService Account User、イメージ読取り権限が必要。image pushにはRegistry writerが必要。通常CDの権限を広げて代用しない。[Cloud Run公式デプロイ要件](https://docs.cloud.google.com/run/docs/deploying)
- 非公開のReady状態と認証付き疎通を先に確認する。必要なら権限を持つ管理者の`gcloud run services proxy grad-checker-api --project grad-checker-512505 --region asia-northeast1 --port 18080`からローカル/api/readyを確認し、終了後proxyを止める。
- Vercelの通常rewriteはCloud RunのInvoker認証を付けないため、APIの公開承認後に管理者が対象サービスへ`allUsers`の`roles/run.invoker`を追加する方針とする。対象サービスのsetIamPolicy権限が必要。組織ポリシーに拒否されたら停止し、別方式を無断で選ばない。[公開アクセスの公式手順](https://docs.cloud.google.com/run/docs/authenticating/public)
- Cloud Run作成・Registry保存・起動/処理・転送・ログ等の費用が発生し得る。min/max設定は費用上限を保証しない。初回作成前に請求先の利用枠・予算通知先を確認する。

既存deploy.ymlはサービス存在確認後にimage pushするため、初回未作成の状態では使えない。初回は上記の管理者手順で作成する。通常CDへの切替・有効化は初回公開成功後の別承認とする。

### 個別承認C: Vercel stage検証と本番昇格

1. 既存Project/Teamを再確認する。実Cloud Run status.urlをCLOUD_RUN_API_ORIGINへ渡す。DB資格情報をVercelへ設定しない。
2. 固定CLI 65.2.0の`vercel pull --environment=production`をumask 077で実行。`verify-frontend-env.mjs`を通し、`vercel build --prod`後に`verify-vercel-output.mjs`で実API origin・パス・SPA除外・no-storeを検証する。
3. `vercel deploy --prebuilt --prod --skip-domain`でstageする。deployment URL・ID・commitを記録する。project/target/出力先が一致することを再確認する。
4. `vercel curl`でstageの/api/readyのJSONとSPA直接URLを検証する。PUBLIC_ORIGINが本番画面に固定されているので、stageから本番利用者としてログインする検証は行わない。
5. stage結果を提示し、当該deployment IDを指定した個別承認後だけ`vercel promote`する。既存deploy.ymlのfrontend jobはstageとpromoteを一括実行するため、初回の個別承認では起動しない。
6. 本番HTTPSで/api/ready、Cookie/CSRF、登録・復旧・ログイン、成績・卒業判定・履歴・本人限定アクセスを検証する。専用の受入アカウント等の追加書込み範囲も公開承認で明示し、既存アカウント・元の1,738行を編集・削除しない。

## ロールバックと公開後確認

- 現在のVercel productionは`dpl_sxePucHULpSAqZfZ4QyXow4DbCKt` / `grad-checker-5m59zzu0r-kanade3256s-projects.vercel.app`。API対応前の初期画面なので、画面を元へ戻す候補であり、正常なAPIの復旧先として認定しない。
- 初回Cloud Runには直前の正常API revisionがない。初回障害時はVercel昇格を止め、必要なら承認済みの障害対応範囲でallUsers bindingを除去してAPI公開を止める。サービスやDBを削除しない。
- 公開が成功した時点でCloud Runの正常revision/digestとVercel deployment IDを記録する。次回以降は対応するrevisionへtrafficを戻し、対応するVercel deploymentへrollbackする。DB差分は保全し、DDL・SQLiteコピー・Seed・初期化を行わない。
- 昇格前に不調ならstageを昇格しない。昇格後に問題が出たら正常revision/deploymentへ戻すか、初回は公開停止を判断する。Vercel rollback後の自動ドメイン割当状態も確認する。
- 公開後はCloud Run Ready / 5xx / latency / memory / OOM、Neon接続・compute、Vercel API中継エラー、GCP Billing/Registry/Secretアクセス/ログ量を確認する。ログ本文やCookie・SQLパラメーター・資格情報は成果物に貼り付けない。

公開全体の承認依頼は、Cloud Shell監査結果、GitHub Secrets監査の順序解決、最新CI、対象main SHA・イメージdigest、公開権限主体、Vercel stage結果が揃った時点で操作ごとに行う。現時点で公開可能とは判定しない。
