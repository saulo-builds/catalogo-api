# routers/pdv.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text

import seguranca
from database import get_db

router = APIRouter(
    prefix="/estoque",
    tags=["PDV"],
    dependencies=[Depends(seguranca.get_current_user)],
    responses={404: {"description": "Não encontrado"}},
)

@router.post("/{variacao_id}/decrementar", status_code=200, response_model=dict)
def decrementar_estoque(variacao_id: int, db: Session = Depends(get_db), current_user: dict = Depends(seguranca.get_current_user)):
    try:
        # 1. Atualiza o estoque
        query = text("UPDATE estoque_variacoes SET quantidade = quantidade - 1 WHERE id = :id AND quantidade > 0")
        resultado = db.execute(query, {"id": variacao_id})
        if resultado.rowcount == 0:
            raise HTTPException(status_code=400, detail="Estoque já está zerado ou variação não encontrada.")

        # 2. Busca o ID do utilizador e a nova quantidade
        user_id = db.execute(text("SELECT id FROM usuarios WHERE username = :username"), {"username": current_user["username"]}).scalar()
        nova_qtd = db.execute(text("SELECT quantidade FROM estoque_variacoes WHERE id = :id"), {"id": variacao_id}).scalar()

        # 3. Regista no histórico
        log_query = text("""
            INSERT INTO historico_estoque (id_variacao_estoque, id_usuario, tipo_movimento, nova_quantidade_estoque)
            VALUES (:id_variacao, :id_usuario, 'decremento', :nova_qtd)
        """)
        db.execute(log_query, {"id_variacao": variacao_id, "id_usuario": user_id, "nova_qtd": nova_qtd})

        db.commit() # Confirma todas as operações
        return {"mensagem": "Estoque decrementado com sucesso.", "nova_quantidade": nova_qtd}
    except Exception as e:
        db.rollback()
        if isinstance(e, HTTPException): raise e
        raise HTTPException(status_code=500, detail=f"Erro ao decrementar estoque: {e}")

@router.post("/{variacao_id}/incrementar", status_code=200, response_model=dict)
def incrementar_estoque(variacao_id: int, db: Session = Depends(get_db), current_user: dict = Depends(seguranca.get_current_user)):
    try:
        query = text("UPDATE estoque_variacoes SET quantidade = quantidade + 1 WHERE id = :id")
        resultado = db.execute(query, {"id": variacao_id})
        if resultado.rowcount == 0:
            raise HTTPException(status_code=404, detail="Variação não encontrada.")

        user_id = db.execute(text("SELECT id FROM usuarios WHERE username = :username"), {"username": current_user["username"]}).scalar()
        nova_qtd = db.execute(text("SELECT quantidade FROM estoque_variacoes WHERE id = :id"), {"id": variacao_id}).scalar()

        log_query = text("""
            INSERT INTO historico_estoque (id_variacao_estoque, id_usuario, tipo_movimento, nova_quantidade_estoque)
            VALUES (:id_variacao, :id_usuario, 'incremento', :nova_qtd)
        """)
        db.execute(log_query, {"id_variacao": variacao_id, "id_usuario": user_id, "nova_qtd": nova_qtd})

        db.commit()
        return {"mensagem": "Estoque incrementado com sucesso.", "nova_quantidade": nova_qtd}
    except Exception as e:
        db.rollback()
        if isinstance(e, HTTPException): raise e
        raise HTTPException(status_code=500, detail=f"Erro ao incrementar estoque: {e}")