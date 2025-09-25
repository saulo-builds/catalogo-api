# migracao_adicionar_precos_historico.py

import sys
from sqlalchemy import create_engine, text

# Adiciona o diretório raiz do projeto ao sys.path
# Isso permite que o script encontre módulos como 'seguranca' e 'database' no futuro, se necessário.
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from scripts.utils import get_database_url

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