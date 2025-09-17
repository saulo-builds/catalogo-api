# routers/estoque.py

from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile, Form
from sqlalchemy.orm import Session
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from typing import List, Optional, Literal
import os

# Importa as bibliotecas do Cloudinary
import cloudinary
import cloudinary.uploader

import schemas
import seguranca
from database import get_db

router = APIRouter(
    prefix="/estoque",
    tags=["Estoque"],
    responses={404: {"description": "Não encontrado"}},
)

@router.get("/produto/{produto_id}", response_model=List[schemas.EstoqueVariacaoResponse])
def listar_variacoes_por_produto(produto_id: int, db: Session = Depends(get_db), current_user: dict = Depends(seguranca.get_current_user)):
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
        variacoes = [schemas.EstoqueVariacaoResponse(id=row[0], cor=row[1], quantidade=row[2], url_foto=row[3], disponivel_encomenda=row[4], produto_nome=row[5], modelo_celular=row[6], preco_venda=row[7]) for row in resultado]
        return variacoes
    except Exception as e:
        if not isinstance(e, HTTPException): raise HTTPException(status_code=500, detail=f"Erro interno ao buscar variações: {e}")
        raise e

@router.post("/", status_code=status.HTTP_201_CREATED, response_model=dict)
def criar_variacao_estoque(id_produto: int = Form(...), cor: str = Form(...), quantidade: int = Form(...), disponivel_encomenda: bool = Form(...), foto: Optional[UploadFile] = File(None), db: Session = Depends(get_db), current_user: dict = Depends(seguranca.get_current_admin_user)):
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

@router.put("/{variacao_id}", response_model=dict)
def atualizar_variacao_estoque(variacao_id: int, cor: str = Form(...), quantidade: int = Form(...), disponivel_encomenda: bool = Form(...), foto: Optional[UploadFile] = File(None), db: Session = Depends(get_db), current_user: dict = Depends(seguranca.get_current_admin_user)):
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

@router.delete("/{variacao_id}", status_code=status.HTTP_204_NO_CONTENT)
def deletar_variacao_estoque(variacao_id: int, db: Session = Depends(get_db), current_user: dict = Depends(seguranca.get_current_admin_user)):
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

@router.post("/{variacao_id}/{acao}", response_model=dict, tags=["PDV"])
def atualizar_estoque_pdv(
    variacao_id: int,
    acao: Literal['incrementar', 'decrementar'],
    db: Session = Depends(get_db),
    current_user: dict = Depends(seguranca.get_current_user)
):
    """
    Incrementa ou decrementa o estoque de uma variação a partir do PDV,
    registando o histórico da transação com os preços do momento para vendas.
    """
    try:
        # 1. Obter dados da variação e do produto, e bloquear a linha para atualização (FOR UPDATE)
        # para evitar condições de corrida em vendas simultâneas.
        variacao_query = text("""
            SELECT ev.quantidade, p.preco_venda, p.preco_custo
            FROM estoque_variacoes ev
            JOIN produtos p ON ev.id_produto = p.id
            WHERE ev.id = :id FOR UPDATE
        """)
        variacao = db.execute(variacao_query, {"id": variacao_id}).first()

        if not variacao:
            raise HTTPException(status_code=404, detail="Variação de estoque não encontrada.")

        quantidade_atual, preco_venda_atual, preco_custo_atual = variacao
        quantidade_alterada = 1  # PDV altera de 1 em 1
        
        if acao == 'decrementar':
            if quantidade_atual < quantidade_alterada:
                raise HTTPException(status_code=400, detail="Estoque insuficiente para realizar a venda.")
            nova_quantidade = quantidade_atual - quantidade_alterada
            tipo_movimento = 'decremento'
            mensagem = "Venda registrada com sucesso."
            preco_venda_transacao = preco_venda_atual
            preco_custo_transacao = preco_custo_atual
        else:  # incrementar
            nova_quantidade = quantidade_atual + quantidade_alterada
            tipo_movimento = 'incremento'
            mensagem = "Reposição de estoque registrada com sucesso."
            preco_venda_transacao = None
            preco_custo_transacao = None

        # 2. Atualizar a quantidade no estoque
        db.execute(text("UPDATE estoque_variacoes SET quantidade = :nova_quantidade WHERE id = :id"), 
                   {"nova_quantidade": nova_quantidade, "id": variacao_id})

        # 3. Obter ID do usuário
        user_id = db.execute(text("SELECT id FROM usuarios WHERE username = :username"), 
                             {"username": current_user['username']}).scalar()
        if not user_id:
            raise HTTPException(status_code=404, detail="Usuário da sessão não encontrado.")

        # 4. Inserir no histórico com os preços do momento
        history_query = text("""
            INSERT INTO historico_estoque (id_variacao_estoque, id_usuario, tipo_movimento, quantidade_alterada, nova_quantidade_estoque, preco_venda_momento, preco_custo_momento)
            VALUES (:id_variacao, :id_usuario, :tipo_movimento, :qtd_alterada, :nova_qtd, :preco_venda, :preco_custo)
        """)
        db.execute(history_query, {
            "id_variacao": variacao_id, "id_usuario": user_id, "tipo_movimento": tipo_movimento,
            "qtd_alterada": quantidade_alterada, "nova_qtd": nova_quantidade,
            "preco_venda": preco_venda_transacao, "preco_custo": preco_custo_transacao,
        })
        
        db.commit()
        
        return {"mensagem": mensagem, "nova_quantidade": nova_quantidade}
    except HTTPException as http_exc:
        db.rollback()
        raise http_exc # Re-lança exceções HTTP para o FastAPI tratar
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Ocorreu um erro interno no servidor: {e}")