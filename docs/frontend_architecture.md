# フロントエンドの構成

バックエンドと同じ4層の責務・依存方向を維持する。
domain・application・infrastructureは業務モジュールにまとめ、presentationはReactの役割ごとにsrc直下へ配置する。
React・TypeScript・Viteを使用する。現在はユーザー名登録・復旧・ログイン画面と、ログイン後の開発用科目一覧。成績保存・卒業判定画面は未実装。

## 配置

```text
frontend/
├── package.json / package-lock.json / tsconfig.json  # 共通の依存管理・型設定
├── src/
│   ├── main.tsx                          # React起動
│   ├── App.tsx                           # アプリ全体の画面配置
│   ├── app/composition/createApplication.ts  # 設定・依存の組み立て
│   ├── layouts/AppLayout.tsx             # 共通レイアウト
│   ├── pages/subjects/SubjectListPage.tsx # 画面構成
│   ├── components/subjects/              # 科目専用の表示部品
│   │   ├── ProgramSelector.tsx           # 課程選択
│   │   ├── SubjectSummary.tsx            # 科目数サマリー
│   │   ├── SubjectFilters.tsx            # 検索・絞り込み・並べ替え操作
│   │   ├── SubjectTable.tsx              # 一覧表示
│   │   └── labels.ts                     # 表示ラベル
│   ├── hooks/
│   │   ├── useRemote.ts                  # 業務共通の非同期状態・キャンセル
│   │   └── subjects/
│   │       ├── useSubjectList.ts         # 画面状態・操作・取得の連携
│   │       └── errors.ts                 # 業務エラーから表示文への変換
│   └── modules/subjects/
│       ├── public.ts                     # UI・他モジュールへの公開契約
│       ├── composition.ts                # 科目モジュールの具体実装の生成
│       ├── domain/subject-list/          # 課程・科目・分類・開講時期のモデル
│       ├── application/
│       │   ├── errors/                   # 取得失敗のエラー契約
│       │   └── subject-list/             # ユースケース・取得契約・検索・並べ替え
│       └── infrastructure/subject-list/  # HTTP・DTO・モデル変換
└── tests/                                # 契約・通信・依存境界テスト
```

科目専用のUIもcomponents・hooks・pagesに置き、各ディレクトリ内でsubjectsにまとめる。
共通部品は各ディレクトリの共通領域へ配置する。業務領域をmodules/subjects、一覧という操作を内部のsubject-listとする。
画像素材・Context・多言語化・API生成コードなどは実装する時点で対応するディレクトリを追加する。
モジュールごとのpackage.jsonやロックは作らず、フロントエンド全体で依存管理する。

## 4層と依存境界

| 層 | 配置 | 責務 |
| --- | --- | --- |
| domain | modules/subjects/domain | UI・通信形式に依存しないモデル |
| application | modules/subjects/application | ユースケース・取得契約・検索・並べ替え・エラー |
| infrastructure | modules/subjects/infrastructure | HTTP・DTO・モデル変換 |
| presentation | pages・components・hooks・layouts・App.tsx | Reactの画面・操作・状態・表示変換 |

- domainは他の層、React、HTTPのDTOに依存しない。
- applicationはdomainを利用する。React、infrastructure、UIに依存しない。
- infrastructureはapplicationの契約を実装し、domainを利用できる。UIを参照しない。
- UIはmodules/subjects/public.tsを通してモデル・ユースケースの型・検索・並べ替え・エラー契約を利用する。DTO・HTTP実装・内部ファイルを直接参照しない。
- public.tsはdomainとapplicationの契約だけを明示的に公開し、HTTP実装・composition・UIを公開しない。
- モジュールはappとUIを参照しない。他モジュールの利用はそのpublic.tsの公開契約に限定し、各層の依存制約も適用する。
- モジュールのcompositionだけが内部の具体実装を生成する。app/compositionだけがそのcompositionを利用し、設定を渡す。
- 業務共通のuseRemoteは科目モジュールを参照しない。HookはPage・表示部品を参照せず、表示部品はPageを参照しない。

## 表示・状態・通信

main.tsxがアプリを起動する。createApplicationがAPIのURLを科目モジュールへ渡して依存を組み立て、Appがレイアウトと画面へ接続する。
useSubjectListが課程選択・フィルタ・並べ替え・再試行と取得処理の連携を担当する。
Pageは画面構成、各コンポーネントはpropsで受け取るデータの表示と操作を担当する。表示部品はHTTP取得や依存の組み立てを行わない。

画面用Hookはユースケースを呼び、ユースケースはSubjectListRepositoryの取得契約を利用する。
単純な委譲でもユースケース境界を維持する。
通信はGoの外部API `/api/dev/subject-list` を利用し、Python内部通信やDBを参照しない。
卒業判定の規則はバックエンドに置き、フロントエンドで複製しない。

HTTP失敗はinfrastructureでSubjectListErrorに変換する。404・409・5xx・その他HTTP失敗をコードで区別し、日本語detailを保持する。
ネットワーク失敗とJSON解析失敗も区別し、キャンセルは変換せず伝播する。
hooks/subjects/errors.tsがコードとdetailから表示文を決める。useRemoteはエラーをunknownとして保持し、業務固有の文言を持たない。
正常JSONのDTO変換は型契約に基づき、実行時スキーマ検証は未導入。

useRemoteはロード・成功・失敗、離脱時のキャンセル、古い応答の排除を担当する。
キャッシュや複数画面の再取得管理は未導入。現在の選択状態は科目画面内で保持する。
成績入力では保存済みデータ、未保存の編集状態、表示対象を分け、絞り込みで編集内容を失わない構成にする。

科目モデルは選択課程における分類・必修区分を含む。同じ科目でも課程によって区分が異なる。
全開講時期、便覧注記、出典、適用入学年度の未確認状態を保持する。
表示仕様は[学生画面設計](screen_design/student_screen_design.md)に従う。

## 確認

- `task frontend-check` / `make frontend-check`: lint・整形・型。
- `npm --prefix frontend test`: DTO変換・検索・並べ替え・取得契約・HTTPエラー・キャンセル・依存境界。
- `task build` / `make build`: 型チェックを含むビルド。
- `task dev` / `make dev`: Go・Pythonと接続して画面確認。

境界テストはTypeScript ASTでimport・export・動的importとfetch呼出しを検査する。
テスト中のTypeScriptは既存コンパイラーで変換する。画面の状態遷移と操作はブラウザーでも確認する。

### 2026-10-11の構成変更後の確認

lint・整形・型チェック、8件のテスト、ビルドが成功。
一時DBを使うVite → Go → Pythonの実接続をブラウザーで確認した。
検索・必修条件とのAND絞り込み・0件・条件解除・単位順の並べ替えが動作した。
課程を連続で切り替え、ロード中に前の一覧を隠し、最後に選んだ社会情報専攻の120科目を表示することを確認した。
人工知能・情報基盤コースでは126科目を確認した。
Python応答のタイムアウトによる日本語エラーと、サービス復旧後の再試行も確認した。
通常の開発DBは使用していない。認証・成績保存・判定画面の検証は含まない。

## アカウント認証の追加（2026-10-11）

認証モジュールは `modules/accounts/`。バックエンドは `application/auth.go` と `infrastructure/auth_client.go`、Pythonは `grad_checker_accounts/{domain,application,infrastructure}/` に配置する。外部HTTPとCookieは `api/presentation/auth.go`、内部アダプターは `internal_auth.py`。画面は `pages/accounts/AuthGate.tsx`、入力部品は `components/accounts/AuthForm.tsx`、状態管理は `hooks/accounts/useAuth.ts`。通信はaccountsモジュール内の取得契約を通し、アプリのcompositionで組み立てる。Pythonの入力・出力契約はPydanticを用い、dataclassは使用しない。

再現手順と認証設定は[認証の開発手順](auth_development.md)を参照する。
