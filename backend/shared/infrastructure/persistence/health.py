"""業務データを読み出さないDB接続プローブ。"""

from sqlalchemy import Engine, text
from sqlalchemy.exc import SQLAlchemyError


def database_ready(engine: Engine) -> bool:
    try:
        with engine.connect() as connection:
            return connection.execute(text("SELECT 1")).scalar_one() == 1
    except SQLAlchemyError:
        return False
