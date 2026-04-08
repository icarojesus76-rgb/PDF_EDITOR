"""
Configuração do banco de dados SQLAlchemy.

Define a engine, session e base para todos os modelos ORM.
Suporta SQLite inicialmente com arquitetura ready para migração
para outros bancos (PostgreSQL, MySQL) via ORM.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from sqlalchemy.pool import StaticPool

from app.core.config import get_settings

settings = get_settings()

# Configuração específica para SQLite
# StaticPool mantém conexão em memória (bom para tests)
# check_same_thread=False permite acesso multi-thread (FastAPI)
if "sqlite" in settings.DATABASE_URL:
    engine = create_engine(
        settings.DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=settings.DEBUG,
    )
else:
    engine = create_engine(
        settings.DATABASE_URL,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
    )

SessionLocal = sessionmaker(
    autocommit=False, autoflush=False, bind=engine, expire_on_commit=False
)

Base = declarative_base()


def get_db() -> Session:
    """
    Dependency do FastAPI para injeção de sessão.
    Garante que cada request tenha sua própria sessão
    e que a sessão seja fechada após o request.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """
    Inicializa o banco de dados criando todas as tabelas.
    Em produção, usar Alembic migrations em vez deste método.
    """
    Base.metadata.create_all(bind=engine)
