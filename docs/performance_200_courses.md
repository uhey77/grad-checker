# Issue #45: 200科目の卒業判定API性能計測

## 実行方法

リポジトリのルートから通常の `make setup` / `task setup` の後に実行する。

```sh
make benchmark-graduation
# または task benchmark-graduation
# 詳細と結果ファイルの指定
cd backend && uv run --locked python -m scripts.benchmark_graduation --iterations 30 --output ../performance-results.json
```

Go、Python 3.15、`uv` が必要。**このベンチマークは開発用**で、ローカルの一時 SQLite と、一時ポート上の Go / Python サーバーを利用する。通常の開発DB、ユーザーの本人成績、保存済み履歴を変更しない。計測後に一時ファイルとプロセスを破棄する。

## データと条件

- 2026年度の既存科目マスタ `backend/seeds/cs_2026.json` と卒業要件マスタ `backend/seeds/cs_requirements_2026.json` を利用する。
- 対象は情報基盤コース。既存126科目の分類・算入要件を維持し、選択科目を74件生成して当該課程を**200科目**にする。便覧にない生成科目は性能確認専用であり、実際に履修できる科目ではない。
- 対象200科目に確定済みA評価を1件ずつ設定する（履修年度2026、前期）。本人の登録、ログイン、所属・成績保存は計測外。
- `GET /api/me/graduation-requirements` と `POST /api/checks` を Go外部API から実行する。POSTの計測は履歴保存のコミットとレスポンスの受信完了までを含む。
- 最初のGET応答を **cold**、以降の連続呼び出しを **warm** として記録する。coldは**プロセス起動後の初回リクエスト**であり、サーバー起動時間・マスタ投入時間は含まない。
- `bridge_get` は直接PythonのHTTPブリッジへ要求した通信込みの時間。 `db_snapshot` は本人とマスタのDB読取り、`python_evaluation` は独立スナップショットからの判定計算時間。各区間は独立測定なので加算して外部API所要時間と比較しない。
- 各計測値はミリ秒。最小、中央値、p95（nearest rank）、最大を出す。ウォームのGET・POST **全サンプルが1,000ms以下**の場合のみ `satisfies_1s=true` とし、超過時は非ゼロ終了する。コールド結果は別に報告する。

## 測定結果

測定環境依存のため、数値を固定値として記載しない。コマンドの出力JSONにOS、Python、Go、SQLiteバージョン、CPU識別子、件数、反復回数、コールド／ウォーム条件と所要時間、1秒の成否が出力される。CIを実行した場合、結果はワークフローの `graduation-benchmark` artifact から入手する。

**実測値はCI実行結果または実機実行結果でのみ確定する。未実測の状態では1秒達成を保証しない。** もし超過した場合は、まず `external_get`・`bridge_get`・`db_snapshot`・`python_evaluation`・`external_post` を比較して調査する。全課程の合算マスタ、他学部データ、履歴件数増大時の性能は、この検証の保証対象外。
