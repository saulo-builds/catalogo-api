# routers/modelos.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from typing import List

import schemas
import seguranca
from database import get_db

router = APIRouter(
    prefix="/modelos",
    tags=["Modelos"],
    dependencies=[Depends(seguranca.get_current_admin_user)],
    responses={404: {"description": "Não encontrado"}},
)

@router.get("/", response_model=List[schemas.ModeloResponse])
def listar_modelos(db: Session = Depends(get_db)):
    try:
        query = text("""
            SELECT m.id, m.nome_modelo, b.nome as marca_nome
            FROM modelos_celular AS m
            JOIN marcas AS b ON m.id_marca = b.id
            ORDER BY b.nome, m.nome_modelo
        """)
        resultado = db.execute(query).fetchall()
        modelos = [schemas.ModeloResponse(id=row[0], nome_modelo=row[1], marca_nome=row[2]) for row in resultado]
        return modelos
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao buscar modelos: {e}")

@router.post("/", status_code=status.HTTP_201_CREATED, response_model=dict)
def criar_modelo(modelo: schemas.ModeloBase, db: Session = Depends(get_db)):
    try:
        query = text("INSERT INTO modelos_celular (nome_modelo, id_marca) VALUES (:nome_modelo, :id_marca)")
        db.execute(query, modelo.model_dump())
        db.commit()
        return {"mensagem": f"Modelo '{modelo.nome_modelo}' criado com sucesso."}
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Não foi possível criar o modelo. Verifique se o ID da marca é válido.")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao criar modelo: {e}")

@router.put("/{modelo_id}", response_model=dict)
def atualizar_modelo(modelo_id: int, modelo: schemas.ModeloBase, db: Session = Depends(get_db)):
    try:
        params = modelo.model_dump()
        params["id"] = modelo_id
        query = text("UPDATE modelos_celular SET nome_modelo = :nome_modelo, id_marca = :id_marca WHERE id = :id")
        resultado = db.execute(query, params)
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

@router.delete("/{modelo_id}", status_code=status.HTTP_204_NO_CONTENT)
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