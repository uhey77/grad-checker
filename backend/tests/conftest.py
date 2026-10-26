"""PostgreSQL検証は明示したローカルDBの、テストごとの専用スキーマで行う。"""

import os
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.engine import make_url

from migrations.schema import initialize_schema
from shared.infrastructure.persistence.database import create_database_engine


@pytest.fixture
def postgres_empty_engine():
    value = os.environ.get("TEST_POSTGRES_URL")
    if not value:
        pytest.skip("TEST_POSTGRES_URLが未設定です（ローカルPostgreSQL専用）。")
    url = make_url(value)
    if url.host not in {"localhost", "127.0.0.1", "::1"}:
        pytest.fail("PostgreSQLテストの接続先はローカルホストに限定します。")
    schema = "test_" + uuid4().hex
    admin = create_database_engine(value)
    with admin.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine = create_database_engine(
        url.update_query_dict({"options": f"-csearch_path={schema}"}).render_as_string(
            hide_password=False
        )
    )
    try:
        yield engine
    finally:
        engine.dispose()
        with admin.begin() as connection:
            # このfixtureが作成したローカルの専用スキーマだけを削除する。
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin.dispose()


@pytest.fixture
def postgres_engine(postgres_empty_engine, tmp_path):
    initialize_schema(postgres_empty_engine, apply=True)
    return postgres_empty_engine
