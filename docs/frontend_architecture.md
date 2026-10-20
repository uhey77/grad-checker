# フロントエンドの構成

バックエンドと同じ4層の責務・依存方向を維持する。
domain・application・infrastructureは業務モジュールにまとめ、presentationはReactの役割ごとにsrc直下へ配置する。
React・TypeScript・Viteを使用する。現在はユーザー名登録・復旧・ログイン画面、ログイン後の所属設定・成績入力と開発用科目一覧。卒業・修了判定と本人専用履歴も実装する。

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
通信はGoの外部API `/api/dev/subject-list` を利用し、Pythonのブリッジ通信やDBを参照しない。
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

認証モジュールは `modules/accounts/`。バックエンドは `application/auth.go` と `infrastructure/auth_client.go`、Pythonは `grad_checker_accounts/{domain,application,infrastructure}/` に配置する。外部HTTPとCookieは `api/presentation/auth.go`、ブリッジアダプターは `go_bridge_auth.py`。画面は `pages/accounts/AuthGate.tsx`、入力部品は `components/accounts/AuthForm.tsx`、状態管理は `hooks/accounts/useAuth.ts`。通信はaccountsモジュール内の取得契約を通し、アプリのcompositionで組み立てる。Pythonの入力・出力契約はPydanticを用い、dataclassは使用しない。

再現手順と認証設定は[認証の開発手順](auth_development.md)を参照する。

## 2026-10-16の認証・科目一覧の整備

既存の配色と科目一覧の構成を維持し、実装済みAPIに接続する認証と閲覧操作を整備した。

認証フォームは日本語で入力を検証し、エラーのある入力欄へフォーカスする。
API・通信エラー時はユーザー名・パスワード・復旧コードの入力をメモリ内に保持し、再試行できる。
成功後の画面遷移や認証画面の切替でフォームを破棄し、前画面のAPIエラーは切替時に解除する。
復旧コードの表示とコピー・保管確認は `components/accounts/RecoveryCode.tsx` が担当する。
コピーに失敗した場合は手動コピーを案内する。ブラウザーストレージへは保存しない。

`useAuth` は期限のタイマーに加え、画面へ戻った際にセッションを再取得する。
失効を確認したら科目画面を外し、再ログインを案内する。
再確認中の通信障害だけで有効なセッションを破棄しない。
再確認のキャンセルと古い応答の排除を行い、更新操作と競合する応答を反映しない。
別タブのログアウト・復旧は、利用可能な環境ではBroadcastChannelでも反映する。

`useSubjectList` は課程一覧と科目一覧の再試行回数を分ける。
科目取得の失敗では課程の選択肢を保持し、科目一覧だけを再取得する。
課程の取得中・失敗・課程0件・課程内の科目0件・検索結果0件を区別する。
検索条件の解除では並べ替えの選択を維持し、課程切替では検索条件を解除する。

本文へのスキップリンク、入力欄とエラー・説明文の関連付け、認証画面切替時の見出しへのフォーカスを追加した。
狭い画面ではフィルタを1列に配置し、表はフォーカス可能な領域内で横スクロールする。

### 検証範囲

Node.js 22.22.0で次が成功した。

- `make frontend-check`（lint・整形状態・型）
- `npm --prefix frontend test`（13件、DTO・通信・検索・並べ替え・依存境界）
- `make build`

Chromiumで、一時SQLiteにCS学部4課程を投入し、Vite → Go → Pythonの実接続を確認した。
通常の開発DBは使用していない。

| 対象 | ブラウザーで確認した内容 |
| --- | --- |
| 登録・復旧 | 登録、復旧コードのコピー、保管確認前の進行禁止、パスワード再設定、新コードへの更新 |
| フォーム | 日本語の検証表示、エラー項目へのフォーカス、確認用パスワードの不一致、API失敗時の入力保持、画面切替時のエラー解除 |
| セッション | ログイン、再読込みでの維持、別タブのログアウト反映、サーバーでの失効後の画面復帰、ログアウト失敗時の表示 |
| 科目一覧 | AND検索、検索結果0件と条件解除、単位順の並べ替え、126科目／120科目の課程切替、切替時の条件解除 |
| 非同期処理 | 科目取得だけの再試行、課程選択肢の維持、課程を連続切替したときの通信キャンセルと古い応答の除外 |
| 表示・操作 | 375px幅でページ全体の横はみ出しがないこと、表領域の横スクロール、キーボードでの表領域へのフォーカス、本文へのスキップリンク |

失敗・課程0件・科目0件はブラウザーで応答を差し替えて確認した。
期限のタイマーは短い有効期限の認証応答を使い、初期認証取得失敗からの再試行も確認した。
所属保存・成績保存・卒業判定・履歴と、Firefox・Safariは今回の検証に含まない。

## 本人の所属設定

`modules/profiles/` のdomainに本人所属・カリキュラム選択肢、applicationにProfileUseCasesと取得・保存契約、infrastructureにHTTP通信とDTO変換を置く。公開契約はpublic.ts、具体実装の組立てはcomposition.tsとapp/compositionで行う。
`pages/profiles/ProfilePage.tsx` が画面構成、`components/profiles/ProgramForm.tsx` が選択・表示、`hooks/profiles/useProfile.ts` が取得・保存・競合・未保存の状態を担当する。AuthGateからセッションのCSRFと期限切れ処理を渡す。アカウント切替時は本人画面を作り直し、離脱時には通信をキャンセルする。
初期取得は本人情報と選択肢を並列取得する。保存は成功応答でのみ保存済み状態を更新し、失敗時は選択を保持する。409後は再取得を要求し、未保存変更の破棄には確認を挟む。開発用科目一覧の閲覧対象は本人の保存済み所属とは独立している。

### 最新mainとの統合確認

所属設定を追加したmainの取込み後、`make frontend-check`、フロントエンドの16テスト、`make build`が成功した。
一時DBを使ったChromiumの実接続で、登録・復旧コードの保管確認・ログイン・所属未設定表示・所属保存・再読み込みでの復元・開発用科目一覧の展開・検索と条件解除・ログアウトを確認した。
本文へのスキップリンクは、現在表示中の本人画面へ移動する。

## 成績入力画面（2026-10-16）

| 場所 | 責務 |
| --- | --- |
| `modules/subjects/{domain,application,infrastructure}/course-catalog/` | 本人課程から見た科目・分類のモデル、取得契約、絞り込み、`/api/courses`・`/api/categories` の取得とDTO変換 |
| `modules/grades/domain/` | 成績記号・確定状態・履修回次のモデル、再履修の可否と修得状況 |
| `modules/grades/application/` | 取得・保存の契約と `GradeError`、未保存の全集合を編集する純粋関数、成績による絞り込み |
| `modules/grades/infrastructure/` | `/api/me/grades` の取得・保存とDTO変換 |
| `hooks/grades/useGradeEntry.ts` | 科目と成績の並行取得、保存済み・未保存・表示対象の分離、保存・競合・再取得・キャンセル |
| `components/grades/` | 絞り込み、科目表と回次の入力、表示ラベル |
| `pages/grades/GradeEntryPage.tsx` | 成績入力画面の構成 |
| `App.tsx` | ログイン後の画面切替と、所属・成績で共有する更新版の受渡し |

再履修の可否と修得状況の区分は入力補助のためにフロントエンドのdomainにも置く。保存時の判定はバックエンドの業務ルールを正とし、卒業判定の規則は複製しない。

### 検証範囲

`task frontend-check`、`npm --prefix frontend test`（23件）、`task build` が成功した。
一時SQLiteにCS学部4課程を投入し、Vite → Go → Pythonの実接続を内蔵ブラウザー（Chromium）で確認した。通常の開発DBは使用していない。

| 対象 | ブラウザーで確認した内容 |
| --- | --- |
| 所属との連携 | 所属未設定時の案内、所属保存後の成績画面の自動再取得、成績保存後の所属保存が409にならないこと、所属変更後の課程表示 |
| 入力・保存 | 未履修からD・未確定の入力、再履修の追加（前の回次はD・Xのみ、削除は最新回次のみ）、履修年度・学期、保存後の修得状況と背景色、APIの保存内容 |
| 絞り込み | 科目コード検索、履修年度と履修学期の組合せ、0件表示と条件解除 |
| 失敗・競合 | 別経路の保存後の409と保存停止、未保存変更の破棄確認と再取得、取得失敗と再試行、全件取消の確認 |
| 表示 | 375px幅でページの横はみ出しがなく、表領域だけが横スクロールすること |

Firefox・Safari、キーボードだけでの全操作は今回の検証に含まない。

## 表示・状態・通信の共通化（2026-10-16）

画面ごとに同じ情報の表記や状態表示が異なっていたため、共通の部品・Hook・通信基盤へ集約した。

| 場所 | 責務 |
| --- | --- |
| `components/StatusPanels.tsx` | 読み込み中・取得失敗と再試行・0件・入力エラーの表示 |
| `components/SaveBar.tsx`・`ConfirmPanel.tsx` | 保存の失敗・状態・操作の並びと、破棄・全件取消の確認 |
| `components/ScrollTable.tsx`・`FilterFields.tsx`・`PageHeading.tsx` | 横スクロールする表、検索欄と絞り込みの選択欄、画面見出し |
| `components/subjects/labels.ts` | 課程名（学部 ／ 学科 ／ 専攻 ／ コース）、学期名、分類・開講元の区切り、学年共通開講の判定 |
| `components/subjects/SubjectCells.tsx`・`NoMatchingSubjects.tsx` | 科目一覧と成績入力で共通の科目名・区分・種別・単位・開講学期・開講元のセルと検索結果0件 |
| `hooks/useExclusiveAction.ts` | 保存・認証操作を一度に一つだけ実行し、中断した結果を反映しない |
| `hooks/useUnsavedChangesWarning.ts`・`errorMessage.ts` | 未保存時の離脱確認、業務エラーの日本語メッセージの取り出し |
| `shared/infrastructure/http.ts` | Cookie・キャッシュ無効・CSRFの送信、JSON解析、detail抽出、通信失敗とキャンセルの区別 |
| `shared/infrastructure/dtoReader.ts` | DTOの実行時検証。不正値は各モジュールの業務エラーへ変換する |

成績入力の見出しは、所属設定で保存済みの所属と同じ課程の場合に所属設定と同じ課程名で表示する。便覧名・適用入学年度の確認状態は表示しない。所属を取得できない場合は科目APIの課程名で表示する。
開発用科目一覧の課程名も同じ表記とし、固定の学部名の見出しは表示しない。絞り込みの未選択は全画面で「すべて」とする。

`shared/` は業務モジュールのinfrastructureだけが利用でき、モジュール・UI・Reactを参照しない。境界テストで検査する。
読込み処理（複数APIの並列取得と画面状態の初期化）は各画面Hookに残している。


## 卒業要件チェック（2026年10月16日）

`modules/requirements/` のdomainは判定結果、applicationは判定ユースケースと取得契約、
infrastructureは本人専用GETとDTO検証・変換を担当する。`public.ts`とcompositionの境界を維持する。
`GradeEntryPage`が `useGraduationCheck` と `GraduationCheckPanel` を組み合わせ、
成績入力画面の上部にチェックボタン・全体結果・条件別単位・未修得必修・超過換算を表示する。

判定は保存済み成績に対する明示操作とし、未保存の変更・保存中・版競合中は実行しない。
通信中の連打を防ぎ、所属／成績版の変更・編集・画面離脱で通信を中断する。
応答の課程IDと成績版が表示中の保存済みデータに一致しない場合は結果を表示しない。
カリキュラムの確認状態はverified・unverifiedの両方を受け入れ、APIの判定結果・単位を表示する。未知または欠落した確認状態は不正応答として拒否する。
設定不足や未確認の算入規則はAPIの日本語detailを表示し、未達成と区別する。401は認証画面へ戻す。
判定結果はブラウザーストレージへ保存しない。おすすめは判定結果の保存済み候補・理由・状態を表示する。

`CourseRecommendations` は `GraduationResultView` 内で最新詳細・保存直後・過去結果の共通表示を担う。候補の生成・並べ替えはPythonで行い、UIは受け取った順を維持する。`infrastructure/mappers.ts` は候補と寄与条件の重複、状態、正の減少量、開講期を検証し、snake_caseを公開モデルに変換する。推薦導入前の過去結果の欠落・nullだけは情報なしとして扱い、最新結果の欠落は不正応答にする。

### 判定履歴（2026年10月18日）

チェックボタンは `GraduationUseCases.createCheck` で保存済みの成績版とCSRFトークンを `POST /api/checks` へ送り、保存した判定を最新の結果として表示する。
取得先の契約に `listChecks`（`limit`・`offset`）と `getCheck` を追加し、mapperで一覧の要約・過去の判定（当時の入力成績と判定結果）を検証・変換する。
過去の入力成績の科目名は保存済みの判定結果から引き、現在の科目マスタを参照しない。要求と異なる範囲・ID・成績版の応答は不正応答として拒否する。

`useCheckHistory` は一覧（1ページ20件）と選択中の過去の判定を `useRemote` で取得し、ページ切替・画面離脱で古い通信を中断する。401は認証画面へ戻す。
チェック保存後は過去表示を閉じて先頭ページを取り直す。`GraduationCheckPanel` は最新表示と `PastCheckView`（「過去の判定」・判定日時・当時の課程・規則版・判定に使った成績）を切り替え、`CheckHistory` で一覧・ページ移動・取得中・失敗と再試行・0件を表示する。
判定ラベルと日時の表記は `components/requirements/labels.ts` に集約する。共有・公開の操作は設けない。


## マイページと共通ヘッダー（2026-10-16）

`App.tsx` の `StudentScreens` が `useProfile` を呼び、初期画面の決定、所属・成績の共有更新版、保存済み所属の受渡しを担当する。初期画面は最初の本人所属取得後に一度だけ決め、以後は利用者の画面切替を優先する。`ProfilePage` はHookの状態・操作を受け取り、ユーザー名・所属の確認と編集を構成する。`useProfile` が編集状態も管理し、保存成功時だけ編集欄を閉じる。

`AuthGate` は認証済みの場合にセッション・期限切れ処理・ログアウト操作・認証処理の状態を `StudentScreens` へ渡す。未認証の場合は `AppLayout` 内に認証画面を表示する。認証済みの `AppLayout` は `StudentScreens` が配置し、共通レイアウトに業務依存を追加せず `userMenu` スロットへ `components/accounts/UserMenu.tsx` を渡す。ログアウト失敗はメニューが閉じても本文前に表示する。

`UserMenu` は通常のボタンとナビゲーションで構成し、開閉・外側クリック・Escape・フォーカス離脱を扱う。非表示中は `inert` と `aria-hidden` で操作・読み上げ対象から外す。画面切替では本文へ、編集開始では選択欄へ、表示中の保存成功では変更ボタンへフォーカスを移す。CSSの開閉トランジションは動きを減らす設定に対応する。

業務モジュールの公開契約、HTTP・DB、成績入力内の卒業要件チェックは変更しない。四層の責務と依存方向を維持する。


### マイページ変更の検証

`make frontend-check`、`make frontend-test`（31件）、`make build` を実施する。
一時SQLiteに既存の科目・卒業要件シードを投入し、ChromiumでVite → Go → Pythonの実接続を確認した。通常の開発DBは使用していない。

- 所属未設定・設定済みでの初期画面、初回保存後にマイページへ留まること、成績入力への移動。
- 画面往復による所属・成績の未保存入力保持、保存後の再読み込みによる所属復元、成績保存後の所属保存。
- メニューのEnter・Tab・Escape、外側クリック・フォーカス離脱、編集開始・保存後のフォーカス。
- 初期所属取得失敗からの再試行、所属保存失敗の入力保持、409後の保存停止と破棄確認・再取得、ログアウト失敗からの再試行。失敗・409はブラウザーで応答を差し替えた。
- 1280px・375px・320px幅での表示、32文字のユーザー名、メニュー・編集欄の横はみ出し防止、動きを減らす設定。

マイページ変更時点では、既存シードの適用入学年度が未確認のため判定を停止する従来の挙動を確認した。後続の仕様変更でこの停止条件を廃止し、2026年度便覧の判定結果を表示する。Firefox・Safariは今回のブラウザー検証に含めない。


### 適用入学年度による判定停止の廃止（2026-10-16）

2026年度便覧の実シードを一時DBに投入し、確認状態を変更せず、成績0件と必修1単位保存後の判定結果をChromiumで確認した。APIの200応答から20条件と必要・修得・算入・不足単位を表示し、未修得必修と再読込後の再判定も確認した。375px幅でページの横はみ出しがない。`make frontend-check`、32件のフロントエンドテスト、`make build`が成功した。


## ダッシュボード（Issue #42、2026-10-18）

認証後は所属取得の成功時に一度だけダッシュボードを初期表示する。`DashboardPage` は保存済み所属、必要・修得・算入・不足単位、全条件と区分合計の達成概要を表示する。所属未設定ではマイページの所属設定へ案内し、成績0件と概要取得失敗は別の状態として表示する。共通メニューからダッシュボード・成績入力・マイページへ移動でき、既存画面をマウントしたまま表示を切り替えて未保存入力を保持する。

`GraduationUseCases.dashboard` → `GraduationRepository.dashboard` → `HttpGraduationRepository` から `GET /api/me/dashboard` を呼び、共通DTO検証で概要を画面モデルへ変換する。`useDashboard` は `useRemote` により、表示中・保存版・課程・再試行に従って取得し、画面離脱・課程変更時は通信を中断する。異なる課程や既知の保存版より古い結果は表示しない。失敗時は日本語の理由と再試行を表示し、401では再ログインへ戻す。

条件別詳細は利用者の操作時だけ `GET /api/me/graduation-requirements` で取得する。概要と成績版・課程・カリキュラム版・算入規則版が異なる場合は再取得を案内する。ダッシュボードの閲覧・再取得・詳細展開では `POST /checks` を呼ばず、履歴保存は成績入力の明示的なチェック操作に限る。

`GraduationOverview` と `GraduationInfographic` を概要・最新詳細・履歴詳細で共有し、単位と注意文の表示を統一する。

## 2026年10月19日の全課程・修了判定拡張

2026年度の所属選択はProgramCoverageで学位段階・キャンパス・整備状況・根拠を表示する。GraduationCheckPanelで課程別の非単位条件を入力し、requirements/public.tsの契約を通じて保存判定を呼ぶ。DTO検証は各モジュールのinfrastructureに保持し、Reactは修了規則を計算しない。未入力の判定保留と本人申告の参考判定を結果・履歴に表示する。成績表は100件ずつ表示し、検索・絞り込みと全件の入力状態を維持する。

## 成績ルールと公開契約の境界

成績の連番と再履修条件は `modules/grades/domain/attempts.ts` の純粋関数で扱う。編集用Applicationはその規則を呼び出し、`GradeDraftProblem` のコードを返す。`hooks/grades/errors.ts` がコードを日本語の表示文言へ変換し、`useGradeEntry` が表示する。既存の年度範囲・メッセージ・保存操作を維持し、同じ業務条件をバックエンドでも検証する。

モジュールをまたぐ参照は引き続き `public.ts` を使う。公開窓口を経由しても層の依存方向は変わらない。Domainから参照できるのは他モジュールのDomain由来の公開型だけとし、Applicationのユースケース・エラー・検索処理をDomainへ持ち込まない。境界テストは公開名のexport元も確認する。
