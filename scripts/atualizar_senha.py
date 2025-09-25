# atualizar_senha.py

import os
import sys
from getpass import getpass

# Adiciona o diretório raiz do projeto ao sys.path
# Isso permite que o script encontre módulos como 'seguranca' e 'database'
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dotenv import load_dotenv

# Carrega as variáveis de ambiente PRIMEIRO
load_dotenv()

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Importa a nossa função de hashing
from seguranca import gerar_hash_senha
from scripts.utils import get_database_url

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
