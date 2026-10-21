# アーキテクチャとディレクトリ構成

実行するアプリ、業務モジュール、共通基盤を分ける。バックエンドとフロントエンドの依存管理は、それぞれ`backend/`と`frontend/`に維持する。

```text
project/
├── backend/
│   ├── apps/
│   │   ├── api/{controllers,schemas,middleware}/  # Goの外部HTTP
│   │   ├── bridge/{controllers,schemas,middleware}/ # Pythonの内部HTTP
│   │   ├── cli/handlers/                          # マスタ投入
│   │   └── settings.py
│   ├── modules/{accounts,grades,subjects,requirements}/
│   │   ├── public.py / composition.py
│   │   ├── domain/{value_objects,services,errors}/
│   │   ├── application/{dto,use_cases,services,ports,queries,uow,errors}/
│   │   └── infrastructure/
│   │       ├── persistence/
│   │       │   ├── models/
│   │       │   ├── repositories/
│   │       │   ├── queries/
│   │       │   └── unit_of_work.py
│   │       └── external_services/
│   ├── shared/
│   ├── migrations/
│   ├── scripts/                                 # 仕様生成・性能計測
│   ├── seeds/
│   └── tests/{unit,integration,contract,e2e,support}/
├── frontend/
│   ├── src/
│   │   ├── apps/web/{composition,pages,components,hooks,layouts}/
│   │   ├── modules/{accounts,profiles,grades,subjects,requirements}/
│   │   │   ├── public.ts / composition.ts
│   │   │   ├── domain/{entities,value_objects,services}/
│   │   │   ├── application/{dto,use_cases,services,ports,queries,errors}/
│   │   │   └── infrastructure/external_services/schemas/
│   │   └── shared/infrastructure/
│   └── tests/{unit,contract}/
└── docs/
    ├── architecture.md
    └── decisions/
```

これは使う役割を示す構成図であり、全モジュールに全ディレクトリを作るものではない。Worker、イベント配信、メッセージングは現在の機能に存在しない。フロントエンドにもDBのUnit of Workは追加しない。

各操作は1つのUseCaseと`execute`を持つ。バックエンド23操作、フロントエンド19操作の境界を維持する。モジュールの`public`はDomainとApplicationの契約を公開し、`composition`が内部の具体実装を組み立てる。アプリのComposition Rootはモジュールのファクトリーを呼出し、HTTPやReactへ接続する。モジュールからアプリへ依存しない。

Domainは業務上の型・不変条件・計算を所有する。Applicationは入出力DTO、認可を含む実行手順とトランザクション境界を所有する。DTOを返す読取り契約はApplicationの`queries`、書込みを含む取得保存契約と外部処理の抽象は`ports`、トランザクションの抽象は`uow`へ置く。Infrastructureがこれらを実装する。

実行経路はVite `:5173` → Go `:8000` → Python `:8001` → SQLiteを維持する。APIのURL、Cookie・CSRF、DBスキーマ、判定履歴JSON、シードの内容は配置変更の対象外とする。

起動・確認は既存の`make dev`、`make check`、`make test`、`make build`を使う。CLIを直接使う場合は`backend/`で`uv run --locked python -m apps.cli seed-subjects --file seeds/cs_2026.json`、続いて`seed-requirements --file seeds/cs_requirements_2026.json`を実行する。

- [バックエンドの詳細](backend_architecture.md)
- [フロントエンドの詳細](frontend_architecture.md)
- [配置の選択理由](decisions/0001-directory-layout.md)
