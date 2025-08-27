# criar_usuario.py

from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError
from getpass import getpass # Para esconder a senha ao digitar
from seguranca import gerar_hash_senha

# --- Configuração do Banco de Dados (igual ao main.py) ---
DATABASE_URL = "mysql+mysqlconnector://root:@localhost/catalogo_inteligente"

def criar_primeiro_usuario():
    """
    Script para criar um utilizador administrativo na base de dados.
    """
    print("--- Criação do Utilizador Admin ---")
    
    try:
        engine = create_engine(DATABASE_URL)
        with engine.connect() as connection:
            
            # Pede os dados ao utilizador
            username = input("Digite o nome de utilizador desejado: ").strip()
            password = getpass("Digite a senha desejada: ")
            password_confirm = getpass("Confirme a senha: ")

            # Validações simples
            if not username or not password:
                print("\nErro: Nome de utilizador e senha não podem estar vazios.")
                return

            if password != password_confirm:
                print("\nErro: As senhas não coincidem.")
                return

            # Gera o hash da senha
            senha_hashed = gerar_hash_senha(password)

            # Insere o novo utilizador na base de dados
            try:
                query = text("INSERT INTO usuarios (username, senha_hash) VALUES (:username, :senha_hash)")
                
                # Usamos uma transação para garantir a integridade
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
    criar_primeiro_usuario()
