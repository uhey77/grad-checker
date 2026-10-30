# 安定化の追加検証（2026-10-27）

## 完了した事項

PR #79はユーザー操作で2026-10-27 18:42 JSTにdevへ統合された。
統合SHAは `8bbd3c05b888d4b1892ea24ffb7875818ec66cbe`。
[dev push CI 40482775805](https://github.com/uhey77/grad-checker/actions/runs/40482775805) はBackend・Frontend・Containerすべて成功。
production公開jobはdevでは起動しない。

PR #74最新HEAD `fc354e032cffd1a9ad3544572a0d363c8e22fd7f` のレビューでは、ヘッダー改善以外に、判定保存・履歴UIの撤去、ダッシュボード整理、表示用必修内訳API追加を確認した。
総合判定・総必要単位を変えず内訳を追加し、古い結果の未収録内訳を推測しない実装。
ローカルfrontend-check、62テスト、build、必修内訳7テストは成功。
Chromiumのテスト用API応答で1280/375/320pxの概要→詳細、日英切替、3個の48pxヘッダーボタン、Escapeのフォーカス復帰、マイページの編集キャンセル、概要取得失敗→再試行を確認。各幅JavaScript例外0、GETのみ・判定履歴API呼出しなし。本番API/DBの検証とは区別する。
ユーザーが「まだマージしない」と指定したためPR #74は未マージで保持する。今回のリリース・本番試験に含めない。

## 再測定と限界

2026-10-27 18:49 JST、アイドル後にVercel経由を先に測定した。

| 経路 | HTTP | 合計秒 | 最初のバイトまでの秒 |
| --- | --- | --- | --- |
| Vercel 1回目 | 200 | 16.071 | 16.071 |
| Vercel 2回目 | 200 | 0.440 | 0.440 |
| Vercel 3回目 | 200 | 0.443 | 0.443 |
| Cloud Run直接 1回目 | 200 | 0.362 | 0.362 |
| Cloud Run直接 2回目 | 200 | 0.367 | 0.367 |
| Cloud Run直接 3回目 | 200 | 0.366 | 0.366 |

DNS完了は0.017〜0.022秒、TLS完了は0.062〜0.094秒。
初回遅延は以前の直接初回21.484秒と同様に、応答開始前の待ち時間が主体。Cloud Run/Neon起動待ち等は候補であり、原因確定ではない。
クライアントのDNS/TLSだけで16秒を説明する観測ではない。

NeonをSELECTで再確認：18テーブル・27 FK validated・deadlock 0・接続数1・9,986,048 bytes。
今回、全行の過去チェックサム照合を実行したという意味ではない。
Vercel実請求API（2026-10-23〜28 UTC）は再び404 costs_not_foundで、0円とは扱わない。
接続済み個人Gmailで本プロジェクト名/予算名による2026-10-23以降の予算・請求通知を検索したが該当なし。
閾値未到達・反映待ち・別受信先等を切り分けられず、メール到達成功とは判定しない。通知先や予算設定は変更していない。

## GCP監査の実行準備

`production-monitor.yml` は手動のみ・mainの完全SHA一致・既存production承認が必須。
既存WIF/Deployerを使い、本番DB Secretを渡さず、Cloud Run設定・監視時系列・ログの件数だけを読む。
予算作成/更新・DB操作・サービス更新・課金設定変更は行わない。

main反映後、固定main SHAを指定して実行する。

```sh
gh workflow run production-monitor.yml --ref main -f expected_sha=<40桁のmain SHA> -f hours=24
# 翌日の追跡時点では hours=48。公開前・欠測の時間を稼働実績として埋めない。
```

実行にはproduction reviewer `uhey77` のGitHub承認が必要。
既存Deployerにmonitoring/logging読取り権限がない場合はavailable=false/HTTP 403等として記録する。自動でIAM権限を追加しない。
`scripts/deployment/monitor_production.py --hours 24` は認証済みCloud Shellからも同じ固定対象を読める。
出力はログ本文を射影で除外し、Secret・接続URL・トークンは出さない。
CPU/メモリ・リクエストレイテンシの値は5分区間p95の最大値であり、全期間p95や瞬間最大ではない。[公式の分布メトリクスとpercentile](https://docs.cloud.google.com/monitoring/api/v3/distribution-metrics)と[Cloud Runメトリクス一覧](https://docs.cloud.google.com/monitoring/api/metrics_gcp_p_z)に合わせる。
ログのOOM/終了/接続失敗分類は文字列による兆候件数であり、正確な再起動回数や接続エラー総数ではない。
空の時系列、権限不足、件数上限到達は、正常/0件の証明として扱わない。
コンテナ内request_latenciesは起動時間を含まないため、E2E・pending・container startupの各p95も別々に取得し、遅延を切り分ける。request_countはコンテナに到達しない要求を含まないため、HTTP 5xxのリクエストログ件数も別に取得する。
実請求額はMonitoring APIでは取得できないため、GCP Billing Reports・Neon請求画面での別確認が残る。

## ブランチ保護の具体案（未適用）

現行main rulesetはPR必須、削除/force push禁止、必要承認数0、required_status_checksなし。devは未保護。
候補はmain/devにBackend・Frontend・Containerの成功とレビュー1名、会話解決を要求すること。
mainの公開CIではcheck名が `ci / backend` 等、通常PRでは `backend` 等になるため、required status名をそのまま共通指定せず、PR用の安定した集約jobか実測したcheck contextを使う。
卒業判定benchmarkは差分条件でskipするため、無条件の必須checkにしない。
設定を適用する前に、本人レビュー禁止時のレビュー担当者、GitHub rulesetの対象branch、既存PRとの整合を確認する。
既存productionのrequired reviewer/main制限は維持する。

## 通常CDの更新・stage・rollback実証の手順（未実施）

現在の復旧基準はCloud Run `grad-checker-api-00001-g9l` / digest `sha256:d3a2081572a5595f0ed7ab8f67f97650f445b366579c63870e6d0f8bd0331571` とVercel `dpl_GEXV2AgfCoGPq8CZsSMfb1nQJZ6C` の組。
ユーザーから本番試験まで実施する承認を受領した。試験は本番revision/配信先を一時的に変更し、その後に上記正常版へ戻す。PRODUCTION_DEPLOY_ENABLEDは有効化しない。

`production-rehearsal.yml` はmainの完全SHA一致、`REHEARSE_AND_RESTORE`入力、同SHAのCI成功、既存production承認を必須にする。公開中ソース `fce02dd0187d0c1afcb7531176d1def374932450` とbackend/frontend/Dockerfileの追跡ファイルが完全一致しなければ停止する。PR #74は含めない。

```sh
gh workflow run production-rehearsal.yml --ref main -f expected_sha=<40桁のmain SHA> -f confirmation=REHEARSE_AND_RESTORE
```

既存正常digestでno-trafficの一時revisionを作り、設定ハッシュ・Readyを照合後に一時的に100% trafficを向ける。Vercel stageのAPI/SPA検証後に一時promoteし、aliasを照合する。成功・失敗にかかわらずalwaysステップでVercel rollback、正常版再promote、Cloud Run正常revisionへのtraffic復旧と公開API/SPA再検証を行う。予期しない第三のrevisionへtrafficが変更されていた場合は上書きを停止する。runner喪失・timeout等で復旧ステップ自体が動かない場合は、以下の正常版へ手動復旧する。試験revision/stageは削除しない。

```sh
# 認証済み・対象確認済みの管理環境でのみ使用する緊急復旧先
vercel rollback dpl_GEXV2AgfCoGPq8CZsSMfb1nQJZ6C --yes
gcloud run services update-traffic grad-checker-api --project grad-checker-512505 --region asia-northeast1 --to-revisions=grad-checker-api-00001-g9l=100
```

1. リリースPRの最新HEAD CIを確認し、mainマージ後の完全SHAとproduction承認を固定する。
2. 現在のCloud Run service spec・traffic・Ready revision・image digest、Vercelの本番aliasとdeploymentを読み取り照合する。基準と違えば停止し復旧先を再確定する。
3. 初回に隔離DBコンテナ試験を通過した既存の正常digestを再利用する。今回は新しいbackend imageのbuild/pushをせず、DDL・Seed・移行も呼ばない。
4. main限定のproduction承認下でCloud Run更新を実施し、現行フロントとの互換性・readinessを確認する。公開中の正常revision/imageは削除しない。
5. Vercel production設定でbuildし、compiled API rewrite/SPA/資格情報非混入検査後、`--prod --skip-domain` でstageする。保護されたstageへ認証付きでreadiness/SPAを確認し、失敗なら昇格しない。
6. ユーザー承認範囲内でテスト済みstageをpromoteし、公開readiness/SPAを確認する。DB不変の制約により、本番の新規アカウント作成・ログイン・成績保存・履歴作成による検証はしない。
7. Vercelを上記正常deploymentへrollbackし、Cloud Runを上記正常revisionへ100% trafficを戻す。両方のreadiness/SPAと配信先を確認する。サービス/DB/revisionを削除しない。
8. 途中で失敗した場合も、先に変更した対象を正常版へ戻して検証する。復旧処理自体が失敗したら後続の公開を停止し、現在traffic/aliasを明示する。
9. rollback後のVercel自動alias割当状態とCloud Runの最新revision参照に注意し、次回公開が古い/未検証版へ向かないことを確認する。

この手順書とローカルテストは、本番での更新/rollback成功の証拠ではない。
24〜48時間監視、実請求、通知メール、実運用の保護設定、通常CD実証とユーザーの最終承認が揃うまで、自動公開フラグを変更しない。

## 2026-10-30：更新試験の失敗と検証処理の修正

[更新・復旧試験40487548392](https://github.com/uhey77/grad-checker/actions/runs/40487548392)はproduction承認後、Cloud Run更新ステップでRuntimeErrorとなった。
ユーザー提供のCloud Shell読取り結果では更新権限は許可され、試験revisionの作成・Ready記録・正常digestとの一致を確認した。
終了後のtrafficは正常revisionへ100%。workflowの復旧・公開API/SPA確認も成功した。
Vercel stage以降はskipされ、通常更新・復旧試験の完了とは扱わない。
旧ログは検証条件を区別しないため、latestReadyRevisionNameの不一致と設定ハッシュ不一致のどちらが原因かは確定していない。

試験スクリプトは、サービスのlatestReadyRevisionNameとの比較に代えて、指定した試験revisionを直接取得し、名前・Ready=True・固定imageDigestを確認する。
Active=False/Retiredだけでは拒否しない。これは配信先切替後のreadiness成功を証明するものではないため、切替後のtraffic/readiness確認を維持する。
設定比較は従来どおりspec全体と選定済みannotationsのハッシュで行い、自動設定項目を推測で除外しない。
切替直前のtrafficが正常revisionから変化していれば停止する。
失敗時には固定のstage/error_codeとCLI終了コードを記録し、CLI出力・引数・設定値は出さない。
この修正のテストはクラウドを呼ばない。main反映と承認下での本番再試験は別途必要で、自動公開フラグは変更しない。
