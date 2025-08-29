# main.py

import shutil
from fastapi import FastAPI, Depends, HTTPException, status, File, UploadFile, Form
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import OperationalError, IntegrityError
from pydantic import BaseModel, field_validator
import re
from typing import List, Optional
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
import os
from dotenv import load_dotenv

# Importa as bibliotecas do Cloudinary
import cloudinary
import cloudinary.uploader
import cloudinary.api

load_dotenv()
import seguranca

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

# --- Modelos Pydantic ---
class MarcaBase(BaseModel):
    nome: str
    @field_validator('nome')
    def trim_whitespace(cls, v): return v.strip()

class MarcaResponse(BaseModel):
    id: int
    nome: str

class ModeloBase(BaseModel):
    nome_modelo: str
    id_marca: int
    @field_validator('nome_modelo')
    def trim_whitespace(cls, v): return v.strip()

class ModeloResponse(BaseModel):
    id: int
    nome_modelo: str
    marca_nome: str

class ProdutoBase(BaseModel):
    nome: str
    tipo: str
    material: Optional[str] = None
    preco_venda: float
    preco_custo: Optional[float] = None
    id_modelo_celular: int
    @field_validator('nome', 'tipo', 'material')
    def trim_whitespace(cls, v):
        if v is not None: return v.strip()
        return v

class ProdutoResponse(BaseModel):
    id: int
    nome: str
    tipo: str
    material: Optional[str] = None
    preco_venda: float
    modelo_celular: str

class ProdutoAdminResponse(ProdutoBase):
    id: int

class EstoqueVariacaoBase(BaseModel):
    id_produto: int
    cor: str
    quantidade: int
    disponivel_encomenda: bool = True
    @field_validator('cor')
    def trim_whitespace(cls, v): return v.strip()

class EstoqueVariacaoResponse(BaseModel):
    id: int
    cor: str
    quantidade: int
    disponivel_encomenda: bool
    url_foto: Optional[str] = None
    produto_nome: str
    modelo_celular: str
    preco_venda: float

class FornecedorBase(BaseModel):
    nome: str
    contato_telefone: Optional[str] = None
    contato_email: Optional[str] = None
    @field_validator('nome', 'contato_telefone', 'contato_email')
    def trim_whitespace(cls, v):
        if v is not None: return v.strip()
        return v
    @field_validator('contato_telefone')
    def validar_telefone(cls, v):
        if v is None or v == '': return v
        regex = re.compile(r'^\(?\d{2}\)?[\s-]?\d{4,5}-?\d{4}$')
        if not regex.match(v): raise ValueError('Número de telefone inválido.')
        return v

class Token(BaseModel):
    access_token: str
    token_type: str

# Modelos ATUALIZADOS para a Página de Detalhes do Produto
class VariacaoSimples(BaseModel):
    id: int
    cor: str
    quantidade: int
    disponivel_encomenda: bool
    url_foto: Optional[str] = None

class DetalhesProdutoResponse(BaseModel):
    produto_nome: str
    modelo_celular: str
    preco_venda: float
    variacao_selecionada: VariacaoSimples
    outras_variacoes: List[VariacaoSimples]


# --- Configuração do Banco de Dados ---
DATABASE_URL_ENV = os.getenv("DATABASE_URL")

if DATABASE_URL_ENV and DATABASE_URL_ENV.startswith("postgres://"):
    print("A usar a base de dados PostgreSQL do Render.")
    DATABASE_URL = DATABASE_URL_ENV.replace("postgres://", "postgresql+psycopg2://", 1)
else:
    print("A usar a base de dados local MariaDB/MySQL.")
    DATABASE_URL = "mysql+mysqlconnector://root:@localhost/catalogo_inteligente"

try:
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    with engine.connect() as connection:
        print("Conexão com o banco de dados estabelecida com sucesso!")
except Exception as e:
    print(f"Erro ao conectar ao banco de dados: {e}")
    exit()

# --- Dependências ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

async def get_current_user(token: str = Depends(oauth2_scheme)):
    username = seguranca.verificar_token(token)
    if username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido ou expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return {"username": username}

# --- Início da Aplicação FastAPI ---
app = FastAPI()
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# --- Endpoints Públicos ---
@app.get("/")
def ler_raiz():
    return RedirectResponse(url="/catalogo")

@app.get("/login", include_in_schema=False)
def pagina_login():
    return FileResponse(os.path.join(BASE_DIR, 'login.html'))

@app.get("/admin", include_in_schema=False)
def painel_admin():
    return FileResponse(os.path.join(BASE_DIR, 'index.html'))

@app.get("/catalogo", include_in_schema=False)
def ler_catalogo():
    return FileResponse(os.path.join(BASE_DIR, 'catalogo.html'))

@app.get("/produto", include_in_schema=False)
def ler_pagina_produto():
    return FileResponse(os.path.join(BASE_DIR, 'produto.html'))

# Endpoint ATUALIZADO para a Página de Detalhes do Produto
@app.get("/produto/detalhes/{variacao_id}", response_model=DetalhesProdutoResponse)
def get_detalhes_produto(variacao_id: int, db: Session = Depends(get_db)):
    query_selecionada = text("""
        SELECT ev.id, ev.cor, ev.quantidade, ev.url_foto, ev.disponivel_encomenda,
               p.id as produto_id, p.nome as produto_nome, p.preco_venda,
               CONCAT(b.nome, ' ', m.nome_modelo) AS modelo_celular
        FROM estoque_variacoes AS ev
        JOIN produtos AS p ON ev.id_produto = p.id
        JOIN modelos_celular AS m ON p.id_modelo_celular = m.id
        JOIN marcas AS b ON m.id_marca = b.id
        WHERE ev.id = :variacao_id
    """)
    variacao_selecionada_db = db.execute(query_selecionada, {"variacao_id": variacao_id}).first()

    if not variacao_selecionada_db:
        raise HTTPException(status_code=404, detail="Variação de produto não encontrada.")

    produto_id = variacao_selecionada_db[5]

    query_outras = text("""
        SELECT id, cor, quantidade, url_foto, disponivel_encomenda
        FROM estoque_variacoes
        WHERE id_produto = :produto_id
        ORDER BY cor
    """)
    outras_variacoes_db = db.execute(query_outras, {"produto_id": produto_id}).fetchall()

    variacao_selecionada = VariacaoSimples(
        id=variacao_selecionada_db[0], cor=variacao_selecionada_db[1], quantidade=variacao_selecionada_db[2],
        url_foto=variacao_selecionada_db[3], disponivel_encomenda=bool(variacao_selecionada_db[4])
    )

    outras_variacoes = [
        VariacaoSimples(id=row[0], cor=row[1], quantidade=row[2], url_foto=row[3], disponivel_encomenda=bool(row[4]))
        for row in outras_variacoes_db
    ]
    
    return DetalhesProdutoResponse(
        produto_nome=variacao_selecionada_db[6],
        modelo_celular=variacao_selecionada_db[8],
        preco_venda=variacao_selecionada_db[7],
        variacao_selecionada=variacao_selecionada,
        outras_variacoes=outras_variacoes
    )


@app.get("/catalogo/search", response_model=List[EstoqueVariacaoResponse])
def procurar_no_catalogo(q: Optional[str] = None, db: Session = Depends(get_db)):
    if not q: return []
    search_term = f"%{q}%"
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
        variacoes = [EstoqueVariacaoResponse(id=row[0], cor=row[1], quantidade=row[2], url_foto=row[3], disponivel_encomenda=row[4], produto_nome=row[5], modelo_celular=row[6], preco_venda=row[7]) for row in resultado]
        return variacoes
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao buscar no catálogo: {e}")

# --- Endpoint de Autenticação ---
@app.post("/token", response_model=Token)
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    query = text("SELECT username, senha_hash FROM usuarios WHERE username = :username")
    result = db.execute(query, {"username": form_data.username}).first()
    
    if not result or not seguranca.verificar_senha(form_data.password, result[1]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nome de utilizador ou senha incorretos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = seguranca.criar_access_token(data={"sub": form_data.username})
    return {"access_token": access_token, "token_type": "bearer"}


# --- Endpoints de Marcas (Protegidos) ---
@app.get("/marcas", response_model=List[MarcaResponse])
def listar_marcas(db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    try:
        query = text("SELECT id, nome FROM marcas ORDER BY nome")
        resultado = db.execute(query).fetchall()
        marcas = [MarcaResponse(id=row[0], nome=row[1]) for row in resultado]
        return marcas
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao buscar marcas: {e}")

@app.get("/modelos/search", response_model=List[str])
def search_modelos(q: Optional[str] = None, db: Session = Depends(get_db)):
    if not q:
        return []
    
    search_term = f"%{q}%"
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

# ... (O resto do seu código CRUD para Marcas, Modelos, Produtos, Estoque, Fornecedores continua aqui) ...

@app.post("/marcas", status_code=status.HTTP_201_CREATED)
def criar_marca(marca: MarcaBase, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    try:
        query = text("INSERT INTO marcas (nome) VALUES (:nome)")
        db.execute(query, {"nome": marca.nome})
        db.commit()
        return {"mensagem": f"Marca '{marca.nome}' criada com sucesso."}
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Já existe uma marca com este nome.")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao criar marca: {e}")

@app.put("/marcas/{marca_id}")
def atualizar_marca(marca_id: int, marca: MarcaBase, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    try:
        query = text("UPDATE marcas SET nome = :nome WHERE id = :id")
        resultado = db.execute(query, {"nome": marca.nome, "id": marca_id})
        if resultado.rowcount == 0:
            raise HTTPException(status_code=404, detail="Marca não encontrada.")
        db.commit()
        return {"mensagem": f"Marca ID {marca_id} atualizada para '{marca.nome}'."}
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Já existe uma marca com este nome.")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao atualizar marca: {e}")

@app.delete("/marcas/{marca_id}", status_code=status.HTTP_204_NO_CONTENT)
def deletar_marca(marca_id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    try:
        query = text("DELETE FROM marcas WHERE id = :id")
        resultado = db.execute(query, {"id": marca_id})
        if resultado.rowcount == 0:
            raise HTTPException(status_code=404, detail="Marca não encontrada.")
        db.commit()
        return
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Não é possível deletar a marca, pois ela possui modelos de celular vinculados.")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao deletar marca: {e}")

# --- Endpoints de Modelos de Celular ---
@app.get("/modelos", response_model=List[ModeloResponse])
def listar_modelos(db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    try:
        query = text("""
            SELECT m.id, m.nome_modelo, b.nome AS marca_nome
            FROM modelos_celular AS m
            JOIN marcas AS b ON m.id_marca = b.id
            ORDER BY b.nome, m.nome_modelo
        """)
        resultado = db.execute(query).fetchall()
        modelos = [ModeloResponse(id=row[0], nome_modelo=row[1], marca_nome=row[2]) for row in resultado]
        return modelos
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao buscar modelos: {e}")

@app.post("/modelos", status_code=status.HTTP_201_CREATED)
def criar_modelo(modelo: ModeloBase, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    try:
        query = text("INSERT INTO modelos_celular (nome_modelo, id_marca) VALUES (:nome_modelo, :id_marca)")
        db.execute(query, {"nome_modelo": modelo.nome_modelo, "id_marca": modelo.id_marca})
        db.commit()
        return {"mensagem": f"Modelo '{modelo.nome_modelo}' criado com sucesso."}
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Não foi possível criar o modelo. Verifique se o ID da marca é válido.")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao criar modelo: {e}")

@app.put("/modelos/{modelo_id}")
def atualizar_modelo(modelo_id: int, modelo: ModeloBase, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    try:
        query = text("UPDATE modelos_celular SET nome_modelo = :nome_modelo, id_marca = :id_marca WHERE id = :id")
        resultado = db.execute(query, {"nome_modelo": modelo.nome_modelo, "id_marca": modelo.id_marca, "id": modelo_id})
        if resultado.rowcount == 0:
            raise HTTPException(status_code=404, detail="Modelo não encontrado.")
        db.commit()
        return {"mensagem": f"Modelo ID {modelo_id} atualizado com sucesso."}
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Não foi possível atualizar o modelo. Verifique se o ID da marca é válido.")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao atualizar modelo: {e}")

@app.delete("/modelos/{modelo_id}", status_code=status.HTTP_204_NO_CONTENT)
def deletar_modelo(modelo_id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    try:
        query = text("DELETE FROM modelos_celular WHERE id = :id")
        resultado = db.execute(query, {"id": modelo_id})
        if resultado.rowcount == 0:
            raise HTTPException(status_code=404, detail="Modelo não encontrado.")
        db.commit()
        return
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Não é possível deletar o modelo, pois ele possui produtos vinculados.")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao deletar modelo: {e}")

# --- Endpoints de Produtos (Protegidos) ---
@app.get("/produtos", response_model=List[ProdutoResponse])
def listar_produtos(db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    try:
        query = text("""
            SELECT p.id, p.nome, p.tipo, p.material, p.preco_venda, CONCAT(b.nome, ' ', m.nome_modelo) AS modelo_celular
            FROM produtos AS p
            JOIN modelos_celular AS m ON p.id_modelo_celular = m.id
            JOIN marcas AS b ON m.id_marca = b.id
            ORDER BY modelo_celular, p.nome
        """)
        resultado = db.execute(query).fetchall()
        produtos = [ProdutoResponse(id=row[0], nome=row[1], tipo=row[2], material=row[3], preco_venda=row[4], modelo_celular=row[5]) for row in resultado]
        return produtos
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao buscar produtos: {e}")

@app.get("/produtos/{produto_id}/detalhes", response_model=ProdutoAdminResponse)
def get_detalhes_produto_admin(produto_id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    query = text("SELECT id, nome, tipo, material, preco_venda, preco_custo, id_modelo_celular FROM produtos WHERE id = :id")
    produto_db = db.execute(query, {"id": produto_id}).first()
    if not produto_db:
        raise HTTPException(status_code=404, detail="Produto não encontrado.")
    
    produto_dict = {
        "id": produto_db[0],
        "nome": produto_db[1],
        "tipo": produto_db[2],
        "material": produto_db[3],
        "preco_venda": produto_db[4],
        "preco_custo": produto_db[5],
        "id_modelo_celular": produto_db[6]
    }
    return ProdutoAdminResponse(**produto_dict)

@app.post("/produtos", status_code=status.HTTP_201_CREATED)
def criar_produto(produto: ProdutoBase, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    try:
        query = text("""
            INSERT INTO produtos (nome, tipo, material, preco_venda, preco_custo, id_modelo_celular)
            VALUES (:nome, :tipo, :material, :preco_venda, :preco_custo, :id_modelo_celular)
        """)
        db.execute(query, produto.model_dump())
        db.commit()
        return {"mensagem": f"Produto '{produto.nome}' criado com sucesso."}
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Não foi possível criar o produto. Verifique se o ID do modelo de celular é válido.")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao criar produto: {e}")

@app.put("/produtos/{produto_id}")
def atualizar_produto(produto_id: int, produto: ProdutoBase, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    try:
        params = produto.model_dump()
        params["id"] = produto_id
        query = text("""
            UPDATE produtos SET nome = :nome, tipo = :tipo, material = :material, preco_venda = :preco_venda, 
                           preco_custo = :preco_custo, id_modelo_celular = :id_modelo_celular 
            WHERE id = :id
        """)
        resultado = db.execute(query, params)
        if resultado.rowcount == 0:
            raise HTTPException(status_code=404, detail="Produto não encontrado.")
        db.commit()
        return {"mensagem": f"Produto ID {produto_id} atualizado com sucesso."}
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Não foi possível atualizar o produto. Verifique se o ID do modelo de celular é válido.")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao atualizar produto: {e}")

@app.delete("/produtos/{produto_id}", status_code=status.HTTP_204_NO_CONTENT)
def deletar_produto(produto_id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    try:
        query = text("DELETE FROM produtos WHERE id = :id")
        resultado = db.execute(query, {"id": produto_id})
        if resultado.rowcount == 0:
            raise HTTPException(status_code=404, detail="Produto não encontrado.")
        db.commit()
        return
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Não é possível deletar o produto, pois ele possui variações de estoque vinculadas.")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao deletar produto: {e}")

# --- Endpoints de Estoque/Variações (Protegidos) ---
@app.get("/estoque/produto/{produto_id}", response_model=List[EstoqueVariacaoResponse])
def listar_variacoes_por_produto(produto_id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    try:
        query = text("""
            SELECT ev.id, ev.cor, ev.quantidade, ev.url_foto, ev.disponivel_encomenda, p.nome as produto_nome,
                   CONCAT(b.nome, ' ', m.nome_modelo) AS modelo_celular, p.preco_venda
            FROM estoque_variacoes AS ev
            JOIN produtos AS p ON ev.id_produto = p.id
            JOIN modelos_celular AS m ON p.id_modelo_celular = m.id
            JOIN marcas AS b ON m.id_marca = b.id
            WHERE ev.id_produto = :produto_id
            ORDER BY ev.cor
        """)
        resultado = db.execute(query, {"produto_id": produto_id}).fetchall()
        if not resultado:
            produto_existe = db.execute(text("SELECT id FROM produtos WHERE id = :id"), {"id": produto_id}).first()
            if not produto_existe: raise HTTPException(status_code=404, detail="Produto não encontrado.")
        variacoes = [EstoqueVariacaoResponse(id=row[0], cor=row[1], quantidade=row[2], url_foto=row[3], disponivel_encomenda=row[4], produto_nome=row[5], modelo_celular=row[6], preco_venda=row[7]) for row in resultado]
        return variacoes
    except Exception as e:
        if not isinstance(e, HTTPException): raise HTTPException(status_code=500, detail=f"Erro interno ao buscar variações: {e}")
        raise e

@app.post("/estoque", status_code=status.HTTP_201_CREATED)
def criar_variacao_estoque(id_produto: int = Form(...), cor: str = Form(...), quantidade: int = Form(...), disponivel_encomenda: bool = Form(...), foto: Optional[UploadFile] = File(None), db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    url_foto_final = None
    if foto and foto.filename:
        try:
            upload_result = cloudinary.uploader.upload(foto.file, folder="catalogo_api")
            url_foto_final = upload_result.get("secure_url")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Erro ao fazer upload da imagem: {e}")

    try:
        query = text("""
            INSERT INTO estoque_variacoes (id_produto, cor, quantidade, disponivel_encomenda, url_foto)
            VALUES (:id_produto, :cor, :quantidade, :disponivel_encomenda, :url_foto)
        """)
        db.execute(query, {"id_produto": id_produto, "cor": cor.strip(), "quantidade": quantidade, "disponivel_encomenda": disponivel_encomenda, "url_foto": url_foto_final})
        db.commit()
        return {"mensagem": "Variação de estoque criada com sucesso."}
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Não foi possível criar a variação. Verifique se o ID do produto é válido ou se a cor já existe para este produto.")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao criar variação: {e}")

@app.put("/estoque/{variacao_id}")
def atualizar_variacao_estoque(variacao_id: int, cor: str = Form(...), quantidade: int = Form(...), disponivel_encomenda: bool = Form(...), foto: Optional[UploadFile] = File(None), db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    variacao_existente = db.execute(text("SELECT url_foto, id_produto FROM estoque_variacoes WHERE id = :id"), {"id": variacao_id}).first()
    if not variacao_existente:
        raise HTTPException(status_code=404, detail="Variação de estoque não encontrada.")
    
    url_foto_antiga, id_produto = variacao_existente
    url_foto_final = url_foto_antiga

    if foto and foto.filename:
        if url_foto_antiga and "cloudinary" in url_foto_antiga:
            try:
                public_id_with_folder = "/".join(url_foto_antiga.split("/")[-2:])
                public_id = os.path.splitext(public_id_with_folder)[0]
                cloudinary.uploader.destroy(public_id)
            except Exception as e:
                print(f"Aviso: não foi possível apagar a imagem antiga do Cloudinary: {e}")

        try:
            upload_result = cloudinary.uploader.upload(foto.file, folder="catalogo_api")
            url_foto_final = upload_result.get("secure_url")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Erro ao fazer upload da nova imagem: {e}")

    try:
        query = text("""
            UPDATE estoque_variacoes SET cor = :cor, quantidade = :quantidade, disponivel_encomenda = :disponivel_encomenda, url_foto = :url_foto
            WHERE id = :id
        """)
        db.execute(query, {"cor": cor.strip(), "quantidade": quantidade, "disponivel_encomenda": disponivel_encomenda, "url_foto": url_foto_final, "id": variacao_id})
        db.commit()
        return {"mensagem": "Variação de estoque atualizada com sucesso."}
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Já existe uma variação com esta cor para este produto.")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao atualizar variação: {e}")

@app.delete("/estoque/{variacao_id}", status_code=status.HTTP_204_NO_CONTENT)
def deletar_variacao_estoque(variacao_id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    variacao = db.execute(text("SELECT url_foto FROM estoque_variacoes WHERE id = :id"), {"id": variacao_id}).first()
    if not variacao:
        raise HTTPException(status_code=404, detail="Variação de estoque não encontrada.")
    
    url_foto_para_apagar = variacao[0]

    try:
        query = text("DELETE FROM estoque_variacoes WHERE id = :id")
        db.execute(query, {"id": variacao_id})
        db.commit()

        if url_foto_para_apagar and "cloudinary" in url_foto_para_apagar:
            try:
                public_id_with_folder = "/".join(url_foto_para_apagar.split("/")[-2:])
                public_id = os.path.splitext(public_id_with_folder)[0]
                cloudinary.uploader.destroy(public_id)
            except Exception as e:
                print(f"Aviso: não foi possível apagar a imagem do Cloudinary: {e}")
        
        return
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao deletar variação: {e}")

# --- Endpoints de Fornecedores (Protegidos) ---
@app.get("/fornecedores")
def listar_fornecedores(db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    try:
        query = text("SELECT id, nome, contato_telefone, contato_email FROM fornecedores ORDER BY nome")
        resultado = db.execute(query).fetchall()
        fornecedores = [{"id": row[0], "nome": row[1], "contato_telefone": row[2], "contato_email": row[3]} for row in resultado]
        return fornecedores
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao buscar fornecedores: {e}")

@app.post("/fornecedores", status_code=status.HTTP_201_CREATED)
def criar_fornecedor(fornecedor: FornecedorBase, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    try:
        query = text("""
            INSERT INTO fornecedores (nome, contato_telefone, contato_email) 
            VALUES (:nome, :contato_telefone, :contato_email)
        """)
        db.execute(query, fornecedor.model_dump())
        db.commit()
        return {"mensagem": f"Fornecedor '{fornecedor.nome}' criado com sucesso."}
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Já existe um fornecedor com este nome.")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao criar fornecedor: {e}")

@app.put("/fornecedores/{fornecedor_id}")
def atualizar_fornecedor(fornecedor_id: int, fornecedor: FornecedorBase, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    try:
        params = fornecedor.model_dump()
        params["id"] = fornecedor_id
        query = text("""
            UPDATE fornecedores SET nome = :nome, contato_telefone = :contato_telefone, contato_email = :contato_email 
            WHERE id = :id
        """)
        resultado = db.execute(query, params)
        if resultado.rowcount == 0:
            raise HTTPException(status_code=404, detail="Fornecedor não encontrado.")
        db.commit()
        return {"mensagem": f"Fornecedor ID {fornecedor_id} atualizado com sucesso."}
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Já existe um fornecedor com este nome.")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao atualizar fornecedor: {e}")

@app.delete("/fornecedores/{fornecedor_id}", status_code=status.HTTP_204_NO_CONTENT)
def deletar_fornecedor(fornecedor_id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    try:
        query = text("DELETE FROM fornecedores WHERE id = :id")
        resultado = db.execute(query, {"id": fornecedor_id})
        if resultado.rowcount == 0:
            raise HTTPException(status_code=404, detail="Fornecedor não encontrado.")
        db.commit()
        return
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Não é possível deletar o fornecedor, pois ele possui produtos vinculados.")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao deletar fornecedor: {e}")

