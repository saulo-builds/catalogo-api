# main.py

import shutil
from fastapi import FastAPI, Depends, HTTPException, status, File, UploadFile, Form
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import OperationalError, IntegrityError
from pydantic import BaseModel, field_validator
import re # Importa o módulo de expressões regulares
from typing import List, Optional
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

# --- Definição de Caminhos (MAIS ROBUSTO) ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
UPLOAD_DIRECTORY = os.path.join(STATIC_DIR, "images/")

# --- Cria a pasta de uploads se não existir ---
if not os.path.exists(UPLOAD_DIRECTORY):
    os.makedirs(UPLOAD_DIRECTORY)

# --- Modelos Pydantic ---
class MarcaBase(BaseModel):
    nome: str

class ModeloBase(BaseModel):
    nome_modelo: str
    id_marca: int

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

class ProdutoResponse(BaseModel):
    id: int
    nome: str
    tipo: str
    material: Optional[str] = None
    preco_venda: float
    modelo_celular: str

class EstoqueVariacaoBase(BaseModel):
    id_produto: int
    cor: str
    quantidade: int
    disponivel_encomenda: bool = True

class EstoqueVariacaoResponse(BaseModel):
    id: int
    cor: str
    quantidade: int
    disponivel_encomenda: bool
    url_foto: Optional[str] = None
    produto_nome: str
    modelo_celular: str

class FornecedorBase(BaseModel):
    nome: str
    contato_telefone: Optional[str] = None
    contato_email: Optional[str] = None

    # Validador para o campo de telefone
    @field_validator('contato_telefone')
    def validar_telefone(cls, v):
        if v is None:
            return v
        # Expressão regular para validar formatos de telefone brasileiros
        # Ex: (11) 98765-4321, 11987654321, etc.
        regex = re.compile(r'^\(?\d{2}\)?[\s-]?\d{4,5}-?\d{4}$')
        if not regex.match(v):
            raise ValueError('Número de telefone inválido.')
        return v

# --- Configuração do Banco de Dados ---
DATABASE_URL_ENV = os.getenv("DATABASE_URL")

if DATABASE_URL_ENV and DATABASE_URL_ENV.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL_ENV.replace("postgres://", "postgresql://", 1)
    print("A usar a base de dados PostgreSQL do Render.")
else:
    DATABASE_URL = "mysql+mysqlconnector://root:@localhost/catalogo_inteligente"
    print("A usar a base de dados local MariaDB/MySQL.")


try:
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    with engine.connect() as connection:
        print("Conexão com o banco de dados estabelecida com sucesso!")
except Exception as e:
    print(f"Erro ao conectar ao banco de dados: {e}")
    exit()

# --- Dependência para obter a sessão do banco de dados ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- Início da Aplicação FastAPI ---
app = FastAPI()

# --- Montar diretório estático para servir as imagens (MAIS ROBUSTO) ---
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


# --- Endpoint Principal para servir o Frontend (CORRIGIDO) ---
@app.get("/")
def ler_raiz():
    """
    Este endpoint serve a página principal do painel administrativo.
    """
    return FileResponse(os.path.join(BASE_DIR, 'index.html'))


# --- Endpoints de Marcas ---
@app.get("/marcas")
def listar_marcas(db: Session = Depends(get_db)):
    try:
        query = text("SELECT id, nome FROM marcas ORDER BY nome")
        resultado = db.execute(query).fetchall()
        marcas = [{"id": row[0], "nome": row[1]} for row in resultado]
        return marcas
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao buscar marcas: {e}")

@app.post("/marcas", status_code=status.HTTP_201_CREATED)
def criar_marca(marca: MarcaBase, db: Session = Depends(get_db)):
    try:
        query = text("INSERT INTO marcas (nome) VALUES (:nome)")
        db.execute(query, {"nome": marca.nome})
        db.commit()
        return {"mensagem": f"Marca '{marca.nome}' criada com sucesso."}
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Marca já existente.")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao criar marca: {e}")

@app.put("/marcas/{marca_id}")
def atualizar_marca(marca_id: int, marca: MarcaBase, db: Session = Depends(get_db)):
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
def deletar_marca(marca_id: int, db: Session = Depends(get_db)):
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
def listar_modelos(db: Session = Depends(get_db)):
    try:
        query = text("""
            SELECT m.id, m.nome_modelo, b.nome AS marca_nome
            FROM modelos_celular AS m
            JOIN marcas AS b ON m.id_marca = b.id
            ORDER BY b.nome, m.nome_modelo
        """)
        resultado = db.execute(query).fetchall()
        modelos = [
            ModeloResponse(id=row[0], nome_modelo=row[1], marca_nome=row[2]) 
            for row in resultado
        ]
        return modelos
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao buscar modelos: {e}")

@app.post("/modelos", status_code=status.HTTP_201_CREATED)
def criar_modelo(modelo: ModeloBase, db: Session = Depends(get_db)):
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
def atualizar_modelo(modelo_id: int, modelo: ModeloBase, db: Session = Depends(get_db)):
    try:
        query = text("UPDATE modelos_celular SET nome_modelo = :nome_modelo, id_marca = :id_marca WHERE id = :id")
        resultado = db.execute(query, {
            "nome_modelo": modelo.nome_modelo,
            "id_marca": modelo.id_marca,
            "id": modelo_id
        })
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
def deletar_modelo(modelo_id: int, db: Session = Depends(get_db)):
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

# --- Endpoints de Produtos ---
@app.get("/produtos", response_model=List[ProdutoResponse])
def listar_produtos(db: Session = Depends(get_db)):
    try:
        query = text("""
            SELECT 
                p.id, p.nome, p.tipo, p.material, p.preco_venda,
                CONCAT(b.nome, ' ', m.nome_modelo) AS modelo_celular
            FROM produtos AS p
            JOIN modelos_celular AS m ON p.id_modelo_celular = m.id
            JOIN marcas AS b ON m.id_marca = b.id
            ORDER BY modelo_celular, p.nome
        """)
        resultado = db.execute(query).fetchall()
        
        produtos = [
            ProdutoResponse(
                id=row[0], nome=row[1], tipo=row[2], material=row[3],
                preco_venda=row[4], modelo_celular=row[5]
            ) for row in resultado
        ]
        return produtos
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao buscar produtos: {e}")

@app.post("/produtos", status_code=status.HTTP_201_CREATED)
def criar_produto(produto: ProdutoBase, db: Session = Depends(get_db)):
    try:
        query = text("""
            INSERT INTO produtos (nome, tipo, material, preco_venda, preco_custo, id_modelo_celular)
            VALUES (:nome, :tipo, :material, :preco_venda, :preco_custo, :id_modelo_celular)
        """)
        db.execute(query, {
            "nome": produto.nome, "tipo": produto.tipo, "material": produto.material,
            "preco_venda": produto.preco_venda, "preco_custo": produto.preco_custo,
            "id_modelo_celular": produto.id_modelo_celular
        })
        db.commit()
        return {"mensagem": f"Produto '{produto.nome}' criado com sucesso."}
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Não foi possível criar o produto. Verifique se o ID do modelo de celular é válido.")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao criar produto: {e}")

@app.put("/produtos/{produto_id}")
def atualizar_produto(produto_id: int, produto: ProdutoBase, db: Session = Depends(get_db)):
    try:
        query = text("""
            UPDATE produtos SET 
                nome = :nome, 
                tipo = :tipo, 
                material = :material, 
                preco_venda = :preco_venda, 
                preco_custo = :preco_custo, 
                id_modelo_celular = :id_modelo_celular 
            WHERE id = :id
        """)
        resultado = db.execute(query, {
            "nome": produto.nome, "tipo": produto.tipo, "material": produto.material,
            "preco_venda": produto.preco_venda, "preco_custo": produto.preco_custo,
            "id_modelo_celular": produto.id_modelo_celular,
            "id": produto_id
        })
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
def deletar_produto(produto_id: int, db: Session = Depends(get_db)):
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

# --- Endpoints de Estoque/Variações ---
@app.get("/estoque/produto/{produto_id}", response_model=List[EstoqueVariacaoResponse])
def listar_variacoes_por_produto(produto_id: int, db: Session = Depends(get_db)):
    try:
        query = text("""
            SELECT 
                ev.id, ev.cor, ev.quantidade, ev.url_foto, ev.disponivel_encomenda,
                p.nome as produto_nome,
                CONCAT(b.nome, ' ', m.nome_modelo) AS modelo_celular
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
            if not produto_existe:
                raise HTTPException(status_code=404, detail="Produto não encontrado.")
        
        variacoes = [
            EstoqueVariacaoResponse(
                id=row[0], cor=row[1], quantidade=row[2], url_foto=row[3],
                disponivel_encomenda=row[4],
                produto_nome=row[5], modelo_celular=row[6]
            ) for row in resultado
        ]
        return variacoes
    except Exception as e:
        if not isinstance(e, HTTPException):
             raise HTTPException(status_code=500, detail=f"Erro interno ao buscar variações: {e}")
        raise e

@app.post("/estoque", status_code=status.HTTP_201_CREATED)
def criar_variacao_estoque(
    id_produto: int = Form(...),
    cor: str = Form(...),
    quantidade: int = Form(...),
    disponivel_encomenda: bool = Form(...),
    foto: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db)
):
    url_foto_final = None
    if foto and foto.filename:
        nome_arquivo = f"{id_produto}_{cor}_{foto.filename}".replace(" ", "_")
        file_path = os.path.join(UPLOAD_DIRECTORY, nome_arquivo)
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(foto.file, buffer)
        
        url_foto_final = f"/static/images/{nome_arquivo}"

    try:
        query = text("""
            INSERT INTO estoque_variacoes (id_produto, cor, quantidade, disponivel_encomenda, url_foto)
            VALUES (:id_produto, :cor, :quantidade, :disponivel_encomenda, :url_foto)
        """)
        db.execute(query, {
            "id_produto": id_produto,
            "cor": cor,
            "quantidade": quantidade,
            "disponivel_encomenda": disponivel_encomenda,
            "url_foto": url_foto_final
        })
        db.commit()
        return {"mensagem": "Variação de estoque criada com sucesso."}
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Não foi possível criar a variação. Verifique se o ID do produto é válido ou se a cor já existe para este produto.")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao criar variação: {e}")

@app.put("/estoque/{variacao_id}")
def atualizar_variacao_estoque(
    variacao_id: int,
    cor: str = Form(...),
    quantidade: int = Form(...),
    disponivel_encomenda: bool = Form(...),
    foto: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db)
):
    variacao_existente = db.execute(text("SELECT url_foto, id_produto FROM estoque_variacoes WHERE id = :id"), {"id": variacao_id}).first()
    if not variacao_existente:
        raise HTTPException(status_code=404, detail="Variação de estoque não encontrada.")

    url_foto_antiga = variacao_existente[0]
    id_produto = variacao_existente[1]
    url_foto_final = url_foto_antiga

    if foto and foto.filename:
        if url_foto_antiga:
            caminho_foto_antiga = os.path.join(BASE_DIR, url_foto_antiga.lstrip('/'))
            if os.path.exists(caminho_foto_antiga):
                os.remove(caminho_foto_antiga)
        
        nome_arquivo = f"{id_produto}_{cor}_{foto.filename}".replace(" ", "_")
        file_path = os.path.join(UPLOAD_DIRECTORY, nome_arquivo)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(foto.file, buffer)
        url_foto_final = f"/static/images/{nome_arquivo}"

    try:
        query = text("""
            UPDATE estoque_variacoes SET
                cor = :cor,
                quantidade = :quantidade,
                disponivel_encomenda = :disponivel_encomenda,
                url_foto = :url_foto
            WHERE id = :id
        """)
        db.execute(query, {
            "cor": cor,
            "quantidade": quantidade,
            "disponivel_encomenda": disponivel_encomenda,
            "url_foto": url_foto_final,
            "id": variacao_id
        })
        db.commit()
        return {"mensagem": "Variação de estoque atualizada com sucesso."}
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Já existe uma variação com esta cor para este produto.")
    except Exception as e:
        db.rollback()
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=f"Erro ao atualizar variação: {e}")


@app.delete("/estoque/{variacao_id}", status_code=status.HTTP_204_NO_CONTENT)
def deletar_variacao_estoque(variacao_id: int, db: Session = Depends(get_db)):
    variacao = db.execute(text("SELECT url_foto FROM estoque_variacoes WHERE id = :id"), {"id": variacao_id}).first()
    if not variacao:
        raise HTTPException(status_code=404, detail="Variação de estoque não encontrada.")

    try:
        query = text("DELETE FROM estoque_variacoes WHERE id = :id")
        db.execute(query, {"id": variacao_id})
        db.commit()

        url_foto = variacao[0]
        if url_foto:
            caminho_foto = os.path.join(BASE_DIR, url_foto.lstrip('/'))
            if os.path.exists(caminho_foto):
                os.remove(caminho_foto)
        
        return
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao deletar variação: {e}")

# --- Endpoints de Fornecedores ---

@app.get("/fornecedores")
def listar_fornecedores(db: Session = Depends(get_db)):
    try:
        query = text("SELECT id, nome, contato_telefone, contato_email FROM fornecedores ORDER BY nome")
        resultado = db.execute(query).fetchall()
        fornecedores = [
            {"id": row[0], "nome": row[1], "contato_telefone": row[2], "contato_email": row[3]} 
            for row in resultado
        ]
        return fornecedores
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao buscar fornecedores: {e}")

@app.post("/fornecedores", status_code=status.HTTP_201_CREATED)
def criar_fornecedor(fornecedor: FornecedorBase, db: Session = Depends(get_db)):
    try:
        query = text("""
            INSERT INTO fornecedores (nome, contato_telefone, contato_email) 
            VALUES (:nome, :contato_telefone, :contato_email)
        """)
        db.execute(query, {
            "nome": fornecedor.nome,
            "contato_telefone": fornecedor.contato_telefone,
            "contato_email": fornecedor.contato_email
        })
        db.commit()
        return {"mensagem": f"Fornecedor '{fornecedor.nome}' criado com sucesso."}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao criar fornecedor: {e}")

@app.put("/fornecedores/{fornecedor_id}")
def atualizar_fornecedor(fornecedor_id: int, fornecedor: FornecedorBase, db: Session = Depends(get_db)):
    try:
        query = text("""
            UPDATE fornecedores SET 
                nome = :nome, 
                contato_telefone = :contato_telefone, 
                contato_email = :contato_email 
            WHERE id = :id
        """)
        resultado = db.execute(query, {
            "nome": fornecedor.nome,
            "contato_telefone": fornecedor.contato_telefone,
            "contato_email": fornecedor.contato_email,
            "id": fornecedor_id
        })
        if resultado.rowcount == 0:
            raise HTTPException(status_code=404, detail="Fornecedor não encontrado.")
        db.commit()
        return {"mensagem": f"Fornecedor ID {fornecedor_id} atualizado com sucesso."}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao atualizar fornecedor: {e}")

@app.delete("/fornecedores/{fornecedor_id}", status_code=status.HTTP_204_NO_CONTENT)
def deletar_fornecedor(fornecedor_id: int, db: Session = Depends(get_db)):
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
