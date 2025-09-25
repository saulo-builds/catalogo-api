# scripts/migracao_mover_preco_custo.py

import sys
from sqlalchemy import create_engine, text

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
                db_type = engine.dialect.name
                
                # 1. Adicionar a coluna 'preco_custo' em 'estoque_variacoes' se não existir
                check_column_query = text("SELECT 1 FROM information_schema.columns WHERE table_name='estoque_variacoes' AND column_name='preco_custo'")
                if not connection.execute(check_column_query).scalar():
                    print("A adicionar a coluna 'preco_custo' à tabela 'estoque_variacoes'...")
                    connection.execute(text("ALTER TABLE estoque_variacoes ADD COLUMN preco_custo DECIMAL(10, 2);"))
                else:
                    print("A coluna 'preco_custo' já existe em 'estoque_variacoes'.")

                # 2. Verificar se a coluna 'preco_custo' ainda existe em 'produtos'
                check_prod_column_query = text("SELECT 1 FROM information_schema.columns WHERE table_name='produtos' AND column_name='preco_custo'")
                if connection.execute(check_prod_column_query).scalar():
                    print("A migrar dados de 'produtos.preco_custo' para 'estoque_variacoes.preco_custo'...")
                    # Esta query atualiza o custo nas variações com base no custo do seu produto pai.
                    # É uma operação de 'melhor esforço' para migrar os dados existentes.
                    update_query = text("""
                        UPDATE estoque_variacoes ev
                        SET preco_custo = p.preco_custo
                        FROM produtos p
                        WHERE ev.id_produto = p.id AND ev.preco_custo IS NULL;
                    """)
                    # Sintaxe diferente para MySQL
                    if db_type == 'mysql':
                         update_query = text("""
                            UPDATE estoque_variacoes ev JOIN produtos p ON ev.id_produto = p.id
                            SET ev.preco_custo = p.preco_custo
                            WHERE ev.preco_custo IS NULL;
                         """)
                    connection.execute(update_query)
                    
                    print("A remover a coluna 'preco_custo' da tabela 'produtos'...")
                    connection.execute(text("ALTER TABLE produtos DROP COLUMN preco_custo;"))
                else:
                    print("A coluna 'preco_custo' já não existe em 'produtos'.")

                trans.commit()
                print("\nMigração concluída com sucesso!")
            except Exception as e:
                print(f"Ocorreu um erro durante a migração: {e}")
                trans.rollback()
    except Exception as e:
        print(f"Falha ao conectar ao banco de dados: {e}")

if __name__ == "__main__":
    run_migration()