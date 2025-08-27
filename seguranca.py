# seguranca.py

import os
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta, timezone
from typing import Optional

# --- Configurações de Segurança ---
# Lê a chave secreta da variável de ambiente.
# Se não a encontrar, a aplicação irá falhar ao iniciar, o que é uma medida de segurança.
SECRET_KEY = os.getenv("SECRET_KEY")
if SECRET_KEY is None:
    raise ValueError("A variável de ambiente SECRET_KEY não foi definida.")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30 # O token será válido por 30 minutos

# --- Hashing de Senhas ---
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verificar_senha(senha_plana: str, senha_hash: str) -> bool:
    """
    Verifica se uma senha em texto plano corresponde a um hash guardado.
    """
    return pwd_context.verify(senha_plana, senha_hash)

def gerar_hash_senha(senha: str) -> str:
    """
    Gera o hash de uma senha em texto plano.
    """
    return pwd_context.hash(senha)

# --- Funções de Token JWT ---

def criar_access_token(data: dict) -> str:
    """
    Cria um novo token de acesso (JWT).
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verificar_token(token: str) -> Optional[str]:
    """
    Verifica um token e devolve o nome de utilizador (subject) se for válido.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            return None
        return username
    except JWTError:
        return None
