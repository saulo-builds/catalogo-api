# routers/marcas.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from typing import List

import schemas
import seguranca
from database import get_db

router = APIRouter(
    prefix="/marcas",
    tags=["Marcas"],
    dependencies=[Depends(seguranca.get_current_admin_user)],
    responses={404: {"description": "Não encontrado"}},
)

@router.get("/", response_model=List[schemas.MarcaResponse])
def listar_marcas(db: Session = Depends(get_db)):
    try:
        query = text("SELECT id, nome FROM marcas ORDER BY nome")
        resultado = db.execute(query).fetchall()
        marcas = [schemas.MarcaResponse(id=row[0], nome=row[1]) for row in resultado]
        return marcas
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao buscar marcas: {e}")

@router.post("/", status_code=status.HTTP_201_CREATED, response_model=dict)
def criar_marca(marca: schemas.MarcaBase, db: Session = Depends(get_db)):
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

@router.put("/{marca_id}", response_model=dict)
def atualizar_marca(marca_id: int, marca: schemas.MarcaBase, db: Session = Depends(get_db)):
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

@router.delete("/{marca_id}", status_code=status.HTTP_204_NO_CONTENT)
def deletar_marca(marca_id: int, db: Session = Depends(get_db)):
    # A lógica de deleção permanece a mesma, mas agora dentro do router.
    # O código original já está correto.
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
