# routers/fornecedores.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from typing import List

import schemas
import seguranca
from database import get_db

router = APIRouter(
    prefix="/fornecedores",
    tags=["Fornecedores"],
    dependencies=[Depends(seguranca.get_current_admin_user)],
    responses={404: {"description": "Não encontrado"}},
)

@router.get("/", response_model=List[schemas.FornecedorResponse])
def listar_fornecedores(db: Session = Depends(get_db)):
    try:
        query = text("SELECT id, nome, contato_telefone, contato_email FROM fornecedores ORDER BY nome")
        resultado = db.execute(query).fetchall()
        fornecedores = [schemas.FornecedorResponse(id=row[0], nome=row[1], contato_telefone=row[2], contato_email=row[3]) for row in resultado]
        return fornecedores
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao buscar fornecedores: {e}")

@router.post("/", status_code=status.HTTP_201_CREATED, response_model=dict)
def criar_fornecedor(fornecedor: schemas.FornecedorBase, db: Session = Depends(get_db)):
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

@router.put("/{fornecedor_id}", response_model=dict)
def atualizar_fornecedor(fornecedor_id: int, fornecedor: schemas.FornecedorBase, db: Session = Depends(get_db)):
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

@router.delete("/{fornecedor_id}", status_code=status.HTTP_204_NO_CONTENT)
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