# PR #75 本番移行前の監査

初回監査日: 2026-10-23、承認ゲート再監査日・本番DB移行日: 2026-10-26（日本時間）。対象は`feat/production-deployment`。ユーザーの明示承認後、本番DBへ18テーブル作成・881行移行・卒業要件857行追加を実施し、照合に成功した。詳細・現在のDB状態・復旧手順は[本番Neonデータ移行の実行記録](production-neon-migration-2026-10-26.md)を参照する。以下のリハーサル・実行前準備は過去の実測記録として保持する。本番デプロイ、mainマージ、PRODUCTION_DEPLOY_ENABLED変更は行っていない。

## Vercel

| 項目 | 実環境の結果 |
| --- | --- |
| Project / Org | `prj_QgFMi1xMYgrYLGPI1Yi9h0kdkNzW` / `team_tZDGBnNdyZxvlZvkV86h6SGv` |
| Project / owner scope | `grad-checker` / `kanade3256s-projects` |
| Root / Node / Framework | `frontend` / `24.x` / `vite` |
| Build / Install / Output override | `npm run build` / `npm ci` / `null`（Vite既定dist） |
| Git | `link: null`、`createDeployments: disabled`、`disableRepositoryDispatchEvents: true` |
| ローカルCLI | 65.2.0のproject inspectと固定Project IDへのGETが成功 |
| GitHub Secret | [手動監査39925387272](https://github.com/uhey77/grad-checker/actions/runs/39925387272)で既存VERCEL_TOKENのGETが成功 |
| 公式プラグイン | 同じteam/projectへのGETは403。team一覧も空。`saml=false`、`ssoEnforced=false` |

403は公式プラグイン接続の対象チーム認可に局在している。CLIとGitHub Secretの対象チームへのアクセスは成功しているため、プロジェクト削除・新規作成・トークン交換を解決策として実施していない。エラーの回復指示は`authorize_team_access`だが、このセッションにはそのツールが公開されていない。プラグイン側で対象teamの認可リンクを発行可能にする対応が必要。再接続やSSOが原因だとは断定しない。

既存設定を`vercel pull --environment=production`で取得し、公開せず`vercel build --prod`を実行した。install auditは0 vulnerabilities、ビルドは成功。`vercel.mjs`から生成された`.vercel/output/config.json`にAPIの外部rewrite、API/assetsを除外したSPA fallback、API no-storeが存在することを検証した。未作成のCloud Runの代わりに検証用`https://grad-checker-audit.invalid.run.app`をビルド時だけ使用したため、実サービスへの疎通は証明していない。Git自動公開無効は実プロジェクト設定とソース設定を別々に確認した。

手動トークン監査は既存Check workflowの`workflow_dispatch`だけから実行する。監査モード、既知の作業ブランチ、repository、手動指定した完全SHAとgithub.shaの一致を必須にし、PR/再利用可能CIでは実行しない。固定URLのGETだけを行い、Tokenの出力・artifact化・外部への持ち出し、WIF、DB Secret、deployを行わない。監査時は通常テストジョブをskipする。通常PRのCIは引き続き本番Secretを使わない。

## GitHubと承認ゲート

- 認証アカウントは`kanade3256`、repository permissionはWrite。Admin/Maintainはない。
- 2026-10-23時点の`production` GET 404・未構成という結果を更新した。2026-10-26にGitHub REST APIの`GET /repos/uhey77/grad-checker/environments/production`と`GET /repos/uhey77/grad-checker/environments/production/deployment-branch-policies`が成功し、保存済み設定を確認した。

| API項目 | 保存済みの値 | 判定 |
| --- | --- | --- |
| `required_reviewers.reviewers` | User `uhey77` 1名 | スクリプトの「1名以上」を満たす |
| `deployment_branch_policy.custom_branch_policies` | `true` | custom制限を満たす |
| `deployment_branch_policy.protected_branches` | `false` | selected branch方式 |
| `branch_policies` | `total_count: 1`、`name: main`、`type: branch`のみ | main限定を満たす（tag・wildcardなし） |
| `can_admins_bypass` | `false` | 管理者による回避無効を確認 |
| `required_reviewers.prevent_self_review` | `false` | 自己承認可能という管理者設定と一致 |

`production`のIDは`25134972216`、APIの`updated_at`は`2026-10-23T13:33:08Z`。設定変更ではなくGETによる再確認である。`check-release-policy.mjs`は承認者の存在とmain限定を検証するが、承認者のlogin、管理者bypass、Prevent self-reviewは検査しないため、それらはAPIの値を別途照合した。独立した別人の承認を必須とする設定ではない。

既存CLI認証を値非出力で`GH_TOKEN`へ渡し、ローカルで`GITHUB_REPOSITORY=uhey77/grad-checker`、`GITHUB_REF=refs/heads/main`を検証入力として、変更していない`node scripts/deployment/check-release-policy.mjs`を実APIに対して実行した。終了コード0、`Production approval and main branch policy verified`を確認した。これはmainでのActions実行やWIF実認証、Actionsの`github.token`でのAPI読取りを証明するものではない。`node --test scripts/deployment/test-release-policy.mjs`も3件成功した。

- 既存のGCP/VERCEL Variablesはワークフローの固定ターゲットと一致。DATABASE_URL、DIRECT_DATABASE_URL、VERCEL_TOKENは登録済み（値は取得していない）。PRODUCTION_DEPLOY_ENABLEDは未設定のまま（2026-10-26にrepository variables全件とproduction environment variables全件を再確認、environment variablesは0件）。
- deploy backendはmainかつ有効化フラグがtrueの場合だけproduction environmentで動作し、ポリシー検査の後にWIFを実行する。frontendはbackend成功に依存し、別runner・production environment・再検査を使いid-token権限を持たない。
- database-connectivityはmainの手動実行、production environment、ポリシー検査を経てからDB Secretを使用する。SELECT 1のみでDDL・Seedをしない。
- environmentがない状態でworkflowを動かして暗黙作成することや、WIFのmain条件を緩和することは行っていない。

管理者による承認ゲート設定は完了し、現行スクリプトの条件を満たす。この段階ではPRODUCTION_DEPLOY_ENABLEDを変更しない。Writeアカウントへのrepository Admin付与は不要。

## Google Cloud

GCPの静的設定監査は完了。根拠は、2026-10-23（日本時間）にユーザーが認証済みGoogle Cloud Shellで確認した以下の結果。このエージェント環境での実認証・実行検証を示すものではない。

| 項目 | 確認結果 |
| --- | --- |
| GCP Project | `grad-checker-512505` |
| Artifact Registry | `grad-checker`（`asia-northeast1`）が存在 |
| Cloud Run | 現時点でサービス未作成 |
| WIF Provider | `github-provider`が存在 |
| WIF条件 | `uhey77/grad-checker`の`main`限定 |
| Runtime SA | 存在・有効 |
| Deployer SA | 存在・有効 |
| DeployerのCloud Run権限 | `roles/run.developer` |
| Artifact Registry IAM | Deployerに`roles/artifactregistry.writer` |
| Runtime SA IAM | Deployerに`roles/iam.serviceAccountUser` |
| WIF IAM | Deployerに`roles/iam.workloadIdentityUser` |
| 通常DB Secret | Version 1がenabled、Runtime SAに`secretAccessor` |
| Direct DB Secret | Version 1がenabled、Secret単位のIAMバインディングなし |

Direct DB Secretの確認はSecret単位のIAMバインディングがないことまでで、上位階層から継承される権限の不存在を示すものではない。Secret値は本監査文書へ記録しない。Direct SecretはWebに渡さない。

以下は静的設定監査の完了とは分けて、未検証のまま管理する。

- GitHub ActionsからのWIFの実認証。
- 本番DBへの接続。
- 通常DB Secret・Direct DB Secretの値が指す実際の接続先。
- Cloud Runの起動、Secret取得、readinessと実サービスへの疎通（サービス未作成）。

このエージェント環境で以前行った読み取りAPI呼出しは、Cloud RunとSecret metadataが401、Artifact Registry・WIF Provider・Service Accountが403で認証できなかった。これらはリソース不存在や権限不足の証拠ではなく、今回の認証済みCloud Shellによる静的設定確認で更新した。WIF条件の緩和、鍵作成、Secret値の取得、本番リソースの作成・変更は今回行っていない。

## NeonとSQLite

2026-10-26追記: 承認済みの本番移行が完了し、現在は18テーブル・1,738行。元SQLite・保存バックアップは不変、全カラム照合・参照整合性・読取り判定検証が成功した。以下の空DB・881行リハーサルは2026-10-23の記録。[今回の本番実行記録](production-neon-migration-2026-10-26.md)が現在の状態を示す。

Neon公式プラグインで既存project `plain-smoke-97118898`、Freeプラン、PostgreSQL 18、Singapore regionを確認。開始時に存在したのはproduction `br-calm-water-a1uug5fd`だけで、publicテーブルは0だった。

ユーザーの個別承認後に`rehearsal/pr-75`（`br-delicate-sky-a1cmdbb8`）を作成した。computeは0.25 CU固定、期限は2026-10-24 17:36:03 JST。Freeプランではsuspend interval指定がHTTP 412で拒否されたため、ブランチ未作成を確認してからinterval指定を省いて作成し、既定値を維持した。プラン変更はない。共有compute/storage/転送枠を消費する。料金・枠は[Neon公式プラン](https://neon.com/docs/introduction/plans)を参照。

Neon CLIはブラウザー認証がタイムアウトし、ローカルcallbackが手元のブラウザーから到達できなかった。認証済み公式プラグインで継続した。MCPが返したpooled接続から、取得済みcompute metadataにあるdirect hostへ切り替えて移行した。資格情報は権限0600のGit管理外一時ファイルに保存し、引数・ログへ実値を渡していない。

元SQLiteはbackup APIでWALを含む整合したバックアップにした。元の11テーブルには既存データ881行があり、卒業要件・履歴関連7テーブルがないため、未加工バックアップは移行前スキーマ検査で拒否された。別の作業コピーに既存のSQLite初期化処理を適用して不足テーブルを追加し、元の11テーブルの全行・全カラムが変化していないことを照合した。元DBと最初のバックアップは変更していない。

実データに卒業要件と判定履歴がないため、移行成功だけでは本番用卒業要件データの準備完了を意味しない。必要な出典付き規則データの確認・importは本番書込みとして別承認が必要で、今回自動投入していない。認証・成績・判定・履歴の業務動作は別スキーマの合成データで追加検証する。

### リハーサル実行結果

- 実バックアップ881行を18テーブルへコピーし、全テーブル・全カラムを照合してcommitした。スキーマ作成とデータ移行のread-only planも成功した。
- 再実行は既存データを検出して拒否し、拒否前後の全テーブル内容が一致した。
- 元のバックアップのSHA-256は不変。pooled接続でPythonの起動・readinessも成功した。クライアントのTLSはpsycopgのssl_in_useで確認した（Neon proxyの内側を示すpg_stat_sslだけではクライアントTLSの判定にならなかった）。
- 別スキーマの合成データで既存の移行互換性テストを実行し、認証情報・セッション・CSRF・成績・保存済み判定履歴の移行保持を確認した。
- 別スキーマの実Go → Python → Neon HTTP試験で登録・ログイン・復旧・セッション失効が成功した。
- 別スキーマの実HTTP試験で成績保存、卒業判定pass、履歴保存・一覧・読取り、版競合409、別ユーザーからの履歴アクセス404を確認した。
- 最後にproductionのpublicテーブルが引き続き0であることを公式プラグインで確認した。本番へDDL・Seed・データコピーを行っていない。

移行後の実データ件数：

| テーブル | 行数 |
| --- | ---: |
| academic_programs / curricula | 6 / 4 |
| classifications / courses | 68 / 131 |
| course_offerings / curriculum_courses | 161 / 498 |
| students / student_credentials / auth_sessions / auth_attempts | 1 / 1 / 1 / 4 |
| grade_attempts | 6 |
| graduation_requirements / requirement_scopes / credit_rules | 0 / 0 / 0 |
| credit_rule_courses / credit_rule_limits / completion_policies / check_results | 0 / 0 / 0 / 0 |

共有用の成果物には資格情報・個人情報・バックアップDBを含めていない。接続用一時ファイルは試験後に削除する。バックアップはGit管理外の権限0600ファイルで保持し、隔離Neonブランチは指定期限で失効する。

## 変更と検証

- Vercelの実ビルド出力をstage前に検証するスクリプトと正常/誤配信の回帰テスト。
- 既存GitHub Secretによる固定Project/Orgへの手動GET監査と、対象不一致・自動公開有効・403を拒否するテスト。
- SQLite backup APIによるスナップショット作成。WAL、既存保存先の保護、元ファイル未作成、外部キー不正の4テストが成功。
- Cloud RunのSecret参照・資源上限・probe、WIF前の承認ゲート、DB接続試験のmain/Secret制限、監査の手動/完全SHA制限、イメージ固定ターゲットの5契約テストが成功。
- Nodeデプロイ関連テスト14件とactionlintが成功。既存プロジェクト設定を使用したVercel CLI 65.2.0の本番用ローカルビルドと生成routes検証も成功。
- 既存のStarlette TestClient/httpx非推奨警告とuv-buildのバージョン範囲に関する警告は残るが、今回の検証失敗ではない。

## 承認前の移行準備（2026-10-26、実行前記録）

承認ゲートの未構成は解消した。次は移行対象と照合条件を確定する。今回の準備は既存文書・ソースとGitHubの読取り確認までで、本番接続・クラウド操作・workflow dispatchは行っていない。

| 準備項目 | 現状と次に必要な確認 |
| --- | --- |
| PR・CI | PR #75はOPEN、対象head `0d50b56c03817d115b4463736a01267a539d4cae`のbackend/frontend/container/benchmarkは成功、手動vercel-auditはskip。今回の文書更新後のCIは別途確認する |
| 本番移行元 | 881行のリハーサル実績は保持する。切替時の最終バックアップ、書込み停止時点、SHA-256、18テーブルの件数・全カラム照合、所要時間を実行記録として揃える。最終バックアップと移行所要時間の確定値は未確認 |
| 卒業要件 | リハーサル元には要件・規則が0行。[卒業要件マスタ](../backend/seeds/requirements.md)と`cs_requirements_2026.json`には要件80・対象集合492・規則16・換算対象265・共通上限4がある。コピーだけでは判定用データが揃わないため、採用するシードと投入範囲・順序を本番書込みの承認対象に含める |
| 出典上の未確認 | 適用入学年度はunverified/null。他学部4規則の正式な配分順序と対象科目転記は未確認。現行の2026年度便覧を使う運用・アプリ配分方針を維持し、確認済みとして補完しない |
| 移行先・接続 | 既存Neon productionの対象DB、空状態、通常/direct接続の同一接続先・TLS、Secret Manager参照先の一致を実行直前に確認する。2026-10-23の空状態を現在の実測として扱わない。接続値を文書・ログへ保存しない |
| WIF・DB接続 | main限定を維持する。`database-connectivity.yml`はmain手動実行・production承認後のSELECT 1のみ。今回はmainマージ禁止のため実行しない。作業ブランチでmainのWIF認証を代用しない |
| 承認用の変更資料 | [移行手順](../backend/migrations/README.md)の接続不要なDDL出力、移行元/先と照合結果、必要な要件import、失敗時の保全手順を揃えてから、本番DDL・コピー・Seed・mainマージを個別に提示する |

デプロイ関連Nodeテスト14件と`git diff --check`が成功。本番DB変更、mainマージ、Cloud Run作成・公開、Vercel公開、デプロイ有効化は未実施。公開可否の判定には上記の未確認項目と実環境受入が残る。

## 初回公開までの順序

2026-10-26追記: 本番DDL・データコピー・既存CS要件シード投入は個別承認を得て完了した。以下の順序のうちDB移行分は[実行記録](production-neon-migration-2026-10-26.md)で更新済み。mainマージ・本番公開・デプロイ有効化への承認は含まない。

1. このPRの差分・CI・監査結果を確認する。mainへのマージは禁止のまま維持する。
2. GitHub productionのreviewer/main制限は2026-10-26の実API検証で完了。GCPの静的設定監査は完了済み。WIF実認証・本番DB接続・Secret値の接続先・Cloud Run起動は未検証として後続で確認する。Vercel公式プラグインのteam認可は別に解決する。CLI/Actionsによる対象確認は成功済み。
3. 本番に必要な卒業要件データ、移行元バックアップ、移行先、照合結果、所要時間を確認する。実アカウントのパスワードや復旧コードは収集しない。
4. mainへのマージ、DBの初期DDL、データコピー、必要な規則importをそれぞれ影響とともに提示し、個別の本番承認を得る。
5. 承認後のmainでWIFを検証し、承認されたSHAイメージを既存Registryへpushする。初回Cloud Runマニフェストをレビューする。実サービス作成は今回行わない。
6. 初回サービスは非公開で作成し、Runtime SA・通常Secret version 1・TLS・readiness・起動ログを確認する。Vercelの通常rewriteは認証付きCloud Run呼出しを付与しないため、公開APIとしてのInvoker IAM設定は別承認後に管理者が一度だけ行う。run.developerのDeployerへ広いrun.adminを付けて代用しない。
7. Vercelの実Cloud Run originでビルドし、未昇格deploymentでAPI中継・SPAを確認する。本番公開、有効化フラグの変更、promoteは別の明示承認後に行う。
8. HTTPSブラウザーでCookie/CSRF、登録・復旧・ログイン、成績の編集、卒業判定、本人限定履歴、再デプロイ後の保持を確認する。試験用データ書込みも承認された範囲に限る。
9. 異常時は対応する既知の正常Cloud Run revision/Vercel production deploymentへアプリだけを戻す。DBは削除・初期化せず差分を保全する。初回公開で正常revisionがない場合は公開停止を判断し、DBを残して原因を調査する。

マニフェストの1CPU・512MiB・min 0/max 1・concurrency 4・request-based・startup boost無効、通常Secretのみ、起動ready/liveness分離は契約テストで検証している。GCPの静的設定・IAMは認証済みCloud Shellで確認済み。実クラウドのAPI validation、WIF実認証と実行時のIAM成立、Secret値の接続先、本番DB接続、Cloud Run起動は未検証。最小0/最大1でも費用上限は保証しない。Cloud Runのリクエスト・起動/処理時間・転送、Registry保存量、Secretアクセス、ログ量が費用要因であり、[Cloud Run公式料金](https://cloud.google.com/run/pricing)と請求アカウントの利用枠を初回作成前に確認する。今回はCloud Run/Registry/IAM/Budgetの作成・変更を行っていない。
