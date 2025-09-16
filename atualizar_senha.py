# atualizar_senha.py

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
def get_database_url():
    """
    Pergunta ao utilizador qual banco de dados usar e retorna a URL de conexão.
    """
    while True:
        target = input("Onde deseja atualizar a senha? (1 - Local, 2 - Produção/Render): ").strip()
        if target == '1':
            print("\nA usar a base de dados local MariaDB/MySQL.")
            return "mysql+mysqlconnector://root:@localhost/catalogo_inteligente"
        elif target == '2':
            DATABASE_URL_ENV = os.getenv("DATABASE_URL")
            if not DATABASE_URL_ENV or not (DATABASE_URL_ENV.startswith("postgres://") or DATABASE_URL_ENV.startswith("postgresql://")):
                print("\nERRO: A variável 'DATABASE_URL' para o Render não foi encontrada no seu ficheiro .env.")
                print("Operação cancelada.")
                return None

            print("\nAVISO: Você está prestes a se conectar ao banco de dados de PRODUÇÃO no Render.")
            confirm = input("Tem a certeza absoluta que deseja continuar? (s/N): ").lower()
            if confirm != 's':
                print("Operação cancelada.")
                return None
            
            # Garante que a string de conexão use o driver psycopg2
            return DATABASE_URL_ENV.replace("postgres://", "postgresql+psycopg2://", 1).replace("postgresql://", "postgresql+psycopg2://", 1)
        else:
            print("Opção inválida. Por favor, digite '1' para Local ou '2' para Produção.")

def atualizar_senha_usuario():
    DATABASE_URL = get_database_url()
    if not DATABASE_URL: return
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()    
    print("\n--- Atualização de Senha de Utilizador ---")
    try:
        username = input("Digite o nome do utilizador que deseja atualizar: ").strip()
        nova_senha = getpass("Digite a nova senha: ")
        senha_hashed = gerar_hash_senha(nova_senha)
        query = text("UPDATE usuarios SET senha_hash = :senha_hash WHERE username = :username")
        resultado = db.execute(query, {"senha_hash": senha_hashed, "username": username})
        if resultado.rowcount == 0:
            print(f"\nErro: Utilizador '{username}' não encontrado.")
        else:
            db.commit()
            print(f"\nSenha do utilizador '{username}' atualizada com sucesso!")
    except Exception as e:
        db.rollback()
        print(f"\nOcorreu um erro: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    atualizar_senha_usuario()
