# 初回本番公開の実行監査（2026-10-26）

## 最終結果

本番公開とHTTPSブラウザー受入検証は完了。
本番URLは https://grad-checker-chi.vercel.app 。
予算通知は未設定で、ユーザーの指示により原因調査・設定を後回しにした。
自動公開フラグはrepository・production environmentとも未設定を維持した。

| 項目 | 結果 |
| --- | --- |
| PR #76 | 指定HEAD c453bd32df466896aab60b6a6779c652f4dbcc37 の最新CI成功後にDraft解除・MERGED |
| PR #76 main | c1c6cf3f7e47e59c874329ebdf8aa54566e98d49 |
| 初回構築用PR #77 | HEAD 6c386bdcde2626f6677a5322b1d8ae986cb2e18a の全CI成功後にMERGED |
| 公開ソースmain | fce02dd0187d0c1afcb7531176d1def374932450 |
| image | asia-northeast1-docker.pkg.dev/grad-checker-512505/grad-checker/api@sha256:d3a2081572a5595f0ed7ab8f67f97650f445b366579c63870e6d0f8bd0331571 |
| Registry push | 成功、固定SHAタグから取得したdigestを実サービスへ固定 |
| Cloud Run | grad-checker-512505 / asia-northeast1 / grad-checker-api |
| Ready revision | grad-checker-api-00001-g9l |
| Cloud Run origin | https://grad-checker-api-hmhzqixo4q-an.a.run.app |
| readiness | 非公開時の認証付きPASS・匿名拒否、公開後の匿名200 / status=ok、本番Vercel中継もPASS |
| Vercel本番 | dpl_GEXV2AgfCoGPq8CZsSMfb1nQJZ6C（stage検証後に昇格） |
| Vercel旧デプロイ | dpl_sxePucHULpSAqZfZ4QyXow4DbCKt（API未接続の初期画面） |
| 公開設定 | サービス単位のallUsers / roles/run.invokerのみを管理者がCloud Shellで設定。Deployer権限は拡大せず |
| データ保護 | 構築前後18テーブル・1,738行・全カラム一致。受入後もauth_attempts以外の17テーブル全カラム一致 |
| SQLite・バックアップ | 変更せず。元SQLiteのSHA-256も構築前と一致 |
| Phase 1 | 固定digestの初回作成・Ready・認証済みreadinessを確認し完了 |
| 本番公開・受入 | 完了。予算通知・有料観測機能・自動CD有効化は未実施 |

## CI・GitHub承認とCloud Run構築

[main CI 40278413167](https://github.com/uhey77/grad-checker/actions/runs/40278413167) は固定mainのBackend・Frontend・Containerがすべて成功。
BackendにはPostgreSQL結合・Go raceを含む。通常公開jobはフラグ未設定によりスキップされた。
PR #77の同じソースの卒業判定benchmarkも成功。
[初回構築40278417147](https://github.com/uhey77/grad-checker/actions/runs/40278417147) の同じSHAのCIも全成功した。

GitHub APIで現在のCLIアカウントではproduction承認不可と確認し、Required reviewer `uhey77` の承認後にcreateを実行した。
固定mainのイメージを隔離TLS PostgreSQLで試験した後にWIF認証し、Registryへpushした。
Cloud Run v2 create APIによる原子的な初回作成で、既存サービスを更新・上書きしていない。
実サービスのRuntime SA・Secret参照・CPU 1 / 512 MiB / min 0 / max 1 / concurrency 4 / request-based / startup boost無効を照合した。

Runtime SAは `grad-checker-runtime@grad-checker-512505.iam.gserviceaccount.com`。
DB接続はSecret Manager `grad-checker-database-url` version `1` だけを参照し、DIRECT_DATABASE_URLは渡していない。
非公開時の認証付きGo→Python→Neon readiness成功、匿名拒否、公開principal binding不在を確認した。
その後、既存管理者のサービス単位のInvoker操作と公開readiness成功を確認した。
DDL・移行・Seedは再実行していない。

## Vercel stage・本番ブラウザー受入

固定mainから実Cloud Run originでproductionビルドし、対象team/project/rootDirectory、
API rewrite・SPA fallback・no-store・生成物への資格情報変数名混入がないことを検証した。
`--prod --skip-domain` によりstageを作成し、生成URLのVercel認証保護は維持した。
認証済み `vercel curl` と本番Origin指定でstage APIを検証した。これは生成URLでの通常ブラウザー認証試験とは区別する。

| 検証 | 結果 |
| --- | --- |
| stage API readiness / SPA | PASS。SPAの配信HTMLと固定mainのビルドHTMLが一致 |
| Origin・CSRF | 不正Origin、CSRF欠落・不正トークンを403で拒否 |
| Cookie | HttpOnly / Secure / SameSite=Lax、認証トークンの本文露出なし |
| 成績・版競合 | 専用アカウントの必修1科目だけを保存し、古い版は409で拒否 |
| 卒業判定 | 生成時刻を現在時刻と照合し、全業務項目が既存シードからの計算結果と一致 |
| 判定履歴 | 保存・再取得・別の専用アカウントから404による本人制限を確認 |
| 本番HTTPS | Chromiumでログイン、保存済み成績表示、判定保存、履歴表示、再読込み後のセッション維持、ログアウトがPASS |
| ブラウザーエラー | 最終受入中のHTTP 5xxとJavaScript例外はともに0 |

全stage検証成功後にだけ本番へ昇格した。
テスト成績は必修1科目だけなので、卒業判定のfailは期待結果。
課程の適用入学年度が未確認である `verification_status=unverified` は[シードの仕様](../backend/seeds/README.md)どおり保持した。
計算成功を大学による卒業認定や適用年度の確定として扱わない。

検査側の失敗も記録する。CLI deployにもCLOUD_RUN_API_ORIGINが必要で、不足時は停止して修正した。
SPAの検査がrootを期待していたが実装はappであり、このPRで通常CDの同じ誤りも修正した。
verified課程のみを選ぶ検査仮定と、生成時刻まで固定シードと一致させる検査仮定も仕様に合わせて修正した。
ブラウザーの履歴検査はボタンの表示文字とaccessible nameの違いを修正した。
繰り返し試験で5回/15分のログイン試行上限にも達したが、カウンターや設定を変更せず期限後に再検証した。
各段階の検証を飛ばして成功扱いにしていない。

## 本番データの不変性と後片付け

構築前の18テーブル・1,738行の全カラムを含むチェックサムを権限制限したローカル監査ファイルへ保存し、
非公開Cloud Run構築後にも全件一致した。

受入専用の `release_owner_<ランダムsuffix>` / `release_other_<同suffix>` の2アカウントだけを使用した。
IDとユーザー名の両方が一致することを確認するガード、アプリと同じトランザクションadvisory lockの下で、
次の対象だけを一つのトランザクションで後片付けした。

| 削除対象 | 件数 |
| --- | --- |
| 専用students | 2 |
| 当該student_credentials | 2 |
| 当該auth_sessions | 6 |
| 当該grade_attempts | 1 |
| 当該check_results | 3 |
| 専用ユーザー名の認証試行 | 該当キーのみ。共有IPキーは削除せず |

元からあった期限切れauth_attempts 4件は、ユーザーの明示承認に基づき通常の認証処理で削除された。
後片付け後は18テーブル・1,735行で、auth_attemptsは新しい共有IPカウンター1件。
差分は1,738 - 4 + 1で説明できる。
残り17テーブルは構築前と行数・全カラムチェックサムが一致し、元の利用者・認証情報・セッション・成績・マスターは不変。
FK 27件はすべてvalidated、DB deadlockは0、接続数4、DBサイズ9,986,048 bytesを読み取り専用で確認した。
専用パスワード、Cookie jar、CSRF等を含む一時HTTPファイルは削除した。成果物へSecretや個人情報を転記していない。

## ログ・実測・費用

認証済みCloud Shellの監査結果をユーザーから受領した。
Cloud Run正常稼働、直近1時間のERRORログなし。
60秒区間のp95を取得しており、以下は区間p95の最大値であって瞬間ピークではない。

| 項目 | 実測 |
| --- | --- |
| 本番メモリutilization | 最大0.4195、512 MiBに対し約214.8 MiB、29 points、truncated=false |
| 本番CPU utilization | 最大0.2095（20.95%）、28 points、truncated=false |
| 本番リクエスト | 126 pointsの合計77、最大区間11、truncated=false |
| CIコンテナメモリ | 153.7 MiB / 512 MiB、ピーク168,706,048 bytes（約160.9 MiB） |
| Neon | Freeプラン、27 FK有効・deadlock 0。providerのcompute集計は更新遅延の可能性があるため公開試験分の差分課金と解釈しない |
| Vercel runtimeログ | 対象deploymentの直近30分のerror/fatal集計に該当行なし。外部rewrite主体でありGCP側の観測を代替しない |
| Vercel詳細メトリクス | HobbyではObservability Plusが必要とAPI/CLIで確認。未取得。有料プランへ変更していない |
| 実請求額 | 未確定。Vercel請求APIもcosts_not_foundであり0円とは断定しない |
| 予算通知 | 請求通貨JPY、未設定。ユーザー指示で原因調査・設定を後回し |

Cloud Runの料金条件は[公開準備](initial-release-readiness.md)を参照。
無料枠適用前で、1 vCPU / 512 MiBの計算資源は月30稼働時間なら約US$2.73。
通信・保存・Secret・ログ等は別で、JPY請求の実際のSKU価格・無料枠・請求反映を後日確認する。
予算通知は課金停止を意味しない。

`scripts/deployment/audit_live_cloud.py` は固定対象の集計だけを出し、ログ本文・Secret・トークンを出さない。
初版のbudget_not_configuredは複数の失敗を一括分類しているため、予算未設定の原因を確定する証拠には使わない。

## 残タスクと復旧

- 予算通知の原因調査・月500円/1,000円の通知設定（ユーザー指示により後回し）。
- この監査PRのレビュー・マージ。通常CDのSPA検査修正は、自動公開フラグを有効にする前に取り込む。
- 運用のログ保持・長期外部バックアップ・実請求の追跡。ローカル暗号化バックアップだけではホスト障害に耐えない。
- 課程の適用入学年度等の出典確認。未確認のマスターを推測でverifiedへ変更しない。
- プロキシ配下でのIP別試行制限の実運用粒度・授業人数での負荷は別途確認する。上限を無断で緩めていない。

初回公開の復旧先は旧Vercel `dpl_sxePucHULpSAqZfZ4QyXow4DbCKt`（API未接続の初期画面）。
必要ならサービス単位のallUsers Invokerを除去して公開停止する。DBやサービスを削除しない。
今後の正常版の復旧基準は、本監査の固定Cloud Run digest/revisionとVercel deploymentの組。
DBのDDL・Seed・SQLite再移行で復旧しない。
