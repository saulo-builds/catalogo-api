# routers/produtos.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from typing import List

import schemas
import seguranca
from database import get_db

router = APIRouter(
    prefix="/produtos",
    tags=["Produtos"],
    dependencies=[Depends(seguranca.get_current_admin_user)],
    responses={404: {"description": "Não encontrado"}},
)

@router.get("/", response_model=List[schemas.ProdutoResponse])
def listar_produtos(db: Session = Depends(get_db)):
    try:
        query = text("""
            SELECT p.id, p.nome, p.tipo, p.material, p.preco_venda, CONCAT(b.nome, ' ', m.nome_modelo) AS modelo_celular
            FROM produtos AS p
            JOIN modelos_celular AS m ON p.id_modelo_celular = m.id
            JOIN marcas AS b ON m.id_marca = b.id
            ORDER BY modelo_celular, p.nome
        """)
        resultado = db.execute(query).fetchall()
        produtos = [schemas.ProdutoResponse(id=row[0], nome=row[1], tipo=row[2], material=row[3], preco_venda=row[4], modelo_celular=row[5]) for row in resultado]
        return produtos
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao buscar produtos: {e}")

@router.get("/{produto_id}/detalhes", response_model=schemas.ProdutoAdminResponse)
def get_detalhes_produto_admin(produto_id: int, db: Session = Depends(get_db)):
    query = text("SELECT id, nome, tipo, material, preco_venda, id_modelo_celular FROM produtos WHERE id = :id")
    produto_db = db.execute(query, {"id": produto_id}).first()
    if not produto_db:
        raise HTTPException(status_code=404, detail="Produto não encontrado.")
    # Mapeamento por nome para maior clareza
    return schemas.ProdutoAdminResponse(id=produto_db.id, nome=produto_db.nome, tipo=produto_db.tipo, material=produto_db.material, preco_venda=produto_db.preco_venda, id_modelo_celular=produto_db.id_modelo_celular)

@router.post("/", status_code=status.HTTP_201_CREATED, response_model=dict)
def criar_produto(produto: schemas.ProdutoBase, db: Session = Depends(get_db)):
    try:
        query = text("""
            INSERT INTO produtos (nome, tipo, material, preco_venda, id_modelo_celular)
            VALUES (:nome, :tipo, :material, :preco_venda, :id_modelo_celular)
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

@router.put("/{produto_id}", response_model=dict)
def atualizar_produto(produto_id: int, produto: schemas.ProdutoBase, db: Session = Depends(get_db)):
    try:
        params = produto.model_dump()
        params["id"] = produto_id
        query = text("""
            UPDATE produtos SET nome = :nome, tipo = :tipo, material = :material, preco_venda = :preco_venda, id_modelo_celular = :id_modelo_celular 
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

@router.delete("/{produto_id}", status_code=status.HTTP_204_NO_CONTENT)
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

# --- Endpoints de Associação Produto-Fornecedor ---
@router.get("/{produto_id}/fornecedores", response_model=List[schemas.FornecedorResponse])
def listar_fornecedores_do_produto(produto_id: int, db: Session = Depends(get_db)):
    try:
        query = text("""
            SELECT f.id, f.nome, f.contato_telefone, f.contato_email
            FROM fornecedores f
            JOIN produtos_fornecedores pf ON f.id = pf.id_fornecedor
            WHERE pf.id_produto = :produto_id
            ORDER BY f.nome
        """)
        resultado = db.execute(query, {"produto_id": produto_id}).fetchall()
        fornecedores = [schemas.FornecedorResponse(id=row[0], nome=row[1], contato_telefone=row[2], contato_email=row[3]) for row in resultado]
        return fornecedores
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao buscar fornecedores do produto: {e}")

@router.post("/{produto_id}/fornecedores", status_code=status.HTTP_201_CREATED, response_model=dict)
def adicionar_fornecedor_ao_produto(produto_id: int, associacao: schemas.AssociacaoProdutoFornecedor, db: Session = Depends(get_db)):
    try:
        query = text("INSERT INTO produtos_fornecedores (id_produto, id_fornecedor) VALUES (:id_produto, :id_fornecedor)")
        db.execute(query, {"id_produto": produto_id, "id_fornecedor": associacao.id_fornecedor})
        db.commit()
        return {"mensagem": "Fornecedor associado ao produto com sucesso."}
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Associação já existe ou IDs são inválidos.")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao associar fornecedor: {e}")

@router.delete("/{produto_id}/fornecedores/{fornecedor_id}", status_code=status.HTTP_204_NO_CONTENT)
def remover_fornecedor_do_produto(produto_id: int, fornecedor_id: int, db: Session = Depends(get_db)):
    try:
        query = text("DELETE FROM produtos_fornecedores WHERE id_produto = :id_produto AND id_fornecedor = :id_fornecedor")
        resultado = db.execute(query, {"id_produto": produto_id, "id_fornecedor": fornecedor_id})
        if resultado.rowcount == 0:
            raise HTTPException(status_code=404, detail="Associação não encontrada.")
        db.commit()
        return
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao remover associação: {e}")