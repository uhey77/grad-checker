# メール認証の開発手順

自己登録は `@edu.teu.ac.jp` 限定。メールの確認リンクを開いてからアプリ専用パスワードを設定し、その後ログインする。登録開始時にパスワードを受け取らない。確認リンクの再送は新規登録と同じ画面で行う。

## ローカル受信箱で確認する

依存更新後は `task setup` / `make setup`、起動は次のどちらかを使用する。

```sh
task auth-dev
# または
make auth-dev
```

- 画面：`http://127.0.0.1:5173`
- 開発用受信箱：`http://127.0.0.1:8025`
- SMTP受信：`127.0.0.1:1025`

新規登録に大学メール形式のアドレスを入力する。開発用受信箱を再読み込みし、確認リンクからパスワードを設定する。ログインとログアウト、リンクの再使用拒否を確認する。受信箱のメールはメモリ上だけに保持し、終了すると消える。画面・Go・Python・受信箱はCtrl+Cでまとめて終了する。

`auth-dev` はSMTP設定をローカル受信箱へ固定するため、実在する大学メールへ送信しない。アカウントは通常の開発DBへ保存される。自動テストと実装時の検証は一時DBを使用する。

## 実メール送信

`task dev` / `make dev` はSMTP設定を環境変数から読み込む。秘密情報をリポジトリへ保存しない。

| 設定 | 用途・既定 |
|---|---|
| `PUBLIC_ORIGIN` | 確認リンクの画面オリジン。既定 `http://127.0.0.1:5173`。公開時はHTTPS |
| `SMTP_HOST` | 送信サーバー。既定空で、未設定の登録要求は503 |
| `SMTP_PORT` | 既定587 |
| `SMTP_USERNAME` / `SMTP_PASSWORD` | SMTP認証情報 |
| `SMTP_SENDER` | 送信サービスで使用可能な差出人アドレス。空なら503 |
| `SMTP_STARTTLS` | 既定true。falseは認証情報を使わないループバック受信箱のみ許可 |
| `AUTH_VERIFICATION_MINUTES` | 確認リンクの有効期限。既定30分 |
| `AUTH_SESSION_HOURS` | ログイン状態の有効期限。既定24時間 |
| `AUTH_PASSWORD_MIN_LENGTH` / `AUTH_PASSWORD_MAX_LENGTH` | 既定12／128文字。最小12以上、最大1024以下 |
| `AUTH_ATTEMPT_WINDOW_MINUTES` / `AUTH_ATTEMPT_LIMIT` | 操作ごとに接続元別、および登録／ログインのメール別の試行上限。既定15分で5回。成功要求も数える |

画面の文字数・確認期限は `/api/auth/config` から取得する。パスワードはArgon2id（19 MiB、反復2、並列度1）で保存する。[OWASPのパスワード保存指針](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html)と[argon2-cffi API](https://argon2-cffi.readthedocs.io/en/stable/api.html)を参照。

Goを単独起動する場合は `-public-origin` をPythonの `PUBLIC_ORIGIN` と一致させる。HTTPのローカル開発ではSecureなし、HTTPSではSecure付きのHttpOnly／SameSite=Lax Cookieを使用する。Python内部サービスと開発用受信箱は外部へ公開しない。

送信サービス・公開先は未決定。SMTP接続の実装とローカル配送は検証対象だが、実大学メールの受信箱への到達は未確認。サービス選定後に送信元設定と実配送を確認する。公開プロキシ配下では現在のIP制限がプロキシの接続元を共有するため、信頼するプロキシと接続元の認定を配備時に決める。

## 検証

```sh
task check
task test
task build
# Makeでも同名コマンドを利用できる
```

Goの結合テストはPATHにGoがあること、ローカルポートを利用できることが必要。成績保存・所属保存・卒業判定・推薦・履歴・パスワード再発行は今回の実装範囲に含まれない。
