# criar_usuario.py

from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError
from getpass import getpass
from seguranca import gerar_hash_senha
import os
from dotenv import load_dotenv

# Carrega as variáveis de ambiente do ficheiro .env
load_dotenv()

# --- Configuração do Banco de Dados (Lógica Corrigida) ---
# Pega a URL do banco de dados da variável de ambiente (para o Render)
DATABASE_URL_ENV = os.getenv("DATABASE_URL")

if DATABASE_URL_ENV and DATABASE_URL_ENV.startswith("postgres://"):
    # Converte a URL do Render para o formato que o SQLAlchemy entende
    DATABASE_URL = DATABASE_URL_ENV.replace("postgres://", "postgresql://", 1)
    print("A conectar-se à base de dados PostgreSQL do Render...")
else:
    # Se não encontrar a variável de ambiente, usa a URL do banco de dados local
    DATABASE_URL = "mysql+mysqlconnector://root:@localhost/catalogo_inteligente"
    print("A conectar-se à base de dados local MariaDB/MySQL...")


def criar_usuario_admin():
    """
    Script para criar um utilizador administrativo na base de dados.
    """
    print("\n--- Criação do Utilizador Admin ---")
    
    try:
        engine = create_engine(DATABASE_URL)
        with engine.connect() as connection:
            
            username = input("Digite o nome de utilizador desejado: ").strip()
            password = getpass("Digite a senha desejada: ")
            password_confirm = getpass("Confirme a senha: ")

            if not username or not password:
                print("\nErro: Nome de utilizador e senha não podem estar vazios.")
                return

            if password != password_confirm:
                print("\nErro: As senhas não coincidem.")
                return

            senha_hashed = gerar_hash_senha(password)

            try:
                # A sintaxe de inserção é a mesma para ambos os bancos de dados
                query = text("INSERT INTO usuarios (username, senha_hash) VALUES (:username, :senha_hash)")
                
                trans = connection.begin()
                connection.execute(query, {"username": username, "senha_hash": senha_hashed})
                trans.commit()
                
                print(f"\nUtilizador '{username}' criado com sucesso!")

            except IntegrityError:
                print(f"\nErro: O nome de utilizador '{username}' já existe.")
            except Exception as e:
                print(f"\nOcorreu um erro ao inserir na base de dados: {e}")

    except Exception as e:
        print(f"Erro ao conectar à base de dados: {e}")


if __name__ == "__main__":
    criar_usuario_admin()
