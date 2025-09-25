# scripts/utils.py

import os
from dotenv import load_dotenv

# Carrega as variáveis de ambiente do ficheiro .env
load_dotenv()

def get_database_url():
    """
    Pergunta ao utilizador qual banco de dados usar e retorna a URL de conexão apropriada.
    Esta função é partilhada por todos os scripts de manutenção.
    """
    while True:
        target = input("Onde deseja executar esta operação? (1 - Local, 2 - Produção/Render): ").strip()
        if target == '1':
            print("\nA usar a base de dados local MariaDB/MySQL.")
            return "mysql+mysqlconnector://root:@localhost/catalogo_inteligente"
        elif target == '2':
            DATABASE_URL_ENV = os.getenv("DATABASE_URL")
            if not DATABASE_URL_ENV or not (DATABASE_URL_ENV.startswith("postgres://") or DATABASE_URL_ENV.startswith("postgresql://")):
                print("\nERRO: A variável 'DATABASE_URL' para o Render não foi encontrada no seu ficheiro .env.")
                return None

            print("\nAVISO: Você está prestes a se conectar ao banco de dados de PRODUÇÃO no Render.")
            if input("Tem a certeza absoluta que deseja continuar? (s/N): ").lower() != 's':
                print("Operação cancelada.")
                return None
            
            final_url = DATABASE_URL_ENV.replace("postgres://", "postgresql+psycopg2://", 1)
            return final_url + ("?sslmode=require" if "?sslmode=require" not in final_url else "")
        else:
            print("Opção inválida. Por favor, digite '1' para Local ou '2' para Produção.")