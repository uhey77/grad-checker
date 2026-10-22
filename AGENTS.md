# エージェント向け共通ルール

- 日本語で回答する。
- 要件や仕様に曖昧な点がある場合は、ユーザーに確認する。
- サブエージェントは、ユーザーが明示的に依頼した場合のみ使用する。

## アーキテクチャルールの読み方

実装・レビューを始める前に、変更対象に応じて次のファイルを読む。
両方に関わる変更では両方を読み、API契約とデータの意味を合わせる。

- バックエンド: [.agents/rules/backend-architecture.md](.agents/rules/backend-architecture.md)
- フロントエンド: [.agents/rules/frontend-architecture.md](.agents/rules/frontend-architecture.md)

ルールは各層の責務と依存方向を定める。要件・判定ルール・出典と未確認事項は `docs/` の該当文書を参照する。API契約は `backend/apps/api/controllers/apidocs/openapi.json`、DB構造は各モジュールのモデル、検証内容は実際のテストを参照する。
文書と実装に矛盾がある場合は、どちらが意図した仕様かをユーザーに確認する。
ユーザーが設計変更を依頼した場合は、実装と関連するルール・設計文書を合わせて更新する。

## Claude Codeとの共有

`CLAUDE.md` はこのファイルへのシンボリックリンクとする。
`.claude/rules/` の各アーキテクチャルールも、対応する `.agents/rules/` のファイルへのシンボリックリンクとする。
共通ルールは `AGENTS.md`、アーキテクチャルールの本文は `.agents/rules/` で編集する。
ルールを追加・削除・改名する場合は、`.claude/rules/` の対応するリンクも更新する。
