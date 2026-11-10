"""Definições de erros e códigos canônicos para precificação e engenharia de cardápio.

LOFRANO TECNOLOGIA - Padrão de Engenharia de Software.
"""

from typing import Optional

ERR_VALOR_INVALIDO = "VALOR_INVALIDO"
ERR_CODIGO_DUPLICADO = "CODIGO_DUPLICADO"
ERR_INSUMO_NAO_ENCONTRADO = "INSUMO_NAO_ENCONTRADO"
ERR_QUANTIDADE_INVALIDA = "QUANTIDADE_INVALIDA"
ERR_CATEGORIA_VAZIA = "CATEGORIA_VAZIA"
ERR_CARDAPIO_VAZIO = "CARDAPIO_VAZIO"
ERR_JSON_INVALIDO = "JSON_INVALIDO"
ERR_FLOAT_PROIBIDO = "FLOAT_PROIBIDO"
ERR_CHAVE_DUPLICADA = "CHAVE_DUPLICADA"
ERR_BOM_PROIBIDO = "BOM_PROIBIDO"
ERR_PROFUNDIDADE_EXCEDIDA = "PROFUNDIDADE_EXCEDIDA"
ERR_ARQUIVO_EXISTENTE = "ARQUIVO_EXISTENTE"


class PrecificacaoError(Exception):
    """Exceção base para todas as falhas de precificação e análise de cardápio."""

    def __init__(self, mensagem: str, codigo: str = ERR_VALOR_INVALIDO, detalhe: Optional[str] = None):
        super().__init__(mensagem)
        self.mensagem = mensagem
        self.codigo = codigo
        self.detalhe = detalhe

    def __str__(self) -> str:
        if self.detalhe:
            return f"[{self.codigo}] {self.mensagem} — {self.detalhe}"
        return f"[{self.codigo}] {self.mensagem}"


class ErroValidacao(PrecificacaoError):
    """Erro emitido quando dados de domínio violam restrições do negócio."""
    pass


class ErroCodec(PrecificacaoError):
    """Erro emitido durante parsing ou serialização de arquivos canônicos."""
    pass
