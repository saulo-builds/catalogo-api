# catalogo_api/database.py
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Carrega variáveis de ambiente do ficheiro .env (para desenvolvimento local)
load_dotenv()

# Determina o ambiente da aplicação. 'development' é o padrão.
APP_ENV = os.getenv("APP_ENV", "development")

# Lógica para alternar entre produção (PostgreSQL) e desenvolvimento (MySQL)
if APP_ENV == "production":
    # Em produção, a DATABASE_URL DEVE estar definida.
    DATABASE_URL = os.getenv("DATABASE_URL")
    if not DATABASE_URL or not DATABASE_URL.startswith("postgres"):
        raise ValueError("ERRO: Em ambiente de produção, a variável DATABASE_URL do PostgreSQL é obrigatória.")

    # Substituímos para "postgresql://" para compatibilidade com SQLAlchemy.
    SQLALCHEMY_DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    
    # Garante que o SSL seja obrigatório para conexões PostgreSQL em produção,
    # injetando o parâmetro 'sslmode=require' diretamente na URL.
    if 'sslmode' not in SQLALCHEMY_DATABASE_URL:
        separator = '&' if '?' in SQLALCHEMY_DATABASE_URL else '?'
        SQLALCHEMY_DATABASE_URL += f"{separator}sslmode=require"
else:
    # Em desenvolvimento local, usamos uma string de conexão fixa para MySQL/MariaDB.
    # A variável DATABASE_URL do .env será ignorada para a conexão da aplicação principal.
    print("AVISO: A aplicação está a ser executada em modo de DESENVOLVIMENTO. A usar a base de dados local MySQL.")
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
