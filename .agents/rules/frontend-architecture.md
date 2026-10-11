# フロントエンドのアーキテクチャルール

対象は `frontend/`。React・TypeScript・Viteによる現在の層構成を維持する。
科目一覧の設計意図は [フロントエンドの構成](../../docs/frontend_architecture.md) を参照する。

## 各層の責務

| 場所（frontend/src 以下） | 責務 | 配置例 |
| --- | --- | --- |
| `domain/<機能>/` | UI・通信形式に依存しない業務モデル | 課程、科目、分類経路、開講時期の型 |
| `application/<機能>/` | ユースケース、取得先の契約、検索・並べ替え処理 | `SubjectListRepository`、`SubjectListUseCases`、科目の絞り込み |
| `infrastructure/<機能>/` | HTTP通信、APIのDTO、ドメインモデルへの変換 | `HttpSubjectListRepository`、`dto.ts`、`mappers.ts` |
| `presentation/<機能>/` | React画面、表示ラベル、ユーザー操作、画面状態 | `SubjectListPage`、`SubjectTable`、`labels.ts` |
| `presentation/shared/` | 複数画面で利用する表示・状態管理 | `useRemote` |
| `main.tsx` | 具体的な依存関係の組み立てと画面の起動 | HTTP取得先をユースケースへ注入して画面へ渡す |

## 依存方向

- `domain` は他のアプリ層、React、HTTPのDTOに依存させない。
- `application` は `domain` を参照できる。React・`presentation`・`infrastructure` の具体実装は参照しない。
- 取得先の契約は `application` に置く。通信キャンセル用のブラウザー標準 `AbortSignal` は契約で使用できる。
- `infrastructure` は `application` の契約を実装し、`domain` のモデルに変換する。`presentation` は参照しない。
- `presentation` は `application` と `domain` を参照できる。具体的なHTTP取得先やAPIのDTOは参照しない。
- `main.tsx` でリポジトリとユースケースを生成し、画面へ渡す。

## 実装ルール

- 新しい機能は各層の機能ディレクトリに配置する。既存の科目一覧の構成を参考にする。
- コンポーネントやHookから直接 `fetch` しない。ユースケースと取得先の契約を通して取得する。
- APIの `snake_case` と画面で使用するモデルの変換は `infrastructure` のmapperに集約する。コンポーネント内でDTOを変換しない。
- 再利用する検索・並べ替え処理は `application` に置く。選択値や検索文字列など、ユーザー操作に伴う状態は `presentation` で管理する。
- 表示ラベル・React固有の状態を `domain` へ入れない。業務ルールをJSX内へ埋め込まない。
- ロード中・成功・失敗を明示的に扱い、再試行できるようにする。課程切替や画面離脱時には不要な通信をキャンセルし、古いレスポンスで現在の画面を上書きしない。
- 課程ごとの分類・必修区分、複数の開講時期、出典の注記、適用入学年度の未確認状態を保持する。未確認の情報を確認済みとして表示しない。
- `presentation/shared/` への共通化は、実際に共通の表示・状態管理責務がある場合に行う。
- 集約・値オブジェクト・状態管理ライブラリは、必要な業務処理や画面状態が明確になった時点で導入する。

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
