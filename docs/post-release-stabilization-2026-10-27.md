# 公開後の安定化監査（2026-10-27）

## 実施範囲と本番の保全

観測は2026-10-27 18:10〜18:20 JST頃の時点監査。24〜48時間の連続監視完了ではない。
本番DBはSELECTのみ。認証・成績保存等の書込み試験を実行していない。SQLite・バックアップ・Secret・本番Cloud Run/Vercel設定・予算を変更していない。

## PR #78とブランチ

- 最新HEAD `48d436141e85b04e31c3c75017202dfacb972071`、main向け、競合なし（CLEAN）。再実行後のBackend・Frontend・Container・benchmark成功。旧同時runのcancelledを成功と混同しない。
- 差分5ファイルを確認。SPA検査のroot→app修正は `frontend/index.html`、実際の本番配信と一致。初回監査のソースSHA・digest・revision・Vercel deploymentの対応、17テーブル一致と認証試行差分の区別を確認。
- 差分の既知資格情報パターン検査は0件。手動確認でもSecret/接続文字列の実値混入は見当たらない。パターン検査は完全性の保証ではない。
- PR #78はマージ済み。main SHA `9a1ea611374597e27766d934d34311708ecbd9d7`。
- マージ後CI：[Production deployment 40478917240](https://github.com/uhey77/grad-checker/actions/runs/40478917240)。Backend・Frontend・Containerすべて成功、公開Backend/Frontendはフラグ未設定によりskip。
- devを同じmain SHAからGitHub上に新規作成。作成前にdev不在と既存リモートブランチを確認。既存ブランチは削除・書換えしていない。
- mainの旧branch protection APIは404だが、別途ruleset `Protect main` がactiveで既定ブランチの削除・force push禁止とPR必須を確認。承認必要数0、required_status_checksの規則なしで、CI成功や承認レビューはGitHub設定では強制されていない。devはprotected=false。設定変更は行わず残リスクとする。production environmentのreviewer `uhey77` とmainのbranch制限は有効。
- 既存の通常開発PR #74はbaseをmainからdevへ変更済み。HEADは変更せず、base変更後の再照会でMERGEABLEを確認。内容の最終レビュー・再検証は当該開発PRで別途必要。

## 今回取得した結果

| 対象 | 時点監査の結果・限界 |
| --- | --- |
| Cloud Run readiness | 固定既存originの `/api/ready` は3/3 HTTP 200、status=ok。Go→Python→DBの疎通を確認。これは管理APIによるReady revision照合とは異なる |
| 外部からの応答時間 | Cloud Run直接 21.484 / 0.516 / 0.378秒。初回遅延の原因は未確定（cold start、経路、DB起動等の切分けが必要）。Vercel経由 0.648 / 0.650 / 0.440秒。各3点でありSLO/p95の証明ではない |
| Vercel API中継・SPA | `/api/ready` 3/3 HTTP 200、`/acceptance-check` HTTP 200、id=app確認。今回の7リクエストに5xxなし。全トラフィックの5xx件数とは区別 |
| Vercel状態 | 既存projectの最新production `dpl_GEXV2AgfCoGPq8CZsSMfb1nQJZ6C` はREADY。Git linkなし |
| Vercelログ | 同deployment、production、直近30分error/fatalのlevel別集計は該当グループなし。1時間指定はHobby保持窓の制約で失敗したため30分に限定。外部rewrite主体なのでCloud Runのエラーログを代替しない |
| Neon | project `plain-smoke-97118898`、production `br-calm-water-a1uug5fd` ready。DB `grad-checker` は18テーブル、27 FKすべてvalidated、27 FKをSELECTで実データ照合し孤立行0、deadlock 0、接続数2、サイズ9,986,048 bytes |
| DB整合性の限界 | FK整合性を確認。既存全行の過去チェックサムとの再照合・業務全データの一致までは未確認。公開後の正常な件数変化を移行時1,738行と固定比較しない |
| Cloud Run管理情報・ログ | このセッションにはgcloud・GCP認証/管理APIツールがない。現在revision、CPU/メモリ、HTTP 5xx集計、OOM/再起動、Neon接続失敗ログは未取得。過去の0件を今回の実測として再利用しない |
| 実請求 | Vercelの2026-10-26〜28 UTCの請求APIは404 costs_not_found。GCP請求とNeon請求は取得経路なし。3者とも実請求額は未確定で、0円と断定しない |

## 過去の基準値（今回の再測定ではない）

初回Cloud Shell監査：Ready revision `grad-checker-api-00001-g9l`、1 vCPU / 512 MiB、min 0 / max 1 / concurrency 4、直近1時間ERROR 0件。
60秒区間p95の最大CPU 20.95%、メモリ41.95%。瞬間ピークではない。
元の証跡は[初回実行監査](initial-production-execution.md)を参照する。

正常な復旧基準は同revision、image digest `sha256:d3a2081572a5595f0ed7ab8f67f97650f445b366579c63870e6d0f8bd0331571` と上記Vercel deploymentの組。削除・再デプロイ・traffic変更は行っていない。

## 予算通知（設定済み）

ユーザーが認証済みCloud Shellで作成し、読取り照合成功と報告した事実を記録する。このセッションで再作成・更新はしていない。

| 設定 | 値 |
| --- | --- |
| 予算名 | grad-checker-monthly-1000JPY |
| 対象 | grad-checker-512505 |
| 通貨・期間 | JPY / MONTH |
| 予算額 | 1,000円 |
| 実費通知 | 50%（500円）、100%（1,000円） |
| カスタム通知チャネル | 未設定 |
| ユーザー本人へのメール到達 | 別途確認が必要 |

予算通知は支出上限による自動停止ではない。初回公開時点の「未設定」は歴史的記録であり、現在の未完了事項として扱わない。既存監査スクリプトの `--configure-budget` は使用しない。

## 今後24〜48時間の未完了監視

今回の時点監査を起点に2026-10-28〜29の同時刻帯を目安として追跡する。自動監視のスケジュールは未登録で、将来の結果はまだ存在しない。

- 認証済みCloud Shellで `python3 scripts/deployment/audit_live_cloud.py` を読取りモードで実行し、対象revisionと設定、CPU/メモリ、リクエスト数、ERROR集計を再確認する。`--configure-budget` は指定しない。
- Cloud MonitoringでHTTP 5xx数/率、リクエストレイテンシp50/p95/p99、instance数、CPU/メモリを24〜48時間の窓で確認する。既存スクリプトは直近1時間中心なので、1回の実行を長期監視完了と扱わない。
- Cloud LoggingでOOM・container termination/再起動、Neon接続失敗/タイムアウトを分類して件数確認する。ログ本文や接続値は成果物へ貼らない。
- idle後のreadiness遅延を再現し、初回21.484秒の要因をCloud Run起動/Neon起動/ネットワークに切り分ける。授業人数での負荷・IP別認証制限は未検証。
- Vercel経由の5xx/中継遅延をCloud Run側と同じ時間窓で照合する。無料保持窓の外の欠測を0件と扱わない。有料プラン追加は行わない。
- Neonの接続数・制約・deadlock・使用量を再確認し、GCP Billing Reports、Neon/Vercelの請求画面で実際の請求反映を追う。本人への予算通知メール到達を確認する。

## CI/CDと有効化前の残タスク

Checkにdev pushを追加し、隔離PostgreSQL結合/Go/Python、フロント、コンテナの既存検証を再利用する。PR base変更時もCIが走るようeditedを追加。mainでは既存Production deploymentの再利用CI、公開jobはmain限定・production承認付き。Vercel Git自動公開無効とmain限定WIFを維持する。

repository・production environmentの `PRODUCTION_DEPLOY_ENABLED` はいずれも未設定と読取り確認し、変更していない。

有効化前に以下が残る。

1. 本整備PRのCI・レビュー・dev統合、dev push CIの成功、まとめたdev→mainリリースPRのCI/レビュー。
2. 上記24〜48時間の観測、初回遅延の切分け、実請求と通知メール到達の確認。
3. 既存承認ゲートを維持した通常CDのCloud Run更新、Vercel stage/API/SPA検証、正常revision/deploymentへのrollbackを確認する。初回作成/公開成功は通常更新・rollbackの実証とは異なる。現在稼働版を無断で更新して試験しない。
4. バックアップの別ホスト保全・ログ保持、main/dev保護ルールの強制状況を確認する。
5. 上記証跡を提示し、ユーザーの最終承認後にのみ自動公開フラグ有効化を判断する。
