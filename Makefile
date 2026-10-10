.DEFAULT_GOAL := help

.PHONY: help setup frontend-install backend-install backend-dev backend-test dev build preview

help:
	@echo "setup             フロントエンドとバックエンドの依存関係をインストール"
	@echo "frontend-install  npm ciを実行"
	@echo "backend-install   uv sync --lockedを実行"
	@echo "backend-dev       バックエンドの開発サーバーを起動"
	@echo "backend-test      バックエンドのテストを実行"
	@echo "dev               フロントエンドの開発サーバーを起動"
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

backend-test:
	cd backend && uv run pytest

dev:
	cd frontend && npm run dev

build:
	cd frontend && npm run build

preview:
	cd frontend && npm run preview
