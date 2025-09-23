# routers/estoque.py

from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile, Form
from sqlalchemy.orm import Session
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from typing import List, Optional, Literal
from decimal import Decimal
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

@router.get("/health", status_code=status.HTTP_200_OK, include_in_schema=False)
def health_check():
    """
    Endpoint público para verificar a saúde da API e mantê-la "quente".
    """
    return {"status": "ok"}


@router.get("/produto/{produto_id}", response_model=List[schemas.EstoqueVariacaoResponse])
def listar_variacoes_por_produto(produto_id: int, db: Session = Depends(get_db), current_user: dict = Depends(seguranca.get_current_user)):
    try:
        query = text("""
            SELECT ev.id, ev.cor, ev.quantidade, ev.url_foto, ev.disponivel_encomenda, ev.preco_custo, p.nome as produto_nome,
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
        variacoes = [schemas.EstoqueVariacaoResponse(
            id=row.id, 
            cor=row.cor, 
            quantidade=row.quantidade, 
            url_foto=row.url_foto, 
            disponivel_encomenda=row.disponivel_encomenda, 
            preco_custo=row.preco_custo,
            produto_nome=row.produto_nome, 
            modelo_celular=row.modelo_celular, 
            preco_venda=row.preco_venda
        ) for row in resultado]
        return variacoes
    except Exception as e:
        if not isinstance(e, HTTPException): raise HTTPException(status_code=500, detail=f"Erro interno ao buscar variações: {e}")
        raise e

@router.post("/", status_code=status.HTTP_201_CREATED, response_model=dict)
def criar_variacao_estoque(id_produto: int = Form(...), cor: str = Form(...), quantidade: int = Form(...), preco_custo: float = Form(...), disponivel_encomenda: bool = Form(...), foto: Optional[UploadFile] = File(None), db: Session = Depends(get_db), current_user: dict = Depends(seguranca.get_current_admin_user)):
    url_foto_final = None
    if foto and foto.filename:
        try:
            upload_result = cloudinary.uploader.upload(foto.file, folder="catalogo_api")
            url_foto_final = upload_result.get("secure_url")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Erro ao fazer upload da imagem: {e}")
    try:
        query = text("""
            INSERT INTO estoque_variacoes (id_produto, cor, quantidade, preco_custo, disponivel_encomenda, url_foto)
            VALUES (:id_produto, :cor, :quantidade, :preco_custo, :disponivel_encomenda, :url_foto)
        """)
        db.execute(query, {"id_produto": id_produto, "cor": cor.strip(), "quantidade": quantidade, "preco_custo": preco_custo, "disponivel_encomenda": disponivel_encomenda, "url_foto": url_foto_final})
        db.commit()
        return {"mensagem": "Variação de estoque criada com sucesso."}
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Não foi possível criar a variação. Verifique se o ID do produto é válido ou se a cor já existe para este produto.")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao criar variação: {e}")

@router.put("/{variacao_id}", response_model=dict)
def atualizar_variacao_estoque(variacao_id: int, cor: str = Form(...), disponivel_encomenda: bool = Form(...), foto: Optional[UploadFile] = File(None), db: Session = Depends(get_db), current_user: dict = Depends(seguranca.get_current_admin_user)):
    # NOTA: A quantidade e o preço de custo não são editados aqui diretamente.
    # Eles são alterados através dos endpoints de compra (incremento) e venda (decremento).
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
            UPDATE estoque_variacoes SET cor = :cor, disponivel_encomenda = :disponivel_encomenda, url_foto = :url_foto
            WHERE id = :id
        """)
        db.execute(query, {"cor": cor.strip(), "disponivel_encomenda": disponivel_encomenda, "url_foto": url_foto_final, "id": variacao_id})
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

@router.post("/{variacao_id}/compra", response_model=dict, dependencies=[Depends(seguranca.get_current_admin_user)])
def registrar_compra_estoque(
    variacao_id: int,
    compra: schemas.CompraEstoque,
    db: Session = Depends(get_db),
    current_user: dict = Depends(seguranca.get_current_user)
):
    """
    Registra a entrada de novos itens no estoque (compra), recalculando o preço de custo médio ponderado.
    """
    try:
        # Bloqueia a linha para evitar condições de corrida
        variacao_query = text("SELECT quantidade, preco_custo FROM estoque_variacoes WHERE id = :id FOR UPDATE")
        variacao_atual = db.execute(variacao_query, {"id": variacao_id}).first()

        if not variacao_atual:
            raise HTTPException(status_code=404, detail="Variação de estoque não encontrada.")

        qtd_antiga, custo_antigo = variacao_atual
        qtd_antiga = qtd_antiga or 0
        # Garante que o custo antigo seja um Decimal, mesmo que seja nulo no banco
        custo_antigo = custo_antigo or Decimal('0.00')

        # Converte o custo da compra (float) para Decimal para precisão
        custo_unitario_compra = Decimal(str(compra.custo_unitario))

        # Calcula o novo custo médio ponderado usando Decimal
        valor_estoque_antigo = Decimal(qtd_antiga) * custo_antigo
        valor_compra_nova = Decimal(compra.quantidade) * custo_unitario_compra
        
        nova_qtd_total = qtd_antiga + compra.quantidade
        novo_valor_total_estoque = valor_estoque_antigo + valor_compra_nova
        
        novo_custo_medio = novo_valor_total_estoque / Decimal(nova_qtd_total) if nova_qtd_total > 0 else Decimal('0.00')

        # Atualiza a variação do estoque com os novos valores
        update_query = text("UPDATE estoque_variacoes SET quantidade = :qtd, preco_custo = :custo WHERE id = :id")
        db.execute(update_query, {"qtd": nova_qtd_total, "custo": novo_custo_medio, "id": variacao_id})

        # Registra no histórico o custo unitário desta compra específica
        user_id = db.execute(text("SELECT id FROM usuarios WHERE username = :username"), {"username": current_user['username']}).scalar()
        history_query = text("""
            INSERT INTO historico_estoque (id_variacao_estoque, id_usuario, tipo_movimento, quantidade_alterada, nova_quantidade_estoque, preco_custo_momento)
            VALUES (:id_variacao, :id_usuario, 'incremento', :qtd_alterada, :nova_qtd, :custo_compra)
        """)
        db.execute(history_query, {"id_variacao": variacao_id, "id_usuario": user_id, "qtd_alterada": compra.quantidade, "nova_qtd": nova_qtd_total, "custo_compra": custo_unitario_compra})

        db.commit()
        return {"mensagem": "Compra registrada e estoque atualizado com sucesso.", "nova_quantidade": nova_qtd_total, "novo_custo_medio": round(float(novo_custo_medio), 2)}

    except HTTPException as http_exc:
        db.rollback()
        raise http_exc
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Ocorreu um erro interno: {e}")

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
            SELECT ev.quantidade, ev.preco_custo, p.preco_venda
            FROM estoque_variacoes ev
            JOIN produtos p ON ev.id_produto = p.id
            WHERE ev.id = :id FOR UPDATE
        """)
        variacao = db.execute(variacao_query, {"id": variacao_id}).first()

        if not variacao:
            raise HTTPException(status_code=404, detail="Variação de estoque não encontrada.")

        quantidade_atual, preco_custo_atual, preco_venda_atual = variacao
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