.DEFAULT_GOAL := help

.PHONY: dev-go go-api-dev go-api-check go-api-test go-api-format backend-python-dev

.PHONY: help check test frontend-test format backend-check frontend-check setup frontend-install backend-install backend-dev backend-subject-list backend-test backend-lint backend-format-check backend-format backend-typecheck pre-commit-install pre-commit backend-seed dev frontend-dev frontend-lint frontend-format-check frontend-format frontend-typecheck build preview

help:
	@echo "go-api-format     Goコードを整形"
	@echo "backend-python-dev Python内部サービスだけを起動"
	@echo "dev-go            devと同じ構成で起動（互換コマンド）"
	@echo "go-api-dev        科目一覧のGo APIを起動"
	@echo "go-api-check      Goの整形状態・静的解析を検証"
	@echo "go-api-test       Goの入力検証・エラー変換・内部通信をテスト"
	@echo "check             バックエンドとフロントエンドのlint・整形状態・型を検証"
	@echo "test              バックエンドとフロントエンドの全テストを実行"
	@echo "frontend-test     フロントエンドのテストを実行"
	@echo "format            バックエンドとフロントエンドのlint自動修正・整形を実行"
	@echo "backend-check     バックエンドのlint・整形状態・型を検証"
	@echo "frontend-check    フロントエンドのlint・整形状態・型を検証"
	@echo "setup             フロントエンドとバックエンドの依存関係をインストール"
	@echo "frontend-install  npm ciを実行"
	@echo "backend-install   バックエンドの依存を同期"
	@echo "backend-dev       バックエンドの開発サーバーを起動"
	@echo "backend-subject-list   ローカル確認用の科目一覧APIを有効にして起動"
	@echo "backend-test      バックエンドのテストを実行"
	@echo "backend-lint      Ruffとgo vetでlintを検証"
	@echo "backend-format-check Ruffとgofmtで整形状態を検証"
	@echo "backend-format    Ruffのlint自動修正と整形を実行"
	@echo "backend-typecheck tyとgo buildでバックエンドの型を検証"
	@echo "pre-commit-install コミット時のフックを登録"
	@echo "pre-commit        全ファイルにpre-commitを実行"
	@echo "backend-seed      CS学部の便覧掲載科目データを追加投入"
	@echo "dev               フロントエンドと科目一覧APIを同時に起動"
	@echo "frontend-dev      フロントエンドの開発サーバーを起動"
	@echo "frontend-lint     ESLintでlintを検証"
	@echo "frontend-format-check Prettierで整形状態を検証"
	@echo "frontend-format   ESLintの自動修正とPrettierの整形を実行"
	@echo "frontend-typecheck TypeScriptでフロントエンドの型を検証"
	@echo "build             フロントエンドをビルド"
	@echo "preview           ビルド結果をプレビュー"

check:
	$(MAKE) backend-check
	$(MAKE) frontend-check

test:
	$(MAKE) backend-test
	$(MAKE) frontend-test

frontend-test:
	cd frontend && npm test

format:
	$(MAKE) backend-format
	$(MAKE) frontend-format

backend-check:
	$(MAKE) backend-lint
	$(MAKE) backend-format-check
	$(MAKE) backend-typecheck

frontend-check:
	$(MAKE) frontend-lint
	$(MAKE) frontend-format-check
	$(MAKE) frontend-typecheck

setup:
	$(MAKE) frontend-install
	$(MAKE) backend-install
	$(MAKE) pre-commit-install

frontend-install:
	cd frontend && npm ci

backend-install:
	uv sync --locked --project backend

backend-dev:
	node scripts/dev.mjs --backend-only

backend-subject-list:
	node scripts/dev.mjs --backend-only --subject-list-preview

backend-python-dev:
	cd backend && uv run --locked uvicorn api.api_service.main:app --app-dir . --reload --host 127.0.0.1 --port 8001

backend-test:
	cd backend && uv run --locked pytest
	$(MAKE) go-api-test

backend-lint:
	cd backend && uv run --locked ruff check .
	cd backend && go vet ./...

backend-format-check:
	cd backend && uv run --locked ruff format --check .
	node scripts/check-go-format.mjs

backend-format:
	cd backend && uv run --locked ruff check --fix .
	cd backend && uv run --locked ruff format .
	cd backend && go fmt ./...

backend-typecheck:
	cd backend && uv run --locked ty check
	cd backend && go build ./...

pre-commit-install:
	uv run --locked --project backend pre-commit install

pre-commit:
	uv run --locked --project backend pre-commit run --all-files

backend-seed:
	cd backend && uv run --locked python -m scripts.seed_subjects --file seeds/cs_2026.json

dev:
	node scripts/dev.mjs

dev-go:
	$(MAKE) dev

go-api-dev:
	cd backend && go run ./api -subject-list-preview

go-api-check:
	node scripts/check-go-format.mjs
	cd backend && go vet ./...

go-api-format:
	cd backend && go fmt ./...

go-api-test:
	cd backend && go test -race ./...

frontend-dev:
	cd frontend && npm run dev

frontend-lint:
	cd frontend && npm run lint

frontend-format-check:
	cd frontend && npm run format:check

frontend-format:
	cd frontend && npm run lint:fix
	cd frontend && npm run format

frontend-typecheck:
	cd frontend && npm run typecheck

build:
	cd frontend && npm run build

preview:
	cd frontend && npm run preview
