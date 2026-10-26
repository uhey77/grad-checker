# 本番Neonデータ移行の実行記録（2026-10-26）

ユーザーの明示承認に基づき、本番スキーマ作成・SQLiteデータ移行・既存CS卒業要件シード投入を実施した。全18テーブルの照合と読取り専用の卒業判定検証が成功した。本番DBは18テーブル・1,738行。PRマージ、Cloud Run作成・公開、Vercel本番昇格、デプロイ有効化は行っていない。

## 対象と実行コード

- GitHub: `uhey77/grad-checker`、[PR #75](https://github.com/uhey77/grad-checker/pull/75)。実行SHA: `d965a5e669b94abbc5dcd71a0551320be345409c`。
- [Check CI](https://github.com/uhey77/grad-checker/actions/runs/40256142651)のbackend/frontend/containerと[benchmark](https://github.com/uhey77/grad-checker/actions/runs/40256142743)は成功。手動vercel-auditはskip。直前コミットからの差分は監査文書のみで、移行コードは変更していない。
- Neon project: `plain-smoke-97118898`、branch: `production` / `br-calm-water-a1uug5fd`、DB: `grad-checker`、role: `grad-checker_owner`。
- Endpoint: `ep-silent-bird-a1iyza45`、直接接続host: `ep-silent-bird-a1iyza45.ap-southeast-1.aws.neon.tech`。
- 元SQLite: `/root/workspace/grad-checker/backend/data/grad_checker.db`。この環境で見つかった既存のアプリDBを対象とした。過去のリハーサル用バックアップは今回の環境では見つからず、新しいバックアップを作成した。
- 接続先のproject/branch/endpoint/DB/roleの対応をNeon APIで検証し、各書込みフェーズ直前にhost・DB・role・TLSを再検証した。`sslmode=require`を維持し、psycopgの`pgconn.ssl_in_use`も確認した。

## SQLiteの停止とバックアップ

稼働中の元SQLite接続は検出されなかった。さらに元DBへ`BEGIN IMMEDIATE`の書込み予約ロックを保持し、別接続の`BEGIN IMMEDIATE`が拒否されることを確認した。journal modeはdelete。データ更新は行わず、ロック保持中に既存の`backup_sqlite`を使って整合したバックアップを作成した。元DBのintegrity_checkはok、外部キー違反は0。移行・検証完了後に予約ロックを解放し、SQLiteを使うサービスは停止状態のまま再起動していない。ロック解放はSQLiteへの書込み再開の指示ではない。

元DBは11テーブル・881行で、移行コードが要求する要件・履歴関連7テーブルがなかった。保存バックアップをさらにコピーした移行用DBへ、既存の`create_requirement_schema`を適用して空の7テーブルを追加した。元DBと保存バックアップを改訂していない。既存11テーブルの全行・全カラムが保存バックアップと一致し、移行用DBの整合性・外部キー検査も成功した。

個人情報を含むDBと内部証跡はリポジトリ共通Gitディレクトリの`migration-artifacts/production-20261026/`に保持する。この環境での絶対パスは`/root/workspace/grad-checker/.git/migration-artifacts/production-20261026/`。ディレクトリは0700、DBは0600で、コミット・artifact公開しない。これはローカル保管であり、外部の長期保管先への複製は未実施。

| ファイル | 役割 | SHA-256 |
| --- | --- | --- |
| 元SQLite | 変更していない11テーブル | `fa2a6e7050baabbad457cf2bacb133b07a5846010bb22bce663a3f9ae7204092` |
| `source-latest.sqlite3` | 最新の整合バックアップ、以後不変 | `1fbc79b37e282e35efc0d32668d565b5ef770e6f0c9ff147fb947839b6600825` |
| `migration-source.sqlite3` | 空の7テーブルを追加した移行元、以後不変 | `dad274d60addeff60a9dfdb8e8ce347cc11d149055aa2a7a76e858dbdd1231bf` |
| `cs_requirements_2026.json` | リポジトリ既存の投入シード | `fcd410e9fe33a96a69118a5708678e340feabd3b6fa9507ce597a73a54f1d921` |
| `review-schema.sql` | 接続不要で既存コードから生成したDDL | `4ee68660180d385283b77e8099ef0d1d2fb56312702406bb90e83bcbf41a9f3c` |

SQLite backup APIが再構成するため元DBとバックアップのファイルハッシュは異なる。データ同一性は全カラム比較で確認した。元DB・保存バックアップ・移行用DB・シードのハッシュは本番操作の各フェーズ直前と検証終了時に照合した。

## 本番書込みと照合

| フェーズ | 確認完了時刻 | 結果 |
| --- | --- | --- |
| 最新バックアップ・ローカルシード検証 | 2026-10-26 11:04:51 JST | 既存881行保持、シード再生成一致 |
| 本番空状態・直接接続検査 | 2026-10-26 11:05:22 JST | ユーザー領域のテーブル・ビュー・sequence等0件、TLS有効 |
| スキーマ作成 | 2026-10-26 11:05:55 JST | 18テーブルと履歴更新禁止トリガー、全テーブル空、6.000秒 |
| データコピー・再照合 | 2026-10-26 11:07:21 JST | 881行、全18テーブル全カラム一致、74.801秒（コピー開始から独立照合まで） |
| 卒業要件シード投入・再照合 | 2026-10-26 11:08:53 JST | 857行追加、全18テーブルがローカル検証済み結果と一致、71.815秒 |
| 卒業判定検証 | 2026-10-26 11:09:15 JST | 既存利用者1件の判定一致、4課程の総必要124単位を確認 |

スキーマは既存`migrations.schema.initialize_schema`、移行は`migrations.postgres.migrate`を使用した。空状態のplanに続けてapplyを実行し、両コードの既存スキーマ・既存行拒否を維持した。データ移行は単一トランザクションで全行をコピーし、型を復元した全カラム照合に成功してからcommitした。commit後にも別接続で全18テーブルを再照合した。

卒業要件投入は既存の`build_import_use_case(...).execute(...)`を使用した。CLIの初期化・既存規則改訂を本番で繰り返さず、既存の型・重複・参照・条件検証と1トランザクションの追加投入をそのまま使用した。シードは出典JSONと科目シードからメモリ上で再生成して完全一致を確認し、先にローカル作業コピーで投入・判定検証を行った。

27個の外部キー制約について参照先がない行を検索し0件、未検証のPostgreSQL外部キー制約も0件だった。既存アカウント、パスワード・復旧コードのハッシュ、セッション、認証試行、所属・版番号、成績6行は全カラム不変。実アカウントへのログインやパスワード再設定は実行していない。

| テーブル | SQLite移行行数 | シード追加 | 最終行数 |
| --- | ---: | ---: | ---: |
| `academic_programs` | 6 | 0 | 6 |
| `curricula` | 4 | 0 | 4 |
| `classifications` | 68 | 0 | 68 |
| `courses` | 131 | 0 | 131 |
| `course_offerings` | 161 | 0 | 161 |
| `curriculum_courses` | 498 | 0 | 498 |
| `students` | 1 | 0 | 1 |
| `student_credentials` | 1 | 0 | 1 |
| `auth_sessions` | 1 | 0 | 1 |
| `auth_attempts` | 4 | 0 | 4 |
| `grade_attempts` | 6 | 0 | 6 |
| `graduation_requirements` | 0 | 80 | 80 |
| `requirement_scopes` | 0 | 492 | 492 |
| `credit_rules` | 0 | 16 | 16 |
| `credit_rule_courses` | 0 | 265 | 265 |
| `credit_rule_limits` | 0 | 4 | 4 |
| `completion_policies` | 0 | 0 | 0 |
| `check_results` | 0 | 0 | 0 |
| **合計** | **881** | **857** | **1,738** |

## 卒業判定と検証範囲

- 既存利用者の本番スナップショットから既存判定関数を実行し、同じデータ・シードを持つローカル作業コピーと結果全体が一致した。個別の成績・判定内容は記録しない。
- 4課程それぞれについて本番マスタと空の合成成績をメモリ上で判定し、必要124単位・算入0単位の整合性を確認した。テスト用の学生・成績を本番DBへ作成していない。
- 判定後も全18テーブルがローカル検証済み結果と一致し、履歴は0件。判定結果保存や版番号更新は行っていない。
- バックアップ、要件シード、卒業判定の既存テスト83件が成功（18.39秒）。PRの既存CIも成功している。
- Neon APIからも本番DB名、18テーブル、要件80行、verified規則12行・unverified規則4行、未検証外部キー0件を独立確認した。

本シードはCS4課程を対象とする。適用入学年度のunverified/null、他学部4規則の未確認状態・理由・アプリ配分方針は既存データのまま保持する。正式な他学部配分順序や対象科目の転記完了、他学部・大学院マスタの投入完了を意味しない。

## 復旧・再開の手順

1. 元SQLite、最新バックアップ、移行用DBを削除・上書きしない。上記SHA-256とintegrity_check・foreign_key_check、全カラム比較を再確認する。原本の検証には読み取り専用接続を使う。
2. 途中失敗時は後続の書込みを停止する。スキーマ作成・データ移行・シード投入はそれぞれ独立したトランザクションなので、完了済みフェーズまでの状態を先に確認する。今回すべて成功済み。
3. 今の本番DBへ初期DDLやデータ移行を再実行しない。既存スキーマ・行があるため拒否される。障害時も本番DBをdrop/truncate/resetしてやり直さない。
4. 再構築が必要なら、別途承認された隔離・空の移行先を使い、保管中の`migration-source.sqlite3`から既存[移行手順](../backend/migrations/README.md)で再構築し、全18テーブルを照合する。必要な要件シードを同じSHA-256で追加し、再照合する。今回、新しい復旧用クラウドリソースは作成していない。
5. 運用開始後のNeonに追加書込みがある場合は、差分と現在のDBを保全してから復旧先・切替方法を判断する。元SQLiteへ自動的に戻さない。今回アプリの接続先は切り替えておらず、SQLiteを使うサービスも再起動していない。
6. 接続情報は公式接続機能で再取得し、権限を制限したGit管理外ファイルまたは環境変数で渡す。実値をコマンド引数・ログ・文書へ記録しない。今回の一時接続ファイルは検証後に削除した。

## 残タスク

- mainマージ、WIF実認証、Cloud Run起動・公開、Vercel実API中継・本番昇格は未実施。PRはOPEN、`PRODUCTION_DEPLOY_ENABLED`はrepository/production environmentとも未設定を再確認した。
- 今回確認した直接接続と、既存GitHub Secrets・Secret Managerの通常/direct接続が同じ本番DBを指すかは未確認。既存GitHub SecretsとSecret Managerの値は読み出していない。承認済みmainでの接続検証とruntimeのSecret注入・readiness検証は別段階で行う。
- 保管バックアップの長期保管先・保持期間と、初回公開時の書込み再開先を確定する。今回のSQLite以後の書込みはNeonへ自動同期されない。
- [卒業要件マスタ](../backend/seeds/requirements.md)にある未確認事項と対象科目転記を継続管理する。

以前の空DB・未移行という状態は[事前監査](pre-production-audit.md)の過去の実測記録であり、本番DBの現在値はこの記録を参照する。
