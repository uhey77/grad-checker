# 初回本番公開の準備・実行状況

## 現在の状態

2026-10-26に本番公開とHTTPSブラウザー受入検証を完了した。
本番URL: https://grad-checker-chi.vercel.app 。
Cloud Runはgrad-checker-api-00001-g9l、Vercelはdpl_GEXV2AgfCoGPq8CZsSMfb1nQJZ6C。
専用テストデータの後片付け後も、認証試行カウンター以外の17テーブルは構築前と全件一致。
予算通知は設定・読取り照合済み（ユーザーのCloud Shell実行報告）。自動公開フラグは未設定を維持する。
実測値・検証結果・既知の制約は[実行監査](initial-production-execution.md)を参照する。

## 承認と固定対象

2026-10-26、ユーザーは非公開初回構築から必要最小限の公開Invoker、Vercel stage、
検証成功後の本番昇格、専用アカウントによる受入検証まで一括承認した。
GitHub `production` 環境のrequired reviewerによる承認は引き続き必要。
自動公開フラグ `PRODUCTION_DEPLOY_ENABLED` は初回公開の検証終了まで有効にしない。

- リポジトリ: `uhey77/grad-checker`
- PR #76: 承認されたHEAD `c453bd32df466896aab60b6a6779c652f4dbcc37` のCI成功後、Draft解除・マージ済み。
- PR #76のmainマージ: `c1c6cf3f7e47e59c874329ebdf8aa54566e98d49`
- 初回構築用PR #77のmainマージ: `fce02dd0187d0c1afcb7531176d1def374932450`
- GCP: `grad-checker-512505` / `asia-northeast1`
- Cloud Run: `grad-checker-api`
- Registry: `asia-northeast1-docker.pkg.dev/grad-checker-512505/grad-checker/api`
- Runtime SA: `grad-checker-runtime@grad-checker-512505.iam.gserviceaccount.com`
- Runtime Secret: `grad-checker-database-url` version `1` のみ。DIRECT_DATABASE_URLは渡さない。
- フロントエンド本番URL: `https://grad-checker-chi.vercel.app`

過去の個別承認段階と読取り監査の証跡は[マージ後監査](post-merge-readonly-audit.md)を参照する。
以前の「次の公開承認待ち」という記述は上記一括承認により更新された。
各工程の実行成功とユーザーの承認は区別し、未実施を完了扱いにしない。

## 構築と公開の順序

1. 固定main SHAの最新CIを確認する。
2. `Initial private production service` をmain完全SHA指定で手動実行する。
3. production承認後、隔離TLS PostgreSQLによるコンテナ試験を行い、そのイメージだけをpushする。
4. Registryからdigestを確定し、Cloud Run v2 create APIで非公開サービスを原子的に作成する。
   既存サービス・既存SHAタグがある場合は停止する。通常CDやreplaceで初回作成を代用しない。
5. 匿名呼出しの拒否、認証済み `/api/ready`、revision Ready、Runtime SA・Secret・リソースを確認する。
6. 本番DBの全18テーブルの件数・全カラムチェックサムを構築前と比較する。
7. 非公開検証成功後、サービス単位の `allUsers` / `roles/run.invoker` だけを設定する。
   Deployerの権限不足をプロジェクト全体のrun.admin追加で解決しない。
8. 実Cloud Run originでVercelをビルドし、`--prod --skip-domain` で未昇格stageを作成する。
9. readiness・API中継・Origin・CSRF・Cookie・SPAを確認する。
   stageの生成URLとPUBLIC_ORIGINは異なるため、stageのAPI試験と昇格後の通常ブラウザー試験を区別する。
10. すべて成功した場合だけVercelを昇格し、HTTPSブラウザーでログイン・成績・卒業判定・履歴を検証する。
11. 専用テストデータを限定して後片付けし、既存利用者・マスターの不変性とログ・メトリクス・費用を確認する。

設定は1 vCPU / 512 MiB / min 0 / max 1 / concurrency 4 / request-based billing / startup boost無効。
DDL・移行・Seedは再実行しない。SQLiteやバックアップを変更しない。
デプロイ・readiness・認証・API中継に失敗した場合は後続の公開を停止する。

## データ保護と受入対象

構築前に本番18テーブル・1,738行を読み取り専用で再確認し、全カラムを含むテーブル別チェックサムを保管した。
既存アカウント・認証情報・成績はテスト対象に使わない。
現行認証処理は期限切れの認証試行カウンターを通常削除する。
既存4件がすべて期限切れであることを確認し、ユーザーはこの4件の削除を明示承認した。
この通常削除を、専用アカウント・成績・判定履歴の作成と削除から区別して記録する。

移行直後の1,738行固定監査は初回移行検証専用であり、利用開始後の件数増減を失敗と解釈しない。
通常運用ではスキーマ・接続・readinessを検証し、既存データの不変性は対象行とチェックサムで照合する。

暗号化バックアップはユーザー指定によりローカル保管のみ。
鍵は別ディレクトリに権限制限して保管し、外部転送・自動削除は行わない。
同一ホスト障害に耐える外部バックアップは未設定。

## 費用条件と通知

[Cloud Run東京はTier 1](https://docs.cloud.google.com/run/docs/locations)で、
[request-based料金](https://cloud.google.com/run/pricing)はCPU US$0.000024/vCPU秒、メモリUS$0.0000025/GiB秒。
1 vCPU / 512 MiBの計算資源は無料枠適用前で稼働1時間あたり約US$0.0909、月30時間なら約US$2.73。
リクエスト・外向き通信・Registry保存・Secret・ログなどは別途考慮する。
無料枠は請求アカウント内で共有されるため、無料とは断定しない。
月30日間ずっとリクエスト処理中なら計算資源だけで約US$65.45になる。
min 0・max 1は金額による課金停止ではない。

VercelはAPIでHobby、NeonはFree（free_v3）を確認した。
Neon production computeは0.25〜2 CU、suspend_timeout_seconds=0（既定の5分）で、既存設定を変更していない。
Freeの容量・compute・通信枠を超える場合は可用性の制約がある。

月額1,000 JPYの予算通知は実費50%（500円）・100%（1,000円）で設定済み。再作成・更新しない。カスタム通知チャネルは未設定で、本人へのメール到達は未確認。詳細は[安定化監査](post-release-stabilization-2026-10-27.md)を参照する。
通知は課金停止を意味しない。実測請求額を取得できない場合は未確認と記録する。

## 失敗時の停止・復旧

- 初回作成ワークフローは既存サービスを自動更新・削除しない。失敗後はrevision・digest・制限付きログを確認する。
- 非公開構築失敗時は公開IAMとVercel昇格を行わない。
- stage不調時は昇格しない。旧Vercel本番はAPI未接続の初期画面であり、完全動作するAPIの復旧先ではない。
- 初回公開後に障害があればVercelを旧デプロイへ戻し、必要ならサービス単位のallUsers Invoker bindingを除去して公開停止する。
- 正常revision/digestとVercel deployment IDの組を記録し、次回以降の復旧先とする。
- DBの初期化・Seed再投入・SQLite再移行で復旧しない。既存データを保全する。

実行結果は[初回公開の実行監査](initial-production-execution.md)へ記録する。
