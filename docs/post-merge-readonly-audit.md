# PR #75 最終レビュー・マージ後の読取り監査（2026-10-26）

ユーザーはmainマージと読取り監査だけの先行を明示承認した。image push、Cloud Run作成/更新、公開IAM、Vercel昇格、デプロイ有効化、本番DB書込みは承認範囲外であり、実施していない。アプリ・workflow・監査コードは変更していない。この記録は別の文書用ブランチで管理し、mainへ直接コミットしない。

## 固定した対象とマージ結果

- レビュー対象HEAD: `f35a19b2a46b2f98ee9048e51bd82f36d64ddadb`。base: `80ce4fd9b0ca6606f296b644dc3fafd076f59b2c`。PRの差分75ファイルを分類し、実装・テスト・設定・設計/運用文書を確認した。
- マージ直前にHEAD一致、OPEN/MERGEABLE、通常CI成功、repository/production environmentのPRODUCTION_DEPLOY_ENABLEDがどちらも未設定であることをAPIで確認した。
- main pushの対象はdeploy.ymlのみ。backendはmainかつ公開フラグtrueの場合だけ、frontendはbackend成功後だけ動く。check.ymlのSecret監査はmanual専用でworkflow_callではskip。その他のworkflowにmain pushからの公開処理はない。
- `gh pr merge --merge --match-head-commit`で指定HEADを保護してマージ。main SHA: `8718b6ccd8cbde37085a05a135f94d60cf8a512f`。マージ時刻: 2026-10-26 13:31:41 JST。
- [main push run 40269537677](https://github.com/uhey77/grad-checker/actions/runs/40269537677)は成功。ci / backend・frontend・containerは成功、公開用backend/frontendはskip。通常CD・image push・公開は実行されていない。
- [読取り監査run 40269546985](https://github.com/uhey77/grad-checker/actions/runs/40269546985)はmainの上記完全SHAをexpected_shaへ指定して起動。database・wifの両jobが成功し、run全体もsuccess。databaseは2026-10-26 14:07:13 JST、wifは14:07:43 JSTに完了した。承認履歴APIにuhey77のproduction承認2件を確認した。エージェントは保護設定を回避していない。

## 最新HEADのCI証跡

[Check run 40261172564](https://github.com/uhey77/grad-checker/actions/runs/40261172564)と[benchmark run 40261172541](https://github.com/uhey77/grad-checker/actions/runs/40261172541)はいずれもレビューHEAD f35a19bを対象に成功した。過去のSHAの結果で代用していない。

| 確認 | 結果・実行証跡 |
| --- | --- |
| Backend | make backend-check / make backend-testが成功。Python 358 passed、skipなし、既存警告1件 |
| PostgreSQL integration | 同run内のtest_postgres.py 36件と実Go→Python→PostgreSQL HTTP試験2件が成功。TEST_POSTGRES_URLはローカルサービスを指定 |
| Go race | 同backend jobのgo test -race ./...が成功 |
| Frontend | lint/型/整形/テスト/buildが成功 |
| Deployment configuration | 同backendのtest_deployment_configuration.py 6件成功。Nodeデプロイテスト14件も成功 |
| Container | TLS PostgreSQL、Secure Cookie属性、CSRF、本人分離、成績、判定、履歴、再起動保持、依存障害、子プロセス障害を確認。512MiB/1CPU、使用154MiB、peak 170262528 bytes、停止0.42秒 |
| Graduation benchmark | 成功。main push runにはbenchmarkは含まれないため、レビューHEADの独立runを根拠とする |

## 既存3指摘と修正判断

### P1: Cloud Run初回公開

[deploy.yml:57](../.github/workflows/deploy.yml#L57)のservices describeがimage build/pushより前にあるため、初回サービス未作成で通常CDを使うと失敗する。これは制御フローから確定できる条件付きの動作で、本番に試験用サービスを作って再現していない。

[初回公開手順](initial-release-readiness.md)は通常CDを初回に使わず、承認済みmainのイメージ・manifestをレビューして管理者が非公開サービスを作成し、別途公開IAMを承認する方式を定めている。今回フラグ無効でのマージを妨げない。初回作成前に通常CDを有効化しないことが必須。実イメージdigest・初回revision・実originは作成後まで未確定。

### P1: production承認ゲート

[check-release-policy.mjs:12](../scripts/deployment/check-release-policy.mjs#L12)はrequired_reviewersの存在とcustom/main-only branch policyを検査し、現行の設定で実API検査に成功した。ユーザー名そのもの、管理者bypass、自己承認設定、現在のjobに対する承認履歴は検査しない。現在のAPIはreviewer uhey77、main branch 1件、bypass=false、prevent_self_review=falseであり意図した設定と一致する。

両APIのGitHub公式ドキュメントはActions read権限を要求し、deploy/preflightのjobsはactions: readを指定している。contents: readはcheckout用、id-token: writeはWIF jobだけで、frontend/DB監査に渡していない。実GITHUB_TOKENでの確認は上記読取り監査のdatabase/wif両jobで成功し、actions: readで両APIを読めることを実証した。[Environment API](https://docs.github.com/en/rest/deployments/environments#get-an-environment)、[Branch policies API](https://docs.github.com/en/rest/deployments/branch-policies#list-deployment-branch-policies)

**残る保護境界と競合（WARN）:**

- [check.yml:79](../.github/workflows/check.yml#L79)の手動Vercel監査はproduction environmentを使用せず、作業ブランチにrepository SecretのVERCEL_TOKENを渡す。現行スクリプトは固定GETだけで、無改変のmain pushから公開する経路ではない。ただしexpected_shaは呼出側の入力との一致であり、第三者によるレビューの証明ではない。作業ブランチのコード変更と手動実行が可能なWrite権限の主体まで信頼しない場合、Secretをproduction environmentへ移し監査もmainへ限定するか、GET専用の認証へ分離する必要がある。改変コードでのデプロイ/持ち出し試験は実施していない。
- [check-release-policy.mjs:24](../scripts/deployment/check-release-policy.mjs#L24)の環境GETとbranch GETは別々で、cloud操作より前に一度だけ確認する。管理者による実行中の設定変更との原子性は保証しない。設定を後から再追加しても過去のjobが承認済みだった証明にはならない。実行中の設定変更禁止・変更監査を運用に含め、必要なら環境ID/更新時刻やdeployment承認履歴の検査を追加する。実環境を変更する競合試験は行っていない。
- [deploy.yml:144](../.github/workflows/deploy.yml#L144)はstageとpromoteを同じfrontend jobで行う。stage結果を見てから個別承認する初回公開では使用しない。初回は手順どおり手動で分離する。通常CDでも個別の昇格承認を必須にするならpromoteを独立job/workflowへ分ける。

### P2: 本番DB監査の固定行数

[check_release_database.py:16](../backend/scripts/check_release_database.py#L16)と[同:77](../backend/scripts/check_release_database.py#L77)は初回移行直後の18テーブル・1738行に固定されている。ログインでも認証試行/セッションが増えるため、公開後に再利用すると意図的に失敗する。通常deployやruntimeのreadinessからは呼ばれず、初回受入の書込み開始前専用であることも文書化済み。現在の限定監査を妨げない。

推奨: workflow名と説明もinitial migrationに寄せ、継続運用では接続先/TLS/スキーマを確認する別モードまたは既存check_databaseを使う。固定件数の検査を通常運用の成功条件へ組み込まない。

## 実装横断レビュー

- SQLite/PostgreSQL差分は共通engine・UTC日時型・整数/JSON検証式・UPSERT・JSON要約抽出・更新禁止トリガーへ局在している。SQLの値を文字列結合してユーザー入力を埋め込む変更はない。
- readはREPEATABLE READ、writeはREAD COMMITTEDと共通transaction advisory lock。ロック待機後の版照合から更新までを直列化する。例外時rollbackとread時rollbackを維持し、並行登録・復旧・成績/履歴・版競合のPostgreSQLテストが成功している。外部SQLクライアントはアプリのadvisory lockに自動参加しないので、通常運用で直接書き込まない。
- 認証・CSRF・Cookieの公開契約は維持。元の認証情報をコピーし、例外は固定コード/型名へ変換する。Goのブリッジ通信はtimeout、サイズ制限、redirect拒否を維持し、Pythonはloopbackのみ。
- PostgreSQL通常起動は接続/スキーマ検査だけでDDLや既存規則改訂をしない。runtimeはTLS/HTTPSを要求し、SQLite fallbackとDirect URL注入を拒否する。Python準備後にGoを起動し、Go→Pythonの順で停止する。
- /api/healthはliveness、/api/readyは依存接続。DB障害時にreadiness 503・liveness 200となることと、子プロセス終了時の全体失敗をcontainer testが確認している。
- VercelはAPI rewriteをSPAより先に評価し、API/assetsの誤配信を回帰テストで拒否する。実Cloud Run originでのブラウザー、Cookie/CSRF、外部rewrite経由の本人データ動作は公開前後の受入で確認する。
- 移行は読み取り専用の元SQLiteと空のPostgreSQLのみ。親参照順に全件copyし、型復元した全カラムの一致をcommit条件とする。再実行拒否・部分失敗rollback・元SQLite不変をテスト済み。全件メモリ照合は大規模データ向けには未評価だが、今回881行の移行は実測済み。
- 512MiB試験は逐次操作の結果で、同時Argon2負荷や実利用規模の性能保証ではない。初回公開後のmemory/OOM/latency監視を残す。

## 現在のDB・フラグ

マージ後、公式Neon接続の固定production/DBへSELECTだけを実行し、18テーブル・1738行、未検証の外部キー制約0件を確認した。本番へのDDL・データ移行・Seed・アカウント操作は実行していない。元SQLiteと保存バックアップは変更しない。repository/production environmentの公開フラグは未設定を維持する。

## 総合判定

| 項目 | 判定 | 根拠 | 必要な対応 |
| --- | --- | --- | --- |
| コード品質 | PASS | 変更層と依存方向、通常起動と移行の分離、最新CIを確認 | 新たなマージ前必須修正は確認せず |
| DB整合性 | PASS | 既存の全カラム移行照合、PostgreSQL競合/rollback試験、マージ後1738行 | 初期DDL・コピー・Seedを再実行しない |
| セキュリティ | WARN | 現行承認ゲートは有効、Secret非出力とjob権限分離を確認。Write主体/管理者変更の境界は残る | 公開前にSecretの保護境界と設定変更運用を確認 |
| CI | PASS | レビューHEADとmain push双方の通常CI成功 | 本番Secrets/WIFの実認証成功と混同しない |
| デプロイ安全性 | WARN | main pushの公開jobsはskip、初回作成/昇格は手順で分離 | 通常CDを初回に有効化しない。公開操作は別承認 |
| 本番公開準備 | WARN | マージ・DB Secrets/WIFの読取り監査は成功。実サービスは未作成 | 作成・公開IAM・stage・昇格・HTTPS受入を別途承認する |

ユーザー承認に基づく公開無効でのmainマージは完了。公開可とは判定していない。現在の未確認項目は、実サービス起動、公開IAMの組織制約/有効権限、実origin rewrite/HTTPS受入、正常revision/deploymentの確定である。

## 読取り監査の確定結果

| 項目 | 結果 | 根拠 |
| --- | --- | --- |
| production承認 | 成功 | approvals APIがuhey77によるapproved / productionを2件返した |
| GitHub DB Secrets | 成功 | 通常/directの両接続が固定production endpoint・DB/public schema・TLS・全18テーブル件数検査に成功 |
| 件数・読取り専用 | 成功 | ログの制御されたJSONはsource=github-secrets、production_target_verified=true、tables=18、rows=1738、read_only=true |
| GITHUB_TOKEN権限 | 成功 | 両jobでcheck-release-policy.mjsが実API検査に成功。必要なActions read権限を実証 |
| WIF実認証 | 成功 | 固定provider/deployerでgoogle-github-actions/authが成功し、その認証で既存RegistryのGETが成功 |
| Cloud Run inventory | 成功 | 対象project/regionの一覧読取りが成功し、grad-checker-apiは未作成 |
| 公開フラグ | 無効維持 | repository/production environmentの双方で未設定を監査完了後に再確認 |
| 禁止操作 | 未実施 | workflowにはimage push・services replace・公開IAM・Vercel deploy/promote・DDL/移行/Seedがない |

Secret Manager側は23dcc9cを使った認証済みCloud Shellのpass報告、GitHub側は今回のmain実行で実証した。双方が固定された同じproduction endpoint/DBと移行済み18テーブル・1738行に合致する。資格情報文字列やパスワードの同一性を比較したという意味ではない。

監査ログはstdout/stderr全体を成果物へ転載せず、既知の検査JSON・ポリシー成功・固定Registry名・サービス一覧結果だけを抽出して確認した。WIFはread-only APIへのアクセス成立までを実証し、サービス作成・公開IAM変更などの書込み権限や実行時成立までをPASSにしていない。

失敗した監査項目はない。未確認の本番公開作業は、承認済みmain SHAのimage build/pushとdigest記録、非公開Cloud Run作成とRuntime Secret注入/readiness、公開IAM、実originを使うVercel stage、対象deployment指定の本番昇格、HTTPSブラウザーでの専用受入データ操作、メトリクス/費用/ログ確認である。これらは本監査完了をもって自動的に承認されたものと扱わない。
