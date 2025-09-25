# migracao_adicionar_role.py

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
                db_type = engine.dialect.name

                # 1. Verificar se a coluna já existe para evitar erros ao re-executar
                schema_filter = "table_schema = DATABASE()" if db_type == 'mysql' else "table_schema = 'public'"
                check_column_query = text(f"SELECT 1 FROM information_schema.columns WHERE {schema_filter} AND table_name='usuarios' AND column_name='role'")
                column_exists = connection.execute(check_column_query).scalar()

                if column_exists:
                    print("A coluna 'role' já existe na tabela 'usuarios'. Nenhuma ação necessária.")
                    trans.rollback() # Apenas desfaz a transação, sem erro.
                    return

                # 2. Adicionar a coluna 'role'
                print("A adicionar a coluna 'role' à tabela 'usuarios'...")
                connection.execute(text("ALTER TABLE usuarios ADD COLUMN role VARCHAR(50);"))
                
                # 3. Preencher a coluna 'role' para utilizadores existentes (assumindo que são admins)
                print("A definir a função 'admin' para os utilizadores existentes...")
                connection.execute(text("UPDATE usuarios SET role = 'admin' WHERE role IS NULL;"))
                
                # 4. Adicionar a restrição NOT NULL e a restrição CHECK
                print("A adicionar as restrições NOT NULL e CHECK à coluna 'role'...")
                if db_type == 'postgresql':
                    connection.execute(text("ALTER TABLE usuarios ALTER COLUMN role SET NOT NULL;"))
                else: # Sintaxe para MySQL
                    connection.execute(text("ALTER TABLE usuarios MODIFY COLUMN role VARCHAR(50) NOT NULL;"))
                connection.execute(text("ALTER TABLE usuarios ADD CONSTRAINT check_role CHECK (role IN ('admin', 'atendente'));"))

                trans.commit()
                print("\nMigração concluída com sucesso! A coluna 'role' foi adicionada e configurada.")

            except Exception as e:
                print(f"Ocorreu um erro durante a migração: {e}")
                trans.rollback()

    except Exception as e:
        print(f"Falha ao conectar ao banco de dados: {e}")

if __name__ == "__main__":
    run_migration()