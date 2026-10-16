# フロントエンドのアーキテクチャルール

対象は `frontend/`。React・TypeScript・Viteを使用し、バックエンドと同じ4層の責務・依存方向を守る。domain・application・infrastructureは業務モジュール内、presentationはsrc直下のUIディレクトリに配置する。
科目一覧の設計意図は [フロントエンドの構成](../../docs/frontend_architecture.md) を参照する。

[バックエンドの構成](../../docs/backend_architecture.md)に従い、ViteからGoの外部APIを呼び出す。
Pythonの内部通信を画面から直接呼ばない。内部通信の包絡形式やDB処理をフロントエンドに追加しない。

## 各層の責務

| 場所（frontend/src 以下） | 責務 | 配置例 |
| --- | --- | --- |
| `modules/<業務領域>/domain/` | UI・通信形式に依存しない業務モデル | 課程、科目、分類経路、開講時期の型 |
| `modules/<業務領域>/application/` | ユースケース、取得先の契約、検索・並べ替え処理 | `SubjectListRepository`、`SubjectListUseCases`、科目の絞り込み |
| `modules/<業務領域>/infrastructure/` | HTTP通信、APIのDTO、ドメインモデルへの変換 | `HttpSubjectListRepository`、`dto.ts`、`mappers.ts` |
| `pages/<業務領域>/` | 画面構成 | `SubjectListPage` |
| `components/<業務領域>/` | 表示部品・表示ラベル・ユーザー操作 | `SubjectTable`、`SubjectFilters`、`ProgramSelector`、`SubjectSummary` |
| `hooks/<業務領域>/` | 画面状態・操作とユースケースの連携・エラー表示変換 | `useSubjectList`、`errors.ts` |
| `hooks/`・`components/`・`layouts/` | 業務に依存しない共通Hook・表示部品・レイアウト | `useRemote`、`useExclusiveAction`、`StatusPanels`、`SaveBar`、`AppLayout` |
| `components/subjects/labels.ts`・`SubjectCells.tsx` | 画面をまたぐ科目・課程の表記と表のセル | `programLabel`、`OfferingsCell` |
| `shared/infrastructure/` | 業務に依存しないHTTP通信とDTO検証 | `requestJson`、`fetchJson`、`createDtoReader` |
| `modules/<業務領域>/public.ts` | UI・他モジュールへの公開契約 | モデル・ユースケースの型・検索・エラー |
| `modules/<業務領域>/composition.ts` | モジュール内の具体実装の組み立て | HTTP取得先をユースケースへ注入 |
| `app/composition/` | モジュールの組み立て・設定の受渡し | `createApplication` |
| `App.tsx` | アプリ全体の画面配置 | `AppLayout` 内に画面を配置 |
| `main.tsx` | Reactの起動 | アプリを生成しReactへ渡す |

## 依存方向

- `domain` は他のアプリ層、React、HTTPのDTOに依存させない。
- `application` は `domain` を参照できる。React・`presentation`・`infrastructure` の具体実装は参照しない。
- 取得先の契約は `application` に置く。通信キャンセル用のブラウザー標準 `AbortSignal` は契約で使用できる。
- `infrastructure` は `application` の契約を実装し、`domain` のモデルに変換する。`presentation` は参照しない。
- `shared/infrastructure/` は各モジュールの `infrastructure` だけが利用する。`shared/` は自身の中だけを参照し、モジュール・UI・`app`・Reactに依存しない。業務エラーの型と日本語の文言は呼出し側のモジュールが渡す。
- presentation（`pages`・`components`・`hooks`・`layouts`・`App.tsx`）はモジュールの `public.ts` を通してapplicationとdomainを利用する。具体的なHTTP取得先やAPIのDTOは参照しない。
- 各モジュールの `composition.ts` でリポジトリとユースケースを生成する。`app/composition/` が設定を渡し、`main.tsx` がアプリを起動する。
- モジュールは `app`・UIディレクトリ・`App.tsx`・`main.tsx` を参照しない。他モジュールの内部ファイルは参照せず、その `public.ts` に公開された契約を利用する。公開契約の利用にも各層の依存方向を適用する。
- `public.ts` はdomain・applicationの契約だけを公開する。infrastructure・composition・UIは公開しない。`composition.ts` の利用は `app/composition/` に限定する。
- 業務共通のHook・表示部品は業務モジュールに依存させない。科目専用のUIは各ディレクトリ内の `subjects/` に置く。HookからPage・表示部品を参照せず、表示部品からPageを参照しない。

## 実装ルール

- 新しい業務領域は `modules/<業務領域>/` に配置し、その内部にdomain・application・infrastructureと操作別のディレクトリを設ける。UIはsrc直下の対応するディレクトリに配置する。既存の科目一覧の構成を参考にする。
- 依存定義・ロック・型設定は `frontend/` 直下に統一し、モジュールごとに重複させない。
- 単純な委譲でもユースケース境界を維持する。Pageは画面構成、画面用Hookは状態・操作・取得の連携、表示部品は個別の表示と操作を担当する。
- applicationで取得失敗のエラー契約を定義し、infrastructureでHTTP・通信エラーから変換する。presentationで日本語detailとコードから表示を決める。キャンセルは変換せず、共通の非同期Hookに業務固有の文言を置かない。
- コンポーネントやHookから直接 `fetch` しない。ユースケースと取得先の契約を通して取得する。
- APIの `snake_case` と画面で使用するモデルの変換は `infrastructure` のmapperに集約する。コンポーネント内でDTOを変換しない。
- 再利用する検索・並べ替え処理は `application` に置く。選択値や検索文字列など、ユーザー操作に伴う状態は `presentation` で管理する。
- 表示ラベル・React固有の状態を `domain` へ入れない。業務ルールをJSX内へ埋め込まない。
- ロード中・成功・失敗を明示的に扱い、再試行できるようにする。課程切替や画面離脱時には不要な通信をキャンセルし、古いレスポンスで現在の画面を上書きしない。
- 課程ごとの分類・必修区分、複数の開講時期、出典の注記、適用入学年度の未確認状態を保持する。未確認の情報を確認済みとして表示しない。
- 共通Hook・表示部品への共通化は、実際に共通の表示・状態管理責務がある場合に行う。
- 同じ情報は全画面で同じ部品・関数で表示する。読み込み中・失敗・0件・入力エラーは `StatusPanels`、保存の状態と操作は `SaveBar`、破棄・取消の確認は `ConfirmPanel`、表の横スクロールは `ScrollTable`、絞り込み欄は `FilterFields` を使う。課程名は `programLabel`、科目の各列は `SubjectCells` で表示し、画面内に表記を再実装しない。
- HTTP取得先は `shared/infrastructure/http.ts` で通信・JSON解析・detail抽出・通信失敗の変換を行い、モジュール内で `fetch` の手順を重複させない。DTOの実行時検証は `createDtoReader` を使う。
- 集約・値オブジェクト・状態管理ライブラリは、必要な業務処理や画面状態が明確になった時点で導入する。

認証画面はユーザー名・パスワードによる登録とログイン、復旧コードによる再設定を扱う。復旧コードは登録・再設定成功時に一度だけ表示し、保管確認後にログインへ進める。コード・パスワード・セッション原値をブラウザーストレージへ保存しない。

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

- [フロントエンドの構成](../../docs/frontend_architecture.md)
- [学生画面設計](../../docs/screen_design/student_screen_design.md)
- [API仕様](../../docs/api_specification.md)
- [要件定義](../../docs/RDD.md)

設計文書に記載された機能がすべて実装済みであるとは扱わない。
