# create_tables.py

import os
import sys
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Adiciona o diretório raiz do projeto ao sys.path
# Isso permite que o script encontre módulos como 'seguranca' e 'database' no futuro, se necessário.
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


# Carrega as variáveis de ambiente de um ficheiro .env (se existir)
# para facilitar os testes locais.
load_dotenv() 

def get_database_url():
    """
    Pergunta ao utilizador qual banco de dados usar e retorna a URL de conexão.
    """
    while True:
        target = input("Onde deseja criar/atualizar as tabelas? (1 - Local, 2 - Produção/Render): ").strip()
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
            
            # Garante que a string de conexão use o driver psycopg2 e sslmode=require
            final_url = DATABASE_URL_ENV.replace("postgres://", "postgresql+psycopg2://", 1)
            if "?" not in final_url:
                final_url += "?sslmode=require"
            elif "sslmode=" not in final_url:
                final_url += "&sslmode=require"
            return final_url
        else:
            print("Opção inválida. Por favor, digite '1' para Local ou '2' para Produção.")

def create_tables():
    DATABASE_URL = get_database_url()
    if not DATABASE_URL: return
    
    try:
        engine = create_engine(DATABASE_URL)
        with engine.connect() as connection:
            print("Conexão com o banco de dados estabelecida com sucesso!")
            
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
                    preco_venda DECIMAL(10, 2) NOT NULL
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
                    preco_custo DECIMAL(10, 2),
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

                connection.execute(text("""
                CREATE TABLE IF NOT EXISTS historico_estoque (
                    id SERIAL PRIMARY KEY,
                    id_variacao_estoque INTEGER NOT NULL REFERENCES estoque_variacoes(id) ON DELETE CASCADE,
                    id_usuario INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE RESTRICT,
                    tipo_movimento VARCHAR(20) NOT NULL CHECK (tipo_movimento IN ('incremento', 'decremento')),
                    quantidade_alterada INTEGER NOT NULL DEFAULT 1,
                    preco_venda_momento DECIMAL(10, 2),
                    preco_custo_momento DECIMAL(10, 2),
                    data_hora TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    nova_quantidade_estoque INTEGER NOT NULL
                );
                """))
                print("Tabela 'historico_estoque' criada ou já existente.")

                trans.commit()
                print("\nTodas as tabelas foram criadas/verificadas com sucesso!")

            except Exception as e:
                print(f"Ocorreu um erro ao criar as tabelas: {e}")
                trans.rollback()

    except Exception as e:
        print(f"Falha ao conectar ao banco de dados: {e}")

if __name__ == "__main__":
    create_tables()
