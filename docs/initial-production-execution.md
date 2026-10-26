# 初回本番公開の実行監査（2026-10-26）

## 実行対象と承認

ユーザーの一括承認に基づき、本番公開までを対象とする。
PR #76の指定HEADと最新CIを確認してDraft解除・マージした。
PR #77では既存サービスに依存しない非公開初回構築を追加し、最新HEADのBackend・Frontend・Container・卒業判定benchmark成功後にマージした。

| 項目 | 結果 |
| --- | --- |
| PR #76 | MERGED、指定HEAD c453bd32df466896aab60b6a6779c652f4dbcc37 |
| PR #76 main | c1c6cf3f7e47e59c874329ebdf8aa54566e98d49 |
| PR #77 | MERGED、HEAD 6c386bdcde2626f6677a5322b1d8ae986cb2e18a |
| 構築対象main | fce02dd0187d0c1afcb7531176d1def374932450 |
| 初回構築 | [Actions 40278417147](https://github.com/uhey77/grad-checker/actions/runs/40278417147)、全CI・create成功、uhey77のproduction承認履歴を確認 |
| image digest | sha256:d3a2081572a5595f0ed7ab8f67f97650f445b366579c63870e6d0f8bd0331571 |
| Cloud Run revision | grad-checker-api-00001-g9l |
| Cloud Run origin | https://grad-checker-api-hmhzqixo4q-an.a.run.app |
| 認証済みreadiness | PASS、匿名呼出しは拒否 |
| 公開Invoker | ユーザーがCloud Shellでサービス単位にallUsers / roles/run.invokerを設定、匿名readiness 200 |
| Vercel stage | dpl_GEXV2AgfCoGPq8CZsSMfb1nQJZ6C、全stage検証PASS |
| Vercel昇格・ブラウザー受入 | 実行中 |
| HTTPSブラウザー受入 | 未実施 |
| 自動公開フラグ | repository・production environmentとも未設定を再確認 |

## 構築前データ照合

本番productionブランチの既存DBをSELECTのみで再確認した。
18テーブル・1,738行で、全カラムを含むテーブル別チェックサムを権限制限したローカル監査ファイルへ保存した。
DDL・移行・Seed・SQLiteへの書込みは行っていない。

既存の期限切れ認証試行カウンター4件が、専用テストアカウントの認証時にも通常削除されることをコードと集計SQLで確認した。
ユーザーはこの4件の通常削除を明示承認した。既存アカウント・認証情報・成績は変更対象外。
専用テストデータのIDと後片付け範囲は、受入実行時に限定して記録する。

## 非公開構築の実行証跡

同じmain SHAのイメージを隔離TLS PostgreSQLで試験後、WIF認証しRegistryへpushした。
取得したdigestを固定し、Cloud Run v2 create APIで初回サービスを作成した。
実サービスのSA・通常DB Secret参照・CPU 1 / 512 MiB / min 0 / max 1 / concurrency 4 / request-based / startup boost無効を照合し、
公開principalのbindingがないことを確認した。認証付きreadinessはPASS、匿名呼出しは拒否。
構築後に本番全18テーブル・1,738行・全カラムチェックサムが構築前と一致した。
DDL・移行・Seed・本番業務データ書込みは実行していない。

固定mainのCIコンテナ実測は153.7 MiB / 512 MiB、ピーク168,706,048 bytes（約160.9 MiB）。
Cloud Run本番の実測メトリクスや請求額とは区別する。

Vercelは固定mainから実Cloud Run originでproductionビルドを行い、対象team/project/rootDirectory、
API rewrite・SPA fallback・no-store・生成物の資格情報変数名不在を検証した。
stageのAPI中継・SPA・Origin・CSRF・Cookie・成績版競合・履歴本人制限を検証した。
評価時刻は現在時刻と別途照合し、それ以外の卒業判定全業務項目が固定mainの既存シードからの計算結果と一致した。
必修1科目だけの専用テスト成績なので判定はfail。課程のunverifiedはシードの仕様どおり保持した。

検査中に判明した誤りも隠さず記録する。CLI deploy時にもCLOUD_RUN_API_ORIGINを渡す必要があり、
不足で停止した呼出しを修正して再実行した。SPA検査はrootではなく実装上のappを検証する必要があり、
通常CDの同じ誤りもこのPRで修正する。verified課程のみを選ぶ検査仮定もシード仕様と異なっていたため修正した。
各停止時点で昇格は行わず、検証修正後に全stage試験がPASSしてから昇格へ進んだ。

## 現在の実行ゲート

[固定main CI 40278413167](https://github.com/uhey77/grad-checker/actions/runs/40278413167) はBackend・Frontend・Containerがすべて成功し、公開jobはフラグ未設定によりスキップされた。
初回構築run内の同じSHAのCIも成功した。GitHub APIで `current_user_can_approve=false` を確認し、
Required reviewer `uhey77` の実行画面からの承認後にcreate jobを実行した。保護設定を回避していない。
公開IAMはユーザーの既存管理者権限によるサービス単位の操作で設定され、匿名readiness 200を確認した。
Deployerの権限拡大はしていない。本番DBの書込みは専用テストデータと承認済み期限切れカウンターの通常削除だけ。

現在のDeployerに付与されたCloud Run DeveloperはサービスIAMの変更権限を含まないため、
非公開readiness成功後の公開Invoker設定は、既存の権限を持つ認証済み管理者の実行経路で行う。
プロジェクト全体のrun.adminなどは追加しない。

## GCPログ・実測・予算の追加監査

`scripts/deployment/audit_live_cloud.py` は認証済みCloud Shellから固定対象のメタデータ、公開principal、
直近1時間のERROR件数、CPU・メモリutilizationの60秒区間p95、request件数、請求通貨を集計する。
ログ本文・Secret・トークン・他の予算や通知先は出力しない。
`--configure-budget` 指定時だけ、JPY請求・既存同名予算なし・必要権限ありの場合に限り、
このプロジェクトに限定した月1,000円予算を50%/100%で通知する。
既存予算やIAMは変更しない。通知は課金停止を意味しない。
取得不能はavailable=false等で記録し、請求額はこの監査では取得できない。

## 未完了・残タスク

最小公開IAM（認証済みCloud Shellでのサービス単位の実行を依頼済み）、Vercel stage検証・昇格、ブラウザー受入、
データ照合、サービスのログ・メトリクス・請求確認、可能な範囲の予算通知設定。
現時点で初回公開完了とは判定しない。
費用条件と失敗時の手順は[公開準備](initial-release-readiness.md)を参照する。
