from sqlalchemy import inspect, text
from sqlalchemy.orm import Mapped, mapped_column

from escalista.db import Base, init_db, make_engine


class Dummy(Base):
    __tablename__ = "dummy_c0"
    id: Mapped[int] = mapped_column(primary_key=True)


def test_init_db_creates_tables_and_select_works(tmp_path):
    engine = make_engine(f"sqlite:///{tmp_path}/sub/app.db")  # cria a pasta que faltar
    init_db(engine)
    with engine.connect() as conn:
        assert conn.execute(text("SELECT 1")).scalar() == 1
        assert conn.execute(text("PRAGMA foreign_keys")).scalar() == 1
    assert "dummy_c0" in inspect(engine).get_table_names()


def test_init_db_is_idempotent(tmp_path):
    engine = make_engine(f"sqlite:///{tmp_path}/app.db")
    init_db(engine)
    init_db(engine)
