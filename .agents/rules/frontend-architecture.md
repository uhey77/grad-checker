# フロントエンドのアーキテクチャルール

対象は `frontend/`。React・TypeScript・Viteを使用し、バックエンドと同じ4層の責務・依存方向を守る。domain・application・infrastructureは業務モジュール内、presentationはapps/web内のUIディレクトリに配置する。

ViteからGoの外部APIを呼び出す。
Pythonのブリッジ通信を画面から直接呼ばない。ブリッジ通信の包絡形式やDB処理をフロントエンドに追加しない。

## 各層の責務

| 場所（frontend/src 以下） | 責務 | 配置例 |
| --- | --- | --- |
| `modules/<業務領域>/domain/` | UI・通信形式に依存しない業務モデル | 課程、科目、分類経路、開講時期の型 |
| `modules/<業務領域>/application/` | ユースケース、取得先の契約、検索・並べ替え処理 | `use_cases/`、`dto/`、`ports/`、`services/`、`errors/`で役割別に配置 |
| `modules/<業務領域>/infrastructure/` | HTTP通信、APIのDTO、ドメインモデルへの変換 | `HttpSubjectListRepository`、`dto.ts`、`mappers.ts` |
| `apps/web/pages/<業務領域>/` | 画面構成 | `SubjectListPage` |
| `apps/web/components/<業務領域>/` | 表示部品・表示ラベル・ユーザー操作 | `SubjectTable`、`SubjectFilters`、`ProgramSelector`、`SubjectSummary` |
| `apps/web/hooks/<業務領域>/` | 画面状態・操作とユースケースの連携・エラー表示変換 | `useSubjectList`、`errors.ts` |
| `apps/web/hooks/`・`apps/web/components/`・`apps/web/layouts/` | 業務に依存しない共通Hook・表示部品・レイアウト | `useRemote`、`useExclusiveAction`、`StatusPanels`、`SaveBar`、`AppLayout` |
| `apps/web/components/subjects/labels.ts`・`SubjectCells.tsx` | 画面をまたぐ科目・課程の表記と表のセル | `programLabel`、`OfferingsCell` |
| `shared/infrastructure/` | 業務に依存しないHTTP通信とDTO検証 | `requestJson`、`fetchJson`、`createDtoReader` |
| `modules/<業務領域>/public.ts` | UI・他モジュールへの公開契約 | モデル・ユースケースの型・検索・エラー |
| `modules/<業務領域>/composition.ts` | モジュール内の具体実装の組み立て | HTTP取得先をユースケースへ注入 |
| `apps/web/composition/` | モジュールの組み立て・設定の受渡し | `createApplication` |
| `App.tsx` | アプリ全体の画面配置 | `AppLayout` 内に画面を配置 |
| `main.tsx` | Reactの起動 | アプリを生成しReactへ渡す |
| `i18n/` | presentation共通の表示言語・翻訳・文言の変換 | 初期言語、英語リソース、保存、既知detailの翻訳 |

## 依存方向

- `domain` は他のアプリ層、React、HTTPのDTOに依存させない。
- `application` は `domain` を参照できる。React・`presentation`・`infrastructure` の具体実装は参照しない。
- 取得先の契約は `application` に置く。通信キャンセル用のブラウザー標準 `AbortSignal` は契約で使用できる。
- `infrastructure` は `application` の契約を実装し、`domain` のモデルに変換する。`presentation` は参照しない。
- `shared/infrastructure/` は各モジュールの `infrastructure` だけが利用する。`shared/` は自身の中だけを参照し、モジュール・UI・`app`・Reactに依存しない。業務エラーの型と日本語の文言は呼出し側のモジュールが渡す。
- presentation（`pages`・`components`・`hooks`・`layouts`・`App.tsx`）はモジュールの `public.ts` を通してapplicationとdomainを利用する。具体的なHTTP取得先やAPIのDTOは参照しない。
- 各モジュールの `composition.ts` でリポジトリとユースケースを生成する。`apps/web/composition/` が設定を渡し、`main.tsx` がアプリを起動する。
- モジュールは `app`・UIディレクトリ・`App.tsx`・`main.tsx` を参照しない。他モジュールの内部ファイルは参照せず、その `public.ts` に公開された契約を利用する。公開契約の利用にも各層の依存方向を適用する。Domainから他モジュールの公開契約を参照するときはDomain由来の型だけに限定し、境界テストでexport元も検査する。
- `public.ts` はdomain・applicationの契約だけを公開する。infrastructure・composition・UIは公開しない。`composition.ts` の利用は `apps/web/composition/` に限定する。
- 業務共通のHook・表示部品は業務モジュールに依存させない。科目専用のUIは各ディレクトリ内の `subjects/` に置く。HookからPage・表示部品を参照せず、表示部品からPageを参照しない。

## 実装ルール

- 新しい業務領域は `modules/<業務領域>/` に配置し、その内部にdomain・application・infrastructureと操作別のディレクトリを設ける。UIはapps/web内の対応するディレクトリに配置する。既存の科目一覧の構成を参考にする。
- 依存定義・ロック・型設定は `frontend/` 直下に統一し、モジュールごとに重複させない。
- 公開操作は`application/use_cases/<操作>UseCase.ts`の1操作1クラスとし、実行メソッドを`execute`に統一する。複数操作を持つUseCaseクラスは置かない。`AuthUseCases`などの集合型は`ports/`のreadonlyな注入用契約だけに使い、実装は持たせない。Compositionで操作ごとのインスタンスを作り、Hookから各`execute`を呼ぶ。
- Application直下へファイルを並べず、入出力は`dto/`、書込みを含むRepository・注入型は`ports/`、読取り専用契約は`queries/`、検索・並べ替え・編集の共通処理は`services/`、エラーは`errors/`に分ける。未使用の役割の空ディレクトリや旧パスの互換用ファイルは残さない。
- 単純な委譲でもユースケース境界を維持する。Pageは画面構成、画面用Hookは状態・操作・取得の連携、表示部品は個別の表示と操作を担当する。
- applicationで取得失敗のエラー契約を定義し、infrastructureでHTTP・通信エラーから変換する。presentationで日本語detailとコードから表示を決め、選択言語へ翻訳する。キャンセルは変換せず、共通の非同期Hookに業務固有の文言を置かない。
- コンポーネントやHookから直接 `fetch` しない。ユースケースと取得先の契約を通して取得する。
- APIの `snake_case` と画面で使用するモデルの変換は `infrastructure` のmapperに集約する。コンポーネント内でDTOを変換しない。
- 再利用する検索・並べ替え処理は `application/services/` に置く。選択値や検索文字列など、ユーザー操作に伴う状態は `presentation` で管理する。
- 表示ラベル・React固有の状態を `domain` へ入れない。業務ルールをJSX内へ埋め込まない。成績の連番・再履修はDomainで判定し、編集入力の問題はApplicationがコードで返し、hooksで日本語の表示文言へ変換する。
- 翻訳は`i18n/`とpresentationに閉じ、業務モジュールから参照しない。表示文言は翻訳リソースを使用し、科目・所属・分類・出典などの公式データは原文を保持する。Hookのエラー・通知は原文で保持して描画時に翻訳し、切替で入力や状態を初期化しない。既知detailは翻訳し、未知detailの意味は推測しない。
- ロード中・成功・失敗を明示的に扱い、再試行できるようにする。課程切替や画面離脱時には不要な通信をキャンセルし、古いレスポンスで現在の画面を上書きしない。
- 課程ごとの分類・必修区分、複数の開講時期、出典の注記、適用入学年度の未確認状態をデータとして保持する。未確認の情報を確認済みとして表示しない。所属情報の出典・適用入学年度は画面に表示しない。判定を停止する未確認事項とその理由は表示する。
- 共通Hook・表示部品への共通化は、実際に共通の表示・状態管理責務がある場合に行う。
- 同じ情報は全画面で同じ部品・関数で表示する。読み込み中・失敗・0件・入力エラーは `StatusPanels`、保存の状態と操作は `SaveBar`、破棄・取消の確認は `ConfirmPanel`、表の横スクロールは `ScrollTable`、絞り込み欄は `FilterFields` を使う。課程名は `programLabel`、科目の各列は `SubjectCells` で表示し、画面内に表記を再実装しない。
- HTTP取得先は `shared/infrastructure/http.ts` で通信・JSON解析・detail抽出・通信失敗の変換を行い、モジュール内で `fetch` の手順を重複させない。DTOの実行時検証は `createDtoReader` を使う。
- 集約・値オブジェクト・状態管理ライブラリは、必要な業務処理や画面状態が明確になった時点で導入する。

認証画面はユーザー名・パスワードによる登録とログイン、復旧コードによる再設定を扱う。復旧コードは登録・再設定成功時に一度だけ表示し、保管確認後にログインへ進める。コード・パスワード・セッション原値をブラウザーストレージへ保存しない。

ヘッダーと本文の共通配置は `AppLayout` に集約し、同じコンテナーで幅と左右の余白を揃える。画面切替時の本文へのフォーカスと先頭へのスクロールも共通レイアウトで扱い、画面の高さやスクロールバーの有無でヘッダーの位置を変えない。認証後はヘッダーのアプリ名とチェックアイコンからダッシュボードへ移動する。マイページはヘッダーの専用ボタンから移動し、ヘッダーではマイページの右側に言語切替を置く。成績入力はマイページから移動し、成績が未登録のときだけダッシュボードにも入力への案内を表示する。所属名の確認・編集はマイページへ集約し、ダッシュボードには所属カードを表示しない。所属未設定の場合だけ、共通の未設定表示と「所属を設定」を表示する。

所属の編集中は操作を保存・キャンセルに限定し、通常時の再取得操作は表示しない。キャンセルでは未保存の選択を保存済みの所属へ戻して編集を閉じる。所属未設定でもキャンセルできるようにする。取得失敗時は再試行を表示し、更新競合を検知した場合はキャンセル時に最新の所属を取得する。

成績入力画面は成績の入力・編集・保存を担当する。ダッシュボードは保存済みデータから卒業・修了要件の概要と同じ版の詳細を取得し、単位の進捗グラフ・科目区分別の単位・不足単位と履修候補を常時表示する。科目候補は必修・選択必修・選択にまとめ、総単位と区分の合計の一覧は表示しない。総単位の不足を補える候補のうち、これらに表示されない科目はその他の履修候補に表示する。未修得の必修科目は全件表示し、選択・選択必修の候補は条件ごとに開閉できるようにする。内訳の最低条件は対応する選択必修の下に表示し、親が充足済みでも不足した内訳を省略しない。開講学期と判定時の状態は各科目に常時表示せず、別のおすすめ科目一覧を設けない。パネル上部の見出し・説明文・手動判定ボタン・総合判定ラベルと、本人申告の修了条件の入力欄は表示しない。画面では判定履歴の一覧取得・過去結果への切替を行わない。概要・詳細の取得に失敗した場合だけ再試行操作を表示し、再試行では最新の概要と同じ版の詳細を取得する。画面切替で未保存の成績を失わないようにし、画面離脱・所属変更・保存済み成績の更新では古い結果を表示しない。

判定結果の条件一覧は、総必要単位を表の外の概要に表示し、科目区分を行、合計・必修・選択・選択必修を列として表示する。内訳の最低条件は「人文（最低2単位）」などの独立した行を保ち、算入・必要単位と判定を選択必修の列に表示する。行は保存済みの親子関係で字下げし、折りたたまない。必修・選択は親と同じ分類IDを持つ場合に親の行へまとめる。親や分類が一致しない条件を推測で統合せず、各条件の単位と判定を保持する。セルの単位表示は「算入 / 必要」に統一し、修得・不足の補足行は表示しない。APIの`required_course_breakdowns`は表示用の必修内訳として読み、同じ親・同じ分類IDの選択必修と同じ行へ表示する。対応する行がなければ独立した科目区分の行を作る。古い保存済み結果に内訳を推測で補完しない。

## 変更後の確認

コマンドはリポジトリルートで実行する。TaskとMakeのどちらも利用できる。

| 確認 | コマンド |
| --- | --- |
| lint・整形状態・型 | `task frontend-check` または `make frontend-check` |
| テスト | `npm --prefix frontend test` |
| 型チェックを含むビルド | `task build` または `make build` |

処理を変更した場合は、該当するDTO変換・検索条件・取得契約と層の依存方向をテストで確認する。
画面を変更した場合は、表示と操作に加え、ロード・失敗・再試行・課程切替時の状態をブラウザーで確認する。
文書だけの変更では、リンク・配置例・コマンドと実装の整合性を確認する。

## 関連文書

- [バックエンドのルール](backend-architecture.md)
- [OpenAPI](../../backend/apps/api/controllers/apidocs/openapi.json)

設計文書に記載された機能がすべて実装済みであるとは扱わない。

## Web入口と役割別配置

- Reactの起動・アプリのcomposition・画面・部品・Hook・レイアウトは`src/apps/web/`へ集約する。業務は`src/modules/`、実際に共通の通信処理は`src/shared/`に置き、modulesからappsへ依存しない。
- Domainは`entities/`・`value_objects/`・`services/`に分け、入出力の集合・検索結果・更新要求は`application/dto/`へ置く。APIのsnake_caseや検証処理は`infrastructure/external_services/schemas/`に保持する。
- HTTP取得先は`infrastructure/external_services/`でApplication契約を実装する。DBを持たないフロントエンドにpersistenceやUoWを形式だけ追加しない。
- テストは純粋な業務・編集・検索・境界の`tests/unit/`と、HTTP・DTOの`tests/contract/`へ分け、既存の`npm test`で一括実行する。

## 本番ホスティング

- 既存Vercelプロジェクト（Root Directory: frontend、Node.js 24）を再利用する。`vercel.mjs`が非機密のCLOUD_RUN_API_ORIGINから`/api`のHTTPS中継先を構成する。Reactの取得先は相対`/api`を維持し、VITE_*へDB認証情報を渡さない。
- API中継はSPAフォールバックより先に評価し、`/api`をindex.htmlに書き換えない。APIはno-store、画面はCSP等のセキュリティヘッダーを設定する。Git連携による無承認公開は無効化し、GitHub Actionsのproduction承認ゲートからテスト済みの本番用ビルドをpromoteする。
