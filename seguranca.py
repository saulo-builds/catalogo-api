# seguranca.py

import os
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta, timezone
from typing import Optional

# Imports para as novas funções de dependência
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from sqlalchemy import text
from database import get_db

# --- Configurações de Segurança ---
# Lê a chave secreta da variável de ambiente.
# Se não a encontrar, a aplicação irá falhar ao iniciar, o que é uma medida de segurança.
SECRET_KEY = os.getenv("SECRET_KEY")
if SECRET_KEY is None:
    raise ValueError("A variável de ambiente SECRET_KEY não foi definida.")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 480 # 8 horas

# --- Hashing de Senhas ---
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# --- OAuth2 Scheme ---
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

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

# --- Funções de Dependência de Utilizador ---

def get_user_from_db(db: Session, username: str):
    """Função auxiliar para obter o utilizador da BD."""
    query = text("SELECT username, role FROM usuarios WHERE username = :username")
    return db.execute(query, {"username": username}).first()

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """Dependência para obter o utilizador atual a partir do token."""
    username = verificar_token(token)
    if username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido ou expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = get_user_from_db(db, username)
    if user is None:
        raise HTTPException(status_code=401, detail="Utilizador não encontrado")
    return {"username": user[0], "role": user[1]}

async def get_current_admin_user(current_user: dict = Depends(get_current_user)):
    """Dependência para garantir que o utilizador é um administrador."""
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Acesso negado: Requer privilégios de administrador.")
    return current_user
