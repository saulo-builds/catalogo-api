# catalogo_api/database.py
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Carrega variáveis de ambiente do ficheiro .env (para desenvolvimento local)
load_dotenv()

# Pega a URL do banco de dados da variável de ambiente (fornecida pelo Render em produção)
DATABASE_URL = os.getenv("DATABASE_URL")

# Lógica para alternar entre produção (PostgreSQL) e desenvolvimento (MySQL)
if DATABASE_URL and DATABASE_URL.startswith("postgres"):
    # Em produção (Render), a URL começa com "postgres://".
    # Substituímos para "postgresql://" para compatibilidade com SQLAlchemy.
    SQLALCHEMY_DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
else:
    # Em desenvolvimento local, usamos uma string de conexão fixa para MySQL/MariaDB.
    # Este será o fallback se DATABASE_URL não estiver definida ou não for de postgres.
    print("AVISO: DATABASE_URL do PostgreSQL não encontrada. A usar a base de dados local MySQL. Isto não deve acontecer em produção.")
    SQLALCHEMY_DATABASE_URL = "mysql+mysqlconnector://root:@localhost/catalogo_inteligente"

# Cria a engine do SQLAlchemy
# Para produção, o Render pode fechar conexões inativas. `pool_recycle` ajuda a evitar erros.
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_recycle=1800 # Recicla conexões a cada 30 minutos
)

# Cria a classe de sessão
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Função para obter a sessão do banco de dados (usada com Depends)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Função para obter a engine (usada para verificar o dialeto)
def get_engine():
    return engine
