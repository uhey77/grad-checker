# grad-checker

東京工科大学の学生が、所属課程の卒業・修了要件と不足条件を確認するためのWebアプリケーションを開発するリポジトリです。

VS Codeでは [grad-checker.code-workspace](grad-checker.code-workspace) を開くと、ルート・バックエンド・フロントエンドをまとめて扱えます。

## セットアップ

リポジトリのルートで、Task または Make のどちらかを使って依存関係をセットアップしてください。

Task を使用する場合：

```sh
task setup
```

Make を使用する場合：

```sh
make setup
```

## タスクランナーのコマンド

利用できるコマンドと説明は、リポジトリのルートで `task` または `make` を実行して確認してください。
コマンドの定義は [Taskfile.yml](Taskfile.yml) または [Makefile](Makefile) を参照してください。

## 登録・ログインをローカルで試す

```sh
task dev
# または
make dev
```

画面は `http://127.0.0.1:5173`。ユーザー名とアプリ専用パスワードで新規登録し、表示された復旧コードを保管してからログインします。メールアドレス・メール送信サービスは使用しません。`auth-dev` は `dev` と同じ起動構成です。

ログイン後はダッシュボードで最新の卒業要件概要を表示します。「所属を設定」からマイページで課程・カリキュラムを保存し、成績入力から本人の成績を入力・保存できます。ダッシュボードの再取得・条件別詳細の表示では履歴は増えず、成績入力の「卒業要件をチェック」で判定履歴を保存します。現在は2026年度便覧を判定基準に使います。CS学部4課程の適用入学年度は未確認のまま保持します。

初回の卒業判定には、科目マスタと卒業要件・算入規則マスタの両方が必要です。次の順で投入してください。

```sh
task backend-seed
task backend-requirements-seed
# Makeの場合
make backend-seed
make backend-requirements-seed
```

`dev` はマスタを自動投入しません。科目と成績を表示できても、卒業要件マスタが未投入なら判定は設定不足エラーになります。投入後は画面の「判定を再試行」で確認できます。同じマスタの再投入では既存行を追加せず、保存済みの所属・成績を変更しません。再生成は `backend-requirements-build`。出典と配分方針は[卒業要件マスタ](backend/seeds/requirements.md)を参照してください。

設定・復旧・旧DBの扱いは[認証の開発手順](docs/auth_development.md)を参照してください。

## Go公開APIのOpenAPIとSwagger UI

初回は上記の `setup` と2種類のシード投入を実行してください。Python起動時にテーブルとDBディレクトリを初期化します。Swagger UIも使う場合は、通常の `dev` の代わりに次を実行します（終了は Ctrl+C）。

```sh
task api-docs
# または
make api-docs
```

[Swagger UI](http://127.0.0.1:5173/docs) と [OpenAPI JSON](http://127.0.0.1:5173/openapi.json) を開けます。Goの外部APIと同じOriginへViteがプロキシします。`8000/docs` から直接操作すると、既定の許可Originと異なるため変更操作は403になります。`localhost` への置き換えもせず、`127.0.0.1:5173` を使ってください。

Swagger UIでの確認手順：

1. `GET /api/auth/config` でパスワード方針を確認し、`POST /api/auth/register` で登録します。Origin欄は初期値 `http://127.0.0.1:5173` のまま実行します（許可Originを変更した場合は現在の画面Originに合わせます）。復旧コードを保管します。
2. `POST /api/auth/login` を実行します。HttpOnly Cookieはブラウザーが保持・送信するため手入力しません。
3. 応答の `csrf_token` をページ上部の **Authorize → csrfToken** へ入力します。`sessionCookie` は空欄のままにします。
4. `GET /api/programs` の選択肢と `GET /api/me` の `data_revision` を使って `PUT /api/me/program` を実行します。所属・成績の保存ごとに更新後の版を使用します。
5. 科目・成績・判定APIを確認します。`POST /api/checks` は保存済みの版で判定し履歴を作ります。最新判定とダッシュボードのGETは履歴を増やしません。

Swagger UIは認証情報をブラウザーストレージへ保存しません。再読込み時は `GET /api/auth/session` からCSRFを取得し直します。ログアウト・復旧後はAuthorizeを解除します。実行例のパスワードを実運用に使わないでください。Swagger UIのJS/CSSはバージョン固定のCDN（`swagger-ui-dist@5.29.0`）から取得するためネット接続が必要です。仕様の外部バリデーターへの送信は無効にしています（[Swagger UI公式の配信方法](https://swagger.io/docs/open-source-tools/swagger-ui/usage/installation/)）。

Goの `/docs`・`/openapi.json` は `-api-docs` を指定したときだけ有効で、通常の `dev`・Go単独起動では404です。Pythonの同名経路は常に無効です。`api-docs` は開発用科目一覧も有効にするローカル開発コマンドです。本番の起動設定にこれらのフラグを引き継がないでください。

```sh
# 公開契約やレスポンスの型を変更したときに再生成
task api-docs-build
# 生成差分・OpenAPI構文・Goルート・メソッド・実HTTP応答の検証
task api-docs-check
# lint・整形・型、Python/Go/画面の全テスト、画面ビルド
task check
task test
task build
```

Makeでも同名の `make api-docs-build`・`make api-docs-check`・`make check`・`make test`・`make build` を使えます。結合テストは一時SQLiteと空きローカルポートを使い、通常の開発DBを変更しません。Goがない場合にスキップされた結果を、結合テスト成功とは扱わないでください。

仕様は [生成済みOpenAPI](backend/apps/api/controllers/apidocs/openapi.json)。パス・入力・日本語エラー等の編集元は [生成処理](backend/scripts/build_openapi.py)、レスポンス型はPythonのapplication契約です。Goの入力検証・日本語エラー・Cookieの公開形を生成処理で記述し、ブリッジの包絡形式・内部ルートは含めません。`api-docs-check` は `backend-check` とPRのCIにも含まれます。確認対象は [テスト仕様](docs/test_specification.md#5-性能起動ドキュメント)を参照してください。

## 200科目の性能計測

実際のGo外部APIからPython判定・SQLite読取り・判定履歴保存までを、独立した一時DBで計測する場合は `make benchmark-graduation` または `task benchmark-graduation` を使用します。再現手順・反復回数・コールド／ウォームの定義・測定値の読み方は[性能計測手順](docs/performance_200_courses.md)を参照してください。

## 2026年度の全学部・大学院

両キャンパスの38課程を登録し、照合済み28課程を参照判定する。資料不一致などの10課程は理由付きで判定を停止する。範囲・出典・残件は[対応表](docs/curriculum_coverage_2026.md)を参照。大学院の非単位条件は本人申告で、未入力は判定保留となる。

```sh
task backend-all-seed-build
task backend-all-seed
# Makeも同名のターゲットに対応
```
