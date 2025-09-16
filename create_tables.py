# create_tables.py

import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Carrega as variáveis de ambiente de um ficheiro .env (se existir)
# para facilitar os testes locais.
load_dotenv() 

def create_tables():
    # Pega a URL do banco de dados da variável de ambiente.
    # Esta é a mesma lógica do main.py, mas focada no PostgreSQL.
    db_url = os.getenv("DATABASE_URL")

    if not db_url or not db_url.startswith("postgres://"):
        print("Erro: A variável de ambiente DATABASE_URL não está definida ou não é uma URL PostgreSQL.")
        print("Certifique-se de que a definiu antes de executar este script.")
        return

    # Converte a URL para o formato que o SQLAlchemy entende
    db_url = db_url.replace("postgres://", "postgresql://", 1)
    
    try:
        engine = create_engine(db_url)
        with engine.connect() as connection:
            print("Conexão com o banco de dados do Render estabelecida com sucesso!")
            
            # Usamos uma transação para garantir que todas as tabelas sejam criadas ou nenhuma.
            trans = connection.begin()
            try:
                # SQL para criar as tabelas (sintaxe para PostgreSQL)
                # SERIAL é o equivalente ao AUTO_INCREMENT
                # BOOLEAN é o equivalente ao TINYINT(1)
                
                connection.execute(text("""
                CREATE TABLE IF NOT EXISTS marcas (
                    id SERIAL PRIMARY KEY,
                    nome VARCHAR(100) NOT NULL UNIQUE
                );
                """))
                print("Tabela 'marcas' criada ou já existente.")

                connection.execute(text("""
                CREATE TABLE IF NOT EXISTS modelos_celular (
                    id SERIAL PRIMARY KEY,
                    id_marca INTEGER NOT NULL REFERENCES marcas(id) ON DELETE RESTRICT ON UPDATE CASCADE,
                    nome_modelo VARCHAR(150) NOT NULL
                );
                """))
                print("Tabela 'modelos_celular' criada ou já existente.")

                connection.execute(text("""
                CREATE TABLE IF NOT EXISTS produtos (
                    id SERIAL PRIMARY KEY,
                    id_modelo_celular INTEGER NOT NULL REFERENCES modelos_celular(id) ON DELETE RESTRICT ON UPDATE CASCADE,
                    nome VARCHAR(255) NOT NULL,
                    tipo VARCHAR(50) NOT NULL,
                    material VARCHAR(100),
                    preco_venda DECIMAL(10, 2) NOT NULL,
                    preco_custo DECIMAL(10, 2)
                );
                """))
                print("Tabela 'produtos' criada ou já existente.")

                connection.execute(text("""
                CREATE TABLE IF NOT EXISTS estoque_variacoes (
                    id SERIAL PRIMARY KEY,
                    id_produto INTEGER NOT NULL REFERENCES produtos(id) ON DELETE RESTRICT ON UPDATE CASCADE,
                    cor VARCHAR(50) NOT NULL DEFAULT 'N/A',
                    url_foto VARCHAR(255),
                    quantidade INTEGER NOT NULL DEFAULT 0,
                    disponivel_encomenda BOOLEAN NOT NULL DEFAULT TRUE,
                    UNIQUE(id_produto, cor)
                );
                """))
                print("Tabela 'estoque_variacoes' criada ou já existente.")

                connection.execute(text("""
                CREATE TABLE IF NOT EXISTS fornecedores (
                    id SERIAL PRIMARY KEY,
                    nome VARCHAR(150) NOT NULL,
                    contato_telefone VARCHAR(25),
                    contato_email VARCHAR(100)
                );
                """))
                print("Tabela 'fornecedores' criada ou já existente.")

                connection.execute(text("""
                CREATE TABLE IF NOT EXISTS produtos_fornecedores (
                    id_produto INTEGER NOT NULL REFERENCES produtos(id) ON DELETE RESTRICT ON UPDATE CASCADE,
                    id_fornecedor INTEGER NOT NULL REFERENCES fornecedores(id) ON DELETE RESTRICT ON UPDATE CASCADE,
                    PRIMARY KEY (id_produto, id_fornecedor)
                );
                """))
                print("Tabela 'produtos_fornecedores' criada ou já existente.")

                connection.execute(text("""
                CREATE TABLE IF NOT EXISTS usuarios (
                    id SERIAL PRIMARY KEY,
                    username VARCHAR(100) NOT NULL UNIQUE,
                    senha_hash VARCHAR(255) NOT NULL,
                    role VARCHAR(50) NOT NULL CHECK (role IN ('admin', 'atendente'))
                );
                """))
                print("Tabela 'usuarios' criada ou já existente.")


                trans.commit()
                print("\nTodas as tabelas foram criadas com sucesso no banco de dados do Render!")

            except Exception as e:
                print(f"Ocorreu um erro ao criar as tabelas: {e}")
                trans.rollback()

    except Exception as e:
        print(f"Falha ao conectar ao banco de dados: {e}")

if __name__ == "__main__":
    # Para instalar a biblioteca dotenv: pip install python-dotenv
    # Ela não é necessária para o deploy, apenas para facilitar a execução local.
    create_tables()
