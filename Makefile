.DEFAULT_GOAL := help

.PHONY: help check format backend-check frontend-check setup frontend-install backend-install backend-dev backend-catalog backend-test backend-lint backend-format backend-typecheck pre-commit-install pre-commit backend-seed dev frontend-dev frontend-lint frontend-format frontend-typecheck build preview

help:
	@echo "check             バックエンドとフロントエンドのlint・整形状態・型を検証"
	@echo "format            バックエンドとフロントエンドのlint自動修正・整形を実行"
	@echo "backend-check     バックエンドのlint・整形状態・型を検証"
	@echo "frontend-check    フロントエンドのlint・整形状態・型を検証"
	@echo "setup             フロントエンドとバックエンドの依存関係をインストール"
	@echo "frontend-install  npm ciを実行"
	@echo "backend-install   uv sync --lockedを実行"
	@echo "backend-dev       バックエンドの開発サーバーを起動"
	@echo "backend-catalog   ローカル確認用の科目一覧APIを有効にして起動"
	@echo "backend-test      バックエンドのテストを実行"
	@echo "backend-lint      Ruffのlintと整形状態を検証"
	@echo "backend-format    Ruffのlint自動修正と整形を実行"
	@echo "backend-typecheck tyでバックエンドの型を検証"
	@echo "pre-commit-install コミット時のフックを登録"
	@echo "pre-commit        全ファイルにpre-commitを実行"
	@echo "backend-seed      CS学部の便覧掲載科目データを追加投入"
	@echo "dev               フロントエンドと科目一覧APIを同時に起動"
	@echo "frontend-dev      フロントエンドの開発サーバーを起動"
	@echo "frontend-lint     ESLintとPrettierで検証"
	@echo "frontend-format   ESLintの自動修正とPrettierの整形を実行"
	@echo "frontend-typecheck TypeScriptでフロントエンドの型を検証"
	@echo "build             フロントエンドをビルド"
	@echo "preview           ビルド結果をプレビュー"

check:
	$(MAKE) backend-check
	$(MAKE) frontend-check

format:
	$(MAKE) backend-format
	$(MAKE) frontend-format

backend-check:
	$(MAKE) backend-lint
	$(MAKE) backend-typecheck

frontend-check:
	$(MAKE) frontend-lint
	$(MAKE) frontend-typecheck

setup:
	$(MAKE) frontend-install
	$(MAKE) backend-install
	$(MAKE) pre-commit-install

frontend-install:
	cd frontend && npm ci

backend-install:
	cd backend && uv sync --locked

backend-dev:
	cd backend && uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

backend-catalog:
	cd backend && ENABLE_CATALOG_PREVIEW=true uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

backend-test:
	cd backend && uv run pytest

backend-lint:
	cd backend && uv run --locked ruff check .
	cd backend && uv run --locked ruff format --check .

backend-format:
	cd backend && uv run --locked ruff check --fix .
	cd backend && uv run --locked ruff format .

backend-typecheck:
	cd backend && uv run --locked ty check

pre-commit-install:
	uv run --locked --project backend pre-commit install

pre-commit:
	uv run --locked --project backend pre-commit run --all-files

backend-seed:
	cd backend && uv run python -m app.seed --file seeds/cs_2026.json

dev:
	node scripts/dev.mjs

frontend-dev:
	cd frontend && npm run dev

frontend-lint:
	cd frontend && npm run lint
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
