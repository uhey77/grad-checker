.DEFAULT_GOAL := help

.PHONY: help setup frontend-install backend-install backend-dev backend-catalog backend-test backend-seed dev frontend-dev build preview

help:
	@echo "setup             フロントエンドとバックエンドの依存関係をインストール"
	@echo "frontend-install  npm ciを実行"
	@echo "backend-install   uv sync --lockedを実行"
	@echo "backend-dev       バックエンドの開発サーバーを起動"
	@echo "backend-catalog   ローカル確認用の科目一覧APIを有効にして起動"
	@echo "backend-test      バックエンドのテストを実行"
	@echo "backend-seed      CS学部の便覧掲載科目データを追加投入"
	@echo "dev               フロントエンドと科目一覧APIを同時に起動"
	@echo "frontend-dev      フロントエンドの開発サーバーを起動"
	@echo "build             フロントエンドをビルド"
	@echo "preview           ビルド結果をプレビュー"

setup:
	$(MAKE) frontend-install
	$(MAKE) backend-install

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

backend-seed:
	cd backend && uv run python -m app.seed --file seeds/cs_2026.json

dev:
	node scripts/dev.mjs

frontend-dev:
	cd frontend && npm run dev

build:
	cd frontend && npm run build

preview:
	cd frontend && npm run preview
