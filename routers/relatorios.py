# routers/relatorios.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional
from datetime import date, datetime, time, timedelta

import schemas
import seguranca
from database import get_db, get_engine

router = APIRouter(
    prefix="/relatorios",
    tags=["Relatórios"],
    dependencies=[Depends(seguranca.get_current_admin_user)],
    responses={404: {"description": "Não encontrado"}},
)

@router.get("/movimentacoes-pdv", response_model=List[schemas.RelatorioMovimentacaoResponse])
def get_relatorio_movimentacoes_pdv(
    data_inicio: Optional[date] = None,
    data_fim: Optional[date] = None,
    db: Session = Depends(get_db)
):
    # Define o período padrão para os últimos 7 dias se não for especificado
    if data_fim is None:
        data_fim = date.today()
    if data_inicio is None:
        data_inicio = data_fim - timedelta(days=6)

    # Combina data com tempo para criar um datetime completo para a query
    datetime_inicio = datetime.combine(data_inicio, time.min)
    datetime_fim = datetime.combine(data_fim, time.max)

    query = text("""
        SELECT
            h.data_hora,
            p.nome AS produto_nome,
            ev.cor AS cor_variacao,
            CONCAT(b.nome, ' ', m.nome_modelo) AS modelo_celular,
            u.username AS usuario,
            h.tipo_movimento,
            h.nova_quantidade_estoque,
            h.quantidade_alterada
        FROM historico_estoque h
        JOIN usuarios u ON h.id_usuario = u.id
        JOIN estoque_variacoes ev ON h.id_variacao_estoque = ev.id
        JOIN produtos p ON ev.id_produto = p.id
        JOIN modelos_celular m ON p.id_modelo_celular = m.id
        JOIN marcas b ON m.id_marca = b.id
        WHERE h.data_hora BETWEEN :inicio AND :fim
        ORDER BY h.data_hora DESC
    """)

    try:
        resultados = db.execute(query, {"inicio": datetime_inicio, "fim": datetime_fim}).fetchall()
        relatorio = []
        for row in resultados:
            nova_qtd = row[6]
            qtd_alterada = row[7]
            tipo_mov = row[5]
            qtd_anterior = (nova_qtd + qtd_alterada) if tipo_mov == 'decremento' else (nova_qtd - qtd_alterada)
            relatorio.append(schemas.RelatorioMovimentacaoResponse(data_hora=row[0].strftime('%d/%m/%Y %H:%M:%S'), produto_nome=row[1], cor_variacao=row[2], modelo_celular=row[3], usuario=row[4], tipo_movimento='Venda (Decremento)' if tipo_mov == 'decremento' else 'Reposição (Incremento)', quantidade_anterior=qtd_anterior, nova_quantidade=nova_qtd))
        return relatorio
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao gerar relatório: {e}")

@router.get("/dashboard/vendas-por-dia", response_model=schemas.VendasDiariasResponse)
def get_vendas_resumo_diario(db: Session = Depends(get_db)):
    """
    Retorna o número de vendas (decrementos) para cada um dos últimos 7 dias.
    """
    data_fim = date.today()
    data_inicio = data_fim - timedelta(days=6)
    
    engine = get_engine()
    db_type = engine.dialect.name

    # A forma mais portável é gerar os dias em Python e fazer uma query para cada dia.
    # É menos eficiente que uma única query SQL, mas funciona em ambos os bancos de dados
    # sem sintaxe complexa e para um período de 7 dias a performance é aceitável.
    dias = [(data_inicio + timedelta(days=i)) for i in range(7)]
    labels = [d.strftime("%d/%m") for d in dias]
    vendas_data = []

    query_sql = text("""
        SELECT COUNT(id) 
        FROM historico_estoque 
        WHERE tipo_movimento = 'decremento' AND DATE(data_hora) = :dia
    """)
    try:
        for dia in dias:
            # Para PostgreSQL, data_hora é 'timestamp with time zone'. Para MySQL é 'TIMESTAMP'.
            # A função DATE() funciona em ambos para extrair a data.
            vendas = db.execute(query_sql, {"dia": dia}).scalar()
            vendas_data.append(vendas or 0)
        return schemas.VendasDiariasResponse(labels=labels, data=vendas_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao gerar resumo de vendas: {e}")


@router.get("/dashboard/top-produtos", response_model=List[schemas.TopProdutoResponse])
def get_top_produtos_vendidos(db: Session = Depends(get_db)):
    """
    Retorna os 5 produtos (variações) mais vendidos.
    """
    query = text("""
        SELECT 
            CONCAT(p.nome, ' (', ev.cor, ')') as produto,
            COUNT(h.id) as vendas
        FROM historico_estoque h
        JOIN estoque_variacoes ev ON h.id_variacao_estoque = ev.id
        JOIN produtos p ON ev.id_produto = p.id
        WHERE h.tipo_movimento = 'decremento'
        GROUP BY produto
        ORDER BY vendas DESC
        LIMIT 5;
    """)
    try:
        resultados = db.execute(query).fetchall()
        top_produtos = [schemas.TopProdutoResponse(produto=row[0], vendas=row[1]) for row in resultados]
        return top_produtos
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao buscar top produtos: {e}")