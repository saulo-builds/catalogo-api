# criar_usuario.py

import os
from dotenv import load_dotenv

# Carrega as variáveis de ambiente PRIMEIRO
load_dotenv()

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from getpass import getpass

# Importa a nossa função de hashing
from seguranca import gerar_hash_senha

# --- Configuração do Banco de Dados ---
DATABASE_URL_ENV = os.getenv("DATABASE_URL")

if DATABASE_URL_ENV and DATABASE_URL_ENV.startswith("postgres://"):
    print("A conectar-se à base de dados PostgreSQL do Render...")
    # Ajusta a string de conexão para o SQLAlchemy com o driver psycopg2
    DATABASE_URL = DATABASE_URL_ENV.replace("postgres://", "postgresql+psycopg2://", 1)
else:
    print("A conectar-se à base de dados local MariaDB/MySQL...")
    DATABASE_URL = "mysql+mysqlconnector://root:@localhost/catalogo_inteligente"

try:
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    print("Conexão com o banco de dados estabelecida com sucesso!")
except Exception as e:
    print(f"Erro ao conectar ao banco de dados: {e}")
    exit()

def criar_usuario_admin():
    db = SessionLocal()
    print("\n--- Criação do Utilizador Admin ---")
    
    try:
        username = input("Digite o nome de utilizador desejado: ").strip()
        
        # Verifica se o utilizador já existe
        user_exists = db.execute(text("SELECT id FROM usuarios WHERE username = :username"), {"username": username}).first()
        if user_exists:
            print(f"\nErro: O nome de utilizador '{username}' já existe.")
            return

        while True:
            password = getpass("Digite a senha desejada: ")
            password_confirm = getpass("Confirme a senha: ")
            if password == password_confirm:
                break
            else:
                print("As senhas não correspondem. Tente novamente.")

        while True:
            role = input("Digite a função do utilizador (admin/atendente): ").strip().lower()
            if role in ['admin', 'atendente']:
                break
            else:
                print("Função inválida. Por favor, escolha 'admin' ou 'atendente'.")

        # Gera o hash da senha
        senha_hashed = gerar_hash_senha(password)

        # Insere o novo utilizador no banco de dados
        query = text("INSERT INTO usuarios (username, senha_hash, role) VALUES (:username, :senha_hash, :role)")
        db.execute(query, {"username": username, "senha_hash": senha_hashed, "role": role})
        db.commit()

        print(f"\nUtilizador '{username}' com a função '{role}' criado com sucesso!")

    except Exception as e:
        db.rollback()
        print(f"\nOcorreu um erro: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    criar_usuario_admin()

