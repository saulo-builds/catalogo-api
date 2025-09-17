# database.py

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Carrega as variáveis de ambiente
load_dotenv()

_engine = None
_SessionLocal = None

def _initialize_database():
    """Função interna para inicializar o engine e a sessão apenas uma vez."""
    global _engine, _SessionLocal

    if _engine is None:
        DATABASE_URL_ENV = os.getenv("DATABASE_URL")
        APP_ENV = os.getenv("APP_ENV", "production")

        if APP_ENV == "development":
            # MODO DE DESENVOLVIMENTO: A usar a base de dados local MariaDB/MySQL.
            DATABASE_URL = "mysql+mysqlconnector://root:@localhost/catalogo_inteligente"
        elif DATABASE_URL_ENV and (DATABASE_URL_ENV.startswith("postgres://") or DATABASE_URL_ENV.startswith("postgresql://")):
            # MODO DE PRODUÇÃO: A usar a base de dados PostgreSQL do Render.
            DATABASE_URL = DATABASE_URL_ENV.replace("postgres://", "postgresql+psycopg2://", 1).replace("postgresql://", "postgresql+psycopg2://", 1)
        else:
            # FALLBACK: Nenhuma URL de produção encontrada. A usar a base de dados local.
            DATABASE_URL = "mysql+mysqlconnector://root:@localhost/catalogo_inteligente"

        _engine = create_engine(DATABASE_URL)
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)

def get_engine():
    """Retorna a instância do engine, inicializando-a se necessário."""
    _initialize_database()
    return _engine

# --- Dependência ---
def get_db():
    """Dependência do FastAPI para obter uma sessão do banco de dados."""
    _initialize_database()
    db = _SessionLocal()
    try:
        yield db
    finally:
        db.close()