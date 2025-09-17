# main.py

from fastapi import FastAPI, Depends, HTTPException, status, File, UploadFile, Form
from sqlalchemy import text
from sqlalchemy.orm import Session
from typing import List, Optional
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
import os
from dotenv import load_dotenv
from pydantic import BaseModel # Manter para modelos específicos deste ficheiro

# Importa as bibliotecas do Cloudinary
import cloudinary
import cloudinary.uploader
import cloudinary.api

# Carrega as variáveis de ambiente PRIMEIRO
load_dotenv()

import seguranca
import schemas
from database import get_db, get_engine
from routers import marcas, modelos, produtos, fornecedores, estoque, pdv, relatorios

# --- Configuração do Cloudinary ---
cloudinary.config(
    cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key = os.getenv("CLOUDINARY_API_KEY"),
    api_secret = os.getenv("CLOUDINARY_API_SECRET"),
    secure = True
)

# --- Definição de Caminhos ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")

# Modelos Pydantic que são específicos para os endpoints públicos deste ficheiro
class VariacaoSelecionadaResponse(BaseModel):
    id: int
    cor: str
    quantidade: int
    disponivel_encomenda: bool
    url_foto: Optional[str] = None

class OutraVariacaoResponse(BaseModel):
    id: int
    cor: str
    url_foto: Optional[str] = None

class DetalhesProdutoPublicoResponse(BaseModel):
    produto_nome: str
    modelo_celular: str
    preco_venda: float
    variacao_selecionada: VariacaoSelecionadaResponse
    outras_variacoes: List[OutraVariacaoResponse]

# --- Início da Aplicação FastAPI ---
app = FastAPI()
app.include_router(marcas.router)
app.include_router(modelos.router)
app.include_router(produtos.router)
app.include_router(fornecedores.router)
app.include_router(estoque.router)
app.include_router(pdv.router)
app.include_router(relatorios.router)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# --- Endpoints Públicos ---
@app.get("/")
def ler_raiz():
    return RedirectResponse(url="/login")

@app.get("/login", include_in_schema=False)
def pagina_login():
    return FileResponse(os.path.join(BASE_DIR, 'login.html'))

@app.get("/catalogo", include_in_schema=False)
def ler_catalogo():
    return FileResponse(os.path.join(BASE_DIR, 'catalogo.html'))

@app.get("/produto", include_in_schema=False)
def ler_pagina_produto():
    return FileResponse(os.path.join(BASE_DIR, 'produto.html'))

@app.get("/modelos/search", response_model=List[str])
def search_modelos(q: Optional[str] = None, db: Session = Depends(get_db)):
    if not q:
        return []
    
    search_term = f"%{q}%"
    engine = get_engine()
    db_type = engine.dialect.name
    like_operator = "ILIKE" if db_type == "postgresql" else "LIKE"
    
    query_sql = f"""
        SELECT 
            CONCAT(b.nome, ' ', m.nome_modelo) AS full_name
        FROM modelos_celular AS m
        JOIN marcas AS b ON m.id_marca = b.id
        WHERE CONCAT(b.nome, ' ', m.nome_modelo) {like_operator} :search_term
        ORDER BY full_name
        LIMIT 10
    """
    
    try:
        resultado = db.execute(text(query_sql), {"search_term": search_term}).fetchall()
        modelos = [row[0] for row in resultado]
        return modelos
    except Exception as e:
        print(f"Erro na busca por autocompletar: {e}")
        return []

@app.get("/catalogo/search", response_model=List[schemas.EstoqueVariacaoResponse])
def procurar_no_catalogo(q: Optional[str] = None, db: Session = Depends(get_db)):
    # ... (código existente) ...
    if not q: return []
    search_term = f"%{q}%"
    engine = get_engine()
    db_type = engine.dialect.name
    like_operator = "ILIKE" if db_type == "postgresql" else "LIKE"
    query_sql = f"""
        SELECT ev.id, ev.cor, ev.quantidade, ev.url_foto, ev.disponivel_encomenda, p.nome as produto_nome,
               CONCAT(b.nome, ' ', m.nome_modelo) AS modelo_celular, p.preco_venda
        FROM estoque_variacoes AS ev
        JOIN produtos AS p ON ev.id_produto = p.id
        JOIN modelos_celular AS m ON p.id_modelo_celular = m.id
        JOIN marcas AS b ON m.id_marca = b.id
        WHERE CONCAT(b.nome, ' ', m.nome_modelo) {like_operator} :search_term
        ORDER BY ev.cor
    """
    try:
        resultado = db.execute(text(query_sql), {"search_term": search_term}).fetchall()
        variacoes = [schemas.EstoqueVariacaoResponse(id=row[0], cor=row[1], quantidade=row[2], url_foto=row[3], disponivel_encomenda=row[4], produto_nome=row[5], modelo_celular=row[6], preco_venda=row[7]) for row in resultado]
        return variacoes
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao buscar no catálogo: {e}")

# --- Endpoint de Detalhes do Produto (Público) ---
@app.get("/produto/detalhes/{variacao_id}", response_model=DetalhesProdutoPublicoResponse)
def get_detalhes_publicos_produto(variacao_id: int, db: Session = Depends(get_db)):
    # Query 1: Buscar a variação selecionada e os detalhes do produto principal
    query_principal = text("""
        SELECT
            p.id as produto_id,
            p.nome as produto_nome,
            p.preco_venda,
            CONCAT(b.nome, ' ', m.nome_modelo) AS modelo_celular,
            ev.cor,
            ev.quantidade,
            ev.disponivel_encomenda,
            ev.url_foto
        FROM estoque_variacoes AS ev
        JOIN produtos AS p ON ev.id_produto = p.id
        JOIN modelos_celular AS m ON p.id_modelo_celular = m.id
        JOIN marcas AS b ON m.id_marca = b.id
        WHERE ev.id = :variacao_id
    """)
    resultado_principal = db.execute(query_principal, {"variacao_id": variacao_id}).first()

    if not resultado_principal:
        raise HTTPException(status_code=404, detail="Produto não encontrado.")

    produto_id = resultado_principal[0]

    # Query 2: Buscar todas as variações para o mesmo produto
    query_outras_variacoes = text("""
        SELECT id, cor, url_foto
        FROM estoque_variacoes
        WHERE id_produto = :produto_id
        ORDER BY cor
    """)
    resultado_outras_variacoes = db.execute(query_outras_variacoes, {"produto_id": produto_id}).fetchall()

    # Montar a resposta
    variacao_selecionada = VariacaoSelecionadaResponse(
        id=variacao_id,
        cor=resultado_principal[4],
        quantidade=resultado_principal[5],
        disponivel_encomenda=resultado_principal[6],
        url_foto=resultado_principal[7]
    )

    outras_variacoes = [OutraVariacaoResponse(id=row[0], cor=row[1], url_foto=row[2]) for row in resultado_outras_variacoes]

    return DetalhesProdutoPublicoResponse(
        produto_nome=resultado_principal[1],
        modelo_celular=resultado_principal[3],
        preco_venda=resultado_principal[2],
        variacao_selecionada=variacao_selecionada,
        outras_variacoes=outras_variacoes
    )

# --- Endpoint de Autenticação ---
@app.post("/token", response_model=schemas.Token, tags=["Autenticação"])
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    query = text("SELECT username, senha_hash, role FROM usuarios WHERE username = :username")
    result = db.execute(query, {"username": form_data.username}).first()
    if not result or not seguranca.verificar_senha(form_data.password, result[1]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Nome de utilizador ou senha incorretos", headers={"WWW-Authenticate": "Bearer"})
    
    user_role = result[2]
    access_token = seguranca.criar_access_token(data={"sub": form_data.username, "role": user_role})
    return {"access_token": access_token, "token_type": "bearer"}

# --- Endpoints Protegidos ---

@app.get("/admin", include_in_schema=False)
def painel_admin():
    return FileResponse(os.path.join(BASE_DIR, 'index.html'))

# Endpoint do PDV CORRIGIDO - sem dependência de segurança direta
@app.get("/pdv", include_in_schema=False)
def painel_pdv():
    return FileResponse(os.path.join(BASE_DIR, 'pdv.html'))

@app.get("/relatorio-pdv", include_in_schema=False)
def pagina_relatorio_pdv():
    return FileResponse(os.path.join(BASE_DIR, 'relatorio_pdv.html'))
