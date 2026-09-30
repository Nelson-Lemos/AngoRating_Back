from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from app.core.config import settings


connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False

# O host do Neon termina em `-pooler`: é um PgBouncer à frente do Postgres, que
# recicla ligações ociosas do servidor. Sem `pool_pre_ping` o SQLAlchemy
# empresta uma ligação morta e a primeira query leva "server closed the
# connection unexpectedly" — um erro que só aparece em produção, depois de
# alguns minutos sem tráfego. `pre_ping` valida a ligação antes de a usar.
engine_options = {
    "echo": False,
    "connect_args": connect_args,
    "pool_pre_ping": True,
}

if settings.DATABASE_URL.startswith("sqlite"):
    # O ficheiro SQLite é local; um pool não dá ganho nenhum aqui.
    engine_options.pop("pool_pre_ping")
else:
    # O plano free do Neon corta ligações ociosas muito depressa; o pool padrão
    # (5 + 10 de overflow) desperdiça metade das ligações cedidas pelo plano.
    engine_options.update(pool_size=5, max_overflow=5, pool_recycle=300)

engine = create_engine(settings.DATABASE_URL, **engine_options)

if settings.DATABASE_URL.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Uma única definição de `Base` em todo o projecto. Os modelos herdam de
# `app.models.base.Base`; reexportamos aqui porque quase todo o código faz
# `from app.core.database import Base, get_db`. Duas `DeclarativeBase` em
# paralelo significam `create_all()` a não criar nada e `relationship()` a
# explodir — daí a insistência neste reexport.
from app.models.base import Base  # noqa: E402  (tem de vir depois do engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
