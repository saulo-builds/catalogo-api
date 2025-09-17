# migracao_adicionar_role.py

import os
import sys
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Adiciona o diretório raiz do projeto ao sys.path
# Isso permite que o script encontre módulos como 'seguranca' e 'database' no futuro, se necessário.
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


# Carrega as variáveis de ambiente
load_dotenv()

def run_migration():
    db_url = os.getenv("DATABASE_URL")

    if not db_url or not (db_url.startswith("postgres://") or db_url.startswith("postgresql://")):
        print("Erro: A variável de ambiente DATABASE_URL não está definida ou não é uma URL PostgreSQL válida.")
        print("Certifique-se de que a definiu no ficheiro .env antes de executar este script.")
        return

    # Ajusta a URL para o formato do SQLAlchemy
    if db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+psycopg2://", 1)
    else:
        db_url = db_url.replace("postgres://", "postgresql+psycopg2://", 1)

    try:
        engine = create_engine(db_url)
        with engine.connect() as connection:
            print("Conexão com o banco de dados do Render estabelecida com sucesso!")
            
            trans = connection.begin()
            try:
                # 1. Verificar se a coluna já existe para evitar erros ao re-executar
                check_column_query = text("SELECT 1 FROM information_schema.columns WHERE table_name='usuarios' AND column_name='role'")
                column_exists = connection.execute(check_column_query).scalar()

                if column_exists:
                    print("A coluna 'role' já existe na tabela 'usuarios'. Nenhuma ação necessária.")
                    trans.rollback()
                    return

                # 2. Adicionar a coluna 'role'
                print("A adicionar a coluna 'role' à tabela 'usuarios'...")
                connection.execute(text("ALTER TABLE usuarios ADD COLUMN role VARCHAR(50);"))
                
                # 3. Preencher a coluna 'role' para utilizadores existentes (assumindo que são admins)
                print("A definir a função 'admin' para os utilizadores existentes...")
                connection.execute(text("UPDATE usuarios SET role = 'admin' WHERE role IS NULL;"))
                
                # 4. Adicionar a restrição NOT NULL e a restrição CHECK
                print("A adicionar as restrições NOT NULL e CHECK à coluna 'role'...")
                connection.execute(text("ALTER TABLE usuarios ALTER COLUMN role SET NOT NULL;"))
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