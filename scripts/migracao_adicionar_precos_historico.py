# migracao_adicionar_precos_historico.py

import os
import sys
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Adiciona o diretório raiz do projeto ao sys.path
# Isso permite que o script encontre módulos como 'seguranca' e 'database' no futuro, se necessário.
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


# Carrega as variáveis de ambiente
load_dotenv()

def get_database_url():
    """
    Pergunta ao utilizador qual banco de dados usar e retorna a URL de conexão.
    """
    while True:
        target = input("Onde deseja executar a migração? (1 - Local, 2 - Produção/Render): ").strip()
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

def run_migration():
    db_url = get_database_url()
    if not db_url: return

    try:
        engine = create_engine(db_url)
        with engine.connect() as connection:
            print("Conexão com o banco de dados estabelecida com sucesso!")
            
            trans = connection.begin()
            try:
                # Verificar se as colunas já existem para evitar erros ao re-executar
                db_type = engine.dialect.name
                schema_query = "table_schema=DATABASE()" if db_type == 'mysql' else "table_schema='public'"
                check_column_query = text(f"SELECT column_name FROM information_schema.columns WHERE {schema_query} AND table_name='historico_estoque' AND column_name IN ('preco_venda_momento', 'preco_custo_momento')")
                
                existing_columns = {row[0] for row in connection.execute(check_column_query).fetchall()}
                
                if 'preco_venda_momento' in existing_columns and 'preco_custo_momento' in existing_columns:
                    print("As colunas 'preco_venda_momento' e 'preco_custo_momento' já existem. Nenhuma alteração necessária.")
                    trans.rollback()
                    return

                if 'preco_venda_momento' not in existing_columns:
                    print("A adicionar a coluna 'preco_venda_momento'...")
                    connection.execute(text("ALTER TABLE historico_estoque ADD COLUMN preco_venda_momento DECIMAL(10, 2);"))
                
                if 'preco_custo_momento' not in existing_columns:
                    print("A adicionar a coluna 'preco_custo_momento'...")
                    connection.execute(text("ALTER TABLE historico_estoque ADD COLUMN preco_custo_momento DECIMAL(10, 2);"))

                trans.commit()
                print("\nMigração concluída com sucesso! As colunas de preço foram adicionadas à tabela 'historico_estoque'.")
            except Exception as e:
                print(f"Ocorreu um erro durante a migração: {e}")
                trans.rollback()
    except Exception as e:
        print(f"Falha ao conectar ao banco de dados: {e}")

if __name__ == "__main__":
    run_migration()