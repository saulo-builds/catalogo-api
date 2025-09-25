# criar_usuario.py

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

def criar_novo_usuario():
    DATABASE_URL = get_database_url()
    if not DATABASE_URL: return
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()    
    print("\n--- Criação de Novo Utilizador ---")
    
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
    criar_novo_usuario()
