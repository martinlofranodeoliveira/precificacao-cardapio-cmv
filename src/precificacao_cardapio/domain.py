"""Modelos de domínio para fichas técnicas gastronômicas e engenharia de cardápio.

Todos os valores monetários são expressos estritamente em centavos inteiros (int)
e grandezas físicas em unidades discretas (gramas, mililitros, unidades inteiras).
Zero ponto flutuante (float) na representação e nas operações de negócio.

LOFRANO TECNOLOGIA.
"""

from dataclasses import dataclass, field
from enum import Enum
from fractions import Fraction
from typing import Dict, List, Optional

from .errors import (
    ERR_CARDAPIO_VAZIO,
    ERR_CATEGORIA_VAZIA,
    ERR_CODIGO_DUPLICADO,
    ERR_INSUMO_NAO_ENCONTRADO,
    ERR_QUANTIDADE_INVALIDA,
    ERR_VALOR_INVALIDO,
    ErroValidacao,
)


class UnidadeMedida(str, Enum):
    """Unidades de medida padrão para insumos gastronômicos."""
    GRAMA = "g"
    MILILITRO = "ml"
    UNIDADE = "un"


@dataclass(frozen=True)
class Insumo:
    """Cadastro de insumo adquirido pelo estabelecimento."""
    codigo: str
    nome: str
    unidade: UnidadeMedida
    quantidade_embalagem: int  # > 0 (em g, ml ou unidades)
    custo_embalagem_centavos: int  # >= 0 (em centavos de Real)
    fator_correcao_num: int = 1  # Numerador do FC (padrão 1/1 = 1.0)
    fator_correcao_den: int = 1  # Denominador do FC (> 0)

    def __post_init__(self) -> None:
        if not self.codigo or not self.codigo.strip():
            raise ErroValidacao("Código do insumo não pode ser vazio.", ERR_VALOR_INVALIDO)
        if not self.nome or not self.nome.strip():
            raise ErroValidacao("Nome do insumo não pode ser vazio.", ERR_VALOR_INVALIDO)
        if not isinstance(self.unidade, UnidadeMedida):
            raise ErroValidacao(f"Unidade inválida para o insumo {self.codigo}: {self.unidade}.", ERR_VALOR_INVALIDO)
        if not isinstance(self.quantidade_embalagem, int) or self.quantidade_embalagem <= 0:
            raise ErroValidacao(
                f"Quantidade da embalagem do insumo {self.codigo} deve ser inteiro positivo.",
                ERR_QUANTIDADE_INVALIDA,
            )
        if not isinstance(self.custo_embalagem_centavos, int) or self.custo_embalagem_centavos < 0:
            raise ErroValidacao(
                f"Custo da embalagem do insumo {self.codigo} deve ser inteiro não-negativo em centavos.",
                ERR_VALOR_INVALIDO,
            )
        if not isinstance(self.fator_correcao_num, int) or self.fator_correcao_num <= 0:
            raise ErroValidacao(
                f"Numerador do fator de correção do insumo {self.codigo} deve ser inteiro positivo.",
                ERR_VALOR_INVALIDO,
            )
        if not isinstance(self.fator_correcao_den, int) or self.fator_correcao_den <= 0:
            raise ErroValidacao(
                f"Denominador do fator de correção do insumo {self.codigo} deve ser inteiro positivo.",
                ERR_VALOR_INVALIDO,
            )
        if Fraction(self.fator_correcao_num, self.fator_correcao_den) < 1:
            raise ErroValidacao(
                f"Fator de correção (FC = Bruto / Líquido) do insumo {self.codigo} não pode ser menor que 1/1.",
                ERR_VALOR_INVALIDO,
            )

    @property
    def fator_correcao(self) -> Fraction:
        return Fraction(self.fator_correcao_num, self.fator_correcao_den)

    @property
    def custo_unitario_frac(self) -> Fraction:
        """Custo unitário exato em fração de centavos por g, ml ou un."""
        return Fraction(self.custo_embalagem_centavos, self.quantidade_embalagem)


@dataclass(frozen=True)
class ItemFicha:
    """Componente insumo de uma ficha técnica."""
    codigo_insumo: str
    quantidade_liquida: int  # > 0 (em g, ml ou un)
    fator_correcao_override_num: Optional[int] = None
    fator_correcao_override_den: Optional[int] = None

    def __post_init__(self) -> None:
        if not self.codigo_insumo or not self.codigo_insumo.strip():
            raise ErroValidacao("Código do insumo na ficha não pode ser vazio.", ERR_VALOR_INVALIDO)
        if not isinstance(self.quantidade_liquida, int) or self.quantidade_liquida <= 0:
            raise ErroValidacao(
                f"Quantidade líquida do ingrediente {self.codigo_insumo} deve ser inteiro positivo.",
                ERR_QUANTIDADE_INVALIDA,
            )
        if self.fator_correcao_override_num is not None:
            if not isinstance(self.fator_correcao_override_num, int) or self.fator_correcao_override_num <= 0:
                raise ErroValidacao(
                    f"Numerador do FC override de {self.codigo_insumo} deve ser inteiro positivo.",
                    ERR_VALOR_INVALIDO,
                )
            if self.fator_correcao_override_den is None or not isinstance(self.fator_correcao_override_den, int) or self.fator_correcao_override_den <= 0:
                raise ErroValidacao(
                    f"Denominador do FC override de {self.codigo_insumo} deve ser inteiro positivo.",
                    ERR_VALOR_INVALIDO,
                )
            if Fraction(self.fator_correcao_override_num, self.fator_correcao_override_den) < 1:
                raise ErroValidacao(
                    f"FC override de {self.codigo_insumo} não pode ser menor que 1/1.",
                    ERR_VALOR_INVALIDO,
                )


@dataclass(frozen=True)
class FichaTecnica:
    """Ficha técnica de um item de cardápio."""
    codigo: str
    nome: str
    categoria: str
    rendimento_porcoes: int  # > 0 (padrão 1)
    ingredientes: List[ItemFicha]
    custo_embalagem_centavos: int  # >= 0
    preco_venda_centavos: int  # >= 0
    vendas_periodo: int  # >= 0
    cmv_alvo_num: int = 30  # Alvo de CMV (ex: 30/100 = 30%)
    cmv_alvo_den: int = 100
    taxas_impostos_num: int = 0  # Percentual estimado de impostos e taxas sobre venda
    taxas_impostos_den: int = 100

    def __post_init__(self) -> None:
        if not self.codigo or not self.codigo.strip():
            raise ErroValidacao("Código da ficha técnica não pode ser vazio.", ERR_VALOR_INVALIDO)
        if not self.nome or not self.nome.strip():
            raise ErroValidacao("Nome da ficha técnica não pode ser vazio.", ERR_VALOR_INVALIDO)
        if not self.categoria or not self.categoria.strip():
            raise ErroValidacao(f"Categoria da ficha {self.codigo} não pode ser vazia.", ERR_CATEGORIA_VAZIA)
        if not isinstance(self.rendimento_porcoes, int) or self.rendimento_porcoes <= 0:
            raise ErroValidacao(
                f"Rendimento de porções da ficha {self.codigo} deve ser inteiro positivo.",
                ERR_VALOR_INVALIDO,
            )
        if not self.ingredientes:
            raise ErroValidacao(f"Ficha técnica {self.codigo} deve possuir ao menos 1 ingrediente.", ERR_VALOR_INVALIDO)
        if not isinstance(self.custo_embalagem_centavos, int) or self.custo_embalagem_centavos < 0:
            raise ErroValidacao(
                f"Custo de embalagem da ficha {self.codigo} deve ser inteiro não-negativo.",
                ERR_VALOR_INVALIDO,
            )
        if not isinstance(self.preco_venda_centavos, int) or self.preco_venda_centavos < 0:
            raise ErroValidacao(
                f"Preço de venda da ficha {self.codigo} deve ser inteiro não-negativo em centavos.",
                ERR_VALOR_INVALIDO,
            )
        if not isinstance(self.vendas_periodo, int) or self.vendas_periodo < 0:
            raise ErroValidacao(
                f"Vendas do período da ficha {self.codigo} deve ser inteiro não-negativo.",
                ERR_VALOR_INVALIDO,
            )
        if not isinstance(self.cmv_alvo_num, int) or self.cmv_alvo_num <= 0:
            raise ErroValidacao(f"Numerador do CMV alvo da ficha {self.codigo} deve ser > 0.", ERR_VALOR_INVALIDO)
        if not isinstance(self.cmv_alvo_den, int) or self.cmv_alvo_den <= 0:
            raise ErroValidacao(f"Denominador do CMV alvo da ficha {self.codigo} deve ser > 0.", ERR_VALOR_INVALIDO)
        if not isinstance(self.taxas_impostos_num, int) or self.taxas_impostos_num < 0:
            raise ErroValidacao(f"Numerador de taxas/impostos da ficha {self.codigo} deve ser >= 0.", ERR_VALOR_INVALIDO)
        if not isinstance(self.taxas_impostos_den, int) or self.taxas_impostos_den <= 0:
            raise ErroValidacao(f"Denominador de taxas/impostos da ficha {self.codigo} deve ser > 0.", ERR_VALOR_INVALIDO)

    @property
    def cmv_alvo(self) -> Fraction:
        return Fraction(self.cmv_alvo_num, self.cmv_alvo_den)

    @property
    def taxas_impostos(self) -> Fraction:
        return Fraction(self.taxas_impostos_num, self.taxas_impostos_den)


@dataclass(frozen=True)
class Cardapio:
    """Conjunto completo de insumos cadastrados e fichas técnicas para análise."""
    nome_estabelecimento: str
    periodo: str
    insumos: Dict[str, Insumo]
    fichas: List[FichaTecnica]

    def __post_init__(self) -> None:
        if not self.nome_estabelecimento or not self.nome_estabelecimento.strip():
            raise ErroValidacao("Nome do estabelecimento não pode ser vazio.", ERR_VALOR_INVALIDO)
        if not self.periodo or not self.periodo.strip():
            raise ErroValidacao("Período de referência não pode ser vazio.", ERR_VALOR_INVALIDO)
        if not self.insumos:
            raise ErroValidacao("O cardápio deve possuir ao menos 1 insumo cadastrado.", ERR_VALOR_INVALIDO)
        if not self.fichas:
            raise ErroValidacao("O cardápio deve possuir ao menos 1 ficha técnica.", ERR_CARDAPIO_VAZIO)

        # Validar unicidade de códigos de insumos
        if len(self.insumos) != len(set(self.insumos.keys())):
            raise ErroValidacao("Existem códigos duplicados no dicionário de insumos.", ERR_CODIGO_DUPLICADO)

        # Validar unicidade de códigos de fichas técnicas
        codigos_fichas = [f.codigo for f in self.fichas]
        if len(codigos_fichas) != len(set(codigos_fichas)):
            duplicados = [c for c in codigos_fichas if codigos_fichas.count(c) > 1]
            raise ErroValidacao(
                f"Existem fichas técnicas com códigos duplicados: {set(duplicados)}.",
                ERR_CODIGO_DUPLICADO,
            )

        # Validar se todos os ingredientes existem no cadastro de insumos
        for ficha in self.fichas:
            for item in ficha.ingredientes:
                if item.codigo_insumo not in self.insumos:
                    raise ErroValidacao(
                        f"Insumo '{item.codigo_insumo}' referenciado na ficha '{ficha.codigo}' não encontrado no cadastro.",
                        ERR_INSUMO_NAO_ENCONTRADO,
                    )
