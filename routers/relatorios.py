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

@router.get("/dashboard/metricas-financeiras", response_model=schemas.MetricasFinanceirasResponse)
def get_metricas_financeiras(db: Session = Depends(get_db)):
    """
    Calcula métricas financeiras chave para os últimos 7 dias.
    - Faturação Total (Receita)
    - Lucro Total
    - Total de Vendas (transações de decremento)
    - Ticket Médio
    """
    data_fim = date.today()
    data_inicio = data_fim - timedelta(days=6)
    datetime_inicio = datetime.combine(data_inicio, time.min)
    datetime_fim = datetime.combine(data_fim, time.max)

    query = text("""
        SELECT
            SUM(h.preco_venda_momento * h.quantidade_alterada) AS faturacao_total,
            SUM((h.preco_venda_momento - COALESCE(h.preco_custo_momento, 0)) * h.quantidade_alterada) AS lucro_total,
            COUNT(h.id) AS total_vendas
        FROM historico_estoque h
        WHERE h.tipo_movimento = 'decremento'
          AND h.data_hora BETWEEN :inicio AND :fim
    """)

    try:
        resultado = db.execute(query, {"inicio": datetime_inicio, "fim": datetime_fim}).first()
        
        faturacao = resultado[0] or 0.0
        lucro = resultado[1] or 0.0
        vendas = resultado[2] or 0

        ticket_medio = faturacao / vendas if vendas > 0 else 0.0

        return schemas.MetricasFinanceirasResponse(
            faturacao_total=faturacao,
            lucro_total=lucro,
            total_vendas=vendas,
            ticket_medio=ticket_medio
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao calcular métricas financeiras: {e}")

@router.get("/dashboard/vendas-por-dia", response_model=schemas.VendasDiariasResponse)
def get_vendas_resumo_diario(db: Session = Depends(get_db)):
    """
    Retorna a FATURAÇÃO (receita) para cada um dos últimos 7 dias.
    """
    data_fim = date.today()
    data_inicio = data_fim - timedelta(days=6)
    
    dias = [(data_inicio + timedelta(days=i)) for i in range(7)]
    labels = [d.strftime("%d/%m") for d in dias]
    faturacao_data = []

    query_sql = text("""
        SELECT SUM(preco_venda_momento * quantidade_alterada)
        FROM historico_estoque h
        WHERE tipo_movimento = 'decremento' AND DATE(data_hora) = :dia
    """)
    try:
        for dia in dias:
            faturacao_dia = db.execute(query_sql, {"dia": dia}).scalar()
            faturacao_data.append(faturacao_dia or 0.0)
        return schemas.VendasDiariasResponse(labels=labels, data=faturacao_data)
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