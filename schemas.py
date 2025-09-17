# schemas.py

from pydantic import BaseModel, field_validator
import re
from typing import List, Optional, Literal

# --- Modelos Pydantic ---
class MarcaBase(BaseModel):
    nome: str
    @field_validator('nome')
    def trim_whitespace(cls, v): return v.strip()

class MarcaResponse(BaseModel):
    id: int
    nome: str

class ModeloBase(BaseModel):
    nome_modelo: str
    id_marca: int
    @field_validator('nome_modelo')
    def trim_whitespace(cls, v): return v.strip()

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
    @field_validator('nome', 'tipo', 'material')
    def trim_whitespace(cls, v):
        if v is not None: return v.strip()
        return v

class ProdutoResponse(BaseModel):
    id: int
    nome: str
    tipo: str
    material: Optional[str] = None
    preco_venda: float
    modelo_celular: str

class ProdutoAdminResponse(ProdutoBase):
    id: int

class EstoqueVariacaoBase(BaseModel):
    id_produto: int
    cor: str
    quantidade: int
    disponivel_encomenda: bool = True
    @field_validator('cor')
    def trim_whitespace(cls, v): return v.strip()

class EstoqueVariacaoResponse(BaseModel):
    id: int
    cor: str
    quantidade: int
    disponivel_encomenda: bool
    url_foto: Optional[str] = None
    produto_nome: str
    modelo_celular: str
    preco_venda: float

class FornecedorBase(BaseModel):
    nome: str
    contato_telefone: Optional[str] = None
    contato_email: Optional[str] = None
    @field_validator('nome', 'contato_telefone', 'contato_email')
    def trim_whitespace(cls, v):
        if v is not None: return v.strip()
        return v
    @field_validator('contato_telefone')
    def validar_telefone(cls, v):
        if v is None or v == '': return v
        regex = re.compile(r'^\(?\d{2}\)?[\s-]?\d{4,5}-?\d{4}$')
        if not regex.match(v): raise ValueError('Número de telefone inválido.')
        return v

class FornecedorResponse(BaseModel):
    id: int
    nome: str
    contato_telefone: Optional[str] = None
    contato_email: Optional[str] = None

class Token(BaseModel):
    access_token: str
    token_type: str

class AssociacaoProdutoFornecedor(BaseModel):
    id_fornecedor: int

class RelatorioMovimentacaoResponse(BaseModel):
    data_hora: str
    produto_nome: str
    cor_variacao: str
    modelo_celular: str
    usuario: str
    tipo_movimento: Literal['Venda (Decremento)', 'Reposição (Incremento)']
    quantidade_anterior: int
    nova_quantidade: int

class VendasDiariasResponse(BaseModel):
    labels: List[str]
    data: List[int]

class TopProdutoResponse(BaseModel):
    produto: str
    vendas: int

# Os modelos para a página pública de detalhes do produto podem ser movidos para cá também
# se forem usados em mais algum lugar, ou podem ficar em main.py se forem muito específicos.
# Por agora, vamos mantê-los em main.py para simplificar.