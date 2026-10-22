# 0001: 実行アプリと業務モジュールを分け、層の内部を役割で整理する

状態: 採用

Pythonの業務コードに`modules/<業務>/grad_checker_<業務>/`という重複階層があり、HTTPの入口、取得保存契約、DBモデル・Repository・UoWの配置から責務を読み取りにくかった。フロントエンドも画面とアプリの起動処理が`src/`直下に分散していた。

実行入口をバックエンドの`apps/api`・`apps/bridge`・`apps/cli`、フロントエンドの`src/apps/web`へまとめる。業務コードは`modules/<業務>/`直下のDomain・Application・Infrastructureに置く。各モジュールに公開契約とCompositionを置き、アプリのComposition Rootがモジュールを接続する。

ApplicationのRepositoryは現在、Application DTOを返す。これらを名前だけで`domain/repositories`へ移すとDomainがApplicationへ依存するため、読取り専用の契約を`application/queries`、書込みを含む契約を`application/ports`に置く。集約の取得保存をDomainの型だけで表現する必要が生じたときに、DomainのRepositoryを導入する。

UoWの抽象は`application/uow`、SQLの実装は`infrastructure/persistence/unit_of_work.py`に分ける。RepositoryはBEGIN・commit・rollbackを行わず、UseCaseが既存のread/write境界を決める。読取り専用のSQLを`persistence/queries`、書込みを持つ実装を`persistence/repositories`、テーブルを`persistence/models`へ分ける。

共通化済みのClock・業務エラー・DB接続・UoW・ブリッジ通信を`shared`へ集める。既存のCS2026データ改訂は`migrations`へ移し、照合条件と実行タイミングを維持する。マイグレーションツールや新しいスキーマは導入しない。

テストは純粋な規則・UseCase・検索のunit、SQLite・TestClientのintegration、HTTP・DTO・OpenAPIのcontract、実プロセス間のe2eへ分類する。Fakeはsupportへ置く。フロントエンドの実画面は一時DBを使って確認し、自動のブラウザーE2E基盤を実装済みとは扱わない。

空のWorker・Entity・Repository・Policy・Messagingディレクトリは作らない。必要な責務がある場合に対応するディレクトリを追加する。
