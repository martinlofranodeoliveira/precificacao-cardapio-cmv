"""Matriz de Engenharia de Cardápio (Kasavana & Smith / Matriz de Miller).

Classificação determinística dos itens do cardápio em quatro quadrantes de rentabilidade e popularidade:
- ESTRELA (Star): Alta Popularidade e Alta Margem
- BURRO_DE_CARGA (Plowhorse / Cavalo de Batalha): Alta Popularidade e Baixa Margem
- QUEBRA_CABECA (Puzzle / Enigma): Baixa Popularidade e Alta Margem
- CAO (Dog / Abacaxi): Baixa Popularidade e Baixa Margem

Aritmética estritamente inteira e racional exata (zero float).
LOFRANO TECNOLOGIA.
"""

from dataclasses import dataclass
from enum import Enum
from fractions import Fraction
from typing import Dict, List, Optional

from .calculator import FichaCalculada


class Quadrante(str, Enum):
    """Quadrantes da matriz clássica de engenharia de cardápio."""
    ESTRELA = "ESTRELA"
    BURRO_DE_CARGA = "BURRO_DE_CARGA"
    QUEBRA_CABECA = "QUEBRA_CABECA"
    CAO = "CAO"


RECOMENDACOES_ESTRATEGICAS: Dict[Quadrante, str] = {
    Quadrante.ESTRELA: (
        "Item altamente lucrativo e popular. Manter rigorosamente o padrão de ficha técnica, "
        "dar destaque visual no cardápio e assegurar disponibilidade contínua de insumos."
    ),
    Quadrante.BURRO_DE_CARGA: (
        "Item com alto volume de vendas, mas margem abaixo da média. Testar reajuste gradual de preço, "
        "renegociar preços de insumos-chave com fornecedores ou otimizar porções com menor desperdício."
    ),
    Quadrante.QUEBRA_CABECA: (
        "Item com excelente margem unitária, porém baixa saída. Reposicionar em área nobre do cardápio, "
        "treinar equipe de salão para venda sugestiva ou elaborar ações promocionais/combos."
    ),
    Quadrante.CAO: (
        "Item de baixa saída e baixa lucratividade. Avaliar reformulação da receita, aumento drástico de preço "
        "ou descontinuação imediata para desocupar estoque e reduzir complexidade operacional."
    ),
}


@dataclass(frozen=True)
class ItemMatriz:
    """Classificação de um prato na matriz de rentabilidade."""
    ficha: FichaCalculada
    quadrante: Quadrante
    alta_popularidade: bool
    alta_margem: bool
    participacao_vendas_frac: Fraction  # vendas_item / vendas_totais
    limiar_popularidade_frac: Fraction  # (7/10) * (1/N)
    margem_media_referencia_centavos: int
    recomendacao: str


@dataclass(frozen=True)
class AnaliseCardapio:
    """Resultado consolidado da engenharia de cardápio para o estabelecimento."""
    estabelecimento: str
    periodo: str
    itens: List[ItemMatriz]
    total_fichas: int
    total_porcoes_vendidas: int
    faturamento_total_centavos: int
    custo_total_centavos: int
    margem_total_centavos: int
    cmv_medio_ponderado_frac: Fraction
    contagem_quadrantes: Dict[Quadrante, int]

    @property
    def margem_ponderada_percentual_frac(self) -> Fraction:
        if self.faturamento_total_centavos == 0:
            return Fraction(0, 1)
        return Fraction(self.margem_total_centavos, self.faturamento_total_centavos)


def classificar_cardapio(
    estabelecimento: str,
    periodo: str,
    fichas_calculadas: List[FichaCalculada],
    fator_popularidade_num: int = 7,
    fator_popularidade_den: int = 10,
) -> AnaliseCardapio:
    """Executa a classificação determinística de todos os itens do cardápio."""
    if not fichas_calculadas:
        raise ValueError("A lista de fichas calculadas não pode ser vazia.")

    n_itens = len(fichas_calculadas)
    total_vendas = sum(f.vendas_periodo for f in fichas_calculadas)
    faturamento_total = sum(f.faturamento_total_centavos for f in fichas_calculadas)
    custo_total = sum(f.custo_total_periodo_centavos for f in fichas_calculadas)
    margem_total = sum(f.margem_total_periodo_centavos for f in fichas_calculadas)

    # Limiar de popularidade Kasavana & Smith: (fator_popularidade / N)
    # Ex: (7/10) * (1/N) = 7 / (10 * N)
    limiar_pop_frac = Fraction(fator_popularidade_num, fator_popularidade_den * n_itens)

    # Margem de contribuição de referência:
    # Se há vendas no período, usa a média ponderada pelas vendas: sum(v_i * mc_i) / sum(v_i)
    # Se não há vendas (total_vendas == 0), usa a média simples: sum(mc_i) / N
    if total_vendas > 0:
        soma_margens_ponderadas = sum(f.vendas_periodo * f.margem_contribuicao_centavos for f in fichas_calculadas)
        margem_referencia_frac = Fraction(soma_margens_ponderadas, total_vendas)
        margem_referencia_centavos = round(soma_margens_ponderadas / total_vendas)
    else:
        soma_margens_simples = sum(f.margem_contribuicao_centavos for f in fichas_calculadas)
        margem_referencia_frac = Fraction(soma_margens_simples, n_itens)
        margem_referencia_centavos = round(soma_margens_simples / n_itens)

    itens_matriz: List[ItemMatriz] = []
    contagem: Dict[Quadrante, int] = {
        Quadrante.ESTRELA: 0,
        Quadrante.BURRO_DE_CARGA: 0,
        Quadrante.QUEBRA_CABECA: 0,
        Quadrante.CAO: 0,
    }

    # Desempate estável por categoria e código
    fichas_ordenadas = sorted(fichas_calculadas, key=lambda f: (f.categoria, f.codigo))

    for f in fichas_ordenadas:
        # Avaliação de popularidade:
        if total_vendas > 0:
            part_vendas = Fraction(f.vendas_periodo, total_vendas)
            alta_pop = part_vendas >= limiar_pop_frac
        else:
            part_vendas = Fraction(0, 1)
            alta_pop = False

        # Avaliação de margem de contribuição:
        alta_margem = Fraction(f.margem_contribuicao_centavos, 1) >= margem_referencia_frac

        if alta_pop and alta_margem:
            quad = Quadrante.ESTRELA
        elif alta_pop and not alta_margem:
            quad = Quadrante.BURRO_DE_CARGA
        elif not alta_pop and alta_margem:
            quad = Quadrante.QUEBRA_CABECA
        else:
            quad = Quadrante.CAO

        contagem[quad] += 1
        recomendacao = RECOMENDACOES_ESTRATEGICAS[quad]

        itens_matriz.append(
            ItemMatriz(
                ficha=f,
                quadrante=quad,
                alta_popularidade=alta_pop,
                alta_margem=alta_margem,
                participacao_vendas_frac=part_vendas,
                limiar_popularidade_frac=limiar_pop_frac,
                margem_media_referencia_centavos=margem_referencia_centavos,
                recomendacao=recomendacao,
            )
        )

    # CMV médio ponderado global = custo total consolidado / faturamento total consolidado
    if faturamento_total > 0:
        cmv_medio_ponderado = Fraction(custo_total, faturamento_total)
    else:
        cmv_medio_ponderado = Fraction(0, 1)

    return AnaliseCardapio(
        estabelecimento=estabelecimento,
        periodo=periodo,
        itens=itens_matriz,
        total_fichas=n_itens,
        total_porcoes_vendidas=total_vendas,
        faturamento_total_centavos=faturamento_total,
        custo_total_centavos=custo_total,
        margem_total_centavos=margem_total,
        cmv_medio_ponderado_frac=cmv_medio_ponderado,
        contagem_quadrantes=contagem,
    )
