"""Motor de cálculo exato de custos de receitas, CMV e margens de contribuição.

Aritmética estritamente inteira em centavos (int) e frações racionais (Fraction).
Zero float na lógica financeira e de consumo.

LOFRANO TECNOLOGIA.
"""

from dataclasses import dataclass
from fractions import Fraction
import math
from typing import Dict, List

from .domain import FichaTecnica, Insumo, ItemFicha


@dataclass(frozen=True)
class ItemCalculado:
    """Detalhamento contábil e operacional de um ingrediente na ficha técnica."""
    codigo_insumo: str
    nome_insumo: str
    unidade: str
    quantidade_liquida: int
    fator_correcao_num: int
    fator_correcao_den: int
    quantidade_bruta_num: int
    quantidade_bruta_den: int
    custo_frac_num: int
    custo_frac_den: int
    custo_centavos: int  # Teto da fração de centavos

    @property
    def fator_correcao(self) -> Fraction:
        return Fraction(self.fator_correcao_num, self.fator_correcao_den)

    @property
    def quantidade_bruta_frac(self) -> Fraction:
        return Fraction(self.quantidade_bruta_num, self.quantidade_bruta_den)

    @property
    def custo_frac(self) -> Fraction:
        return Fraction(self.custo_frac_num, self.custo_frac_den)


@dataclass(frozen=True)
class FichaCalculada:
    """Ficha técnica com custos consolidados, CMV e margem de contribuição."""
    codigo: str
    nome: str
    categoria: str
    rendimento_porcoes: int
    ingredientes: List[ItemCalculado]
    custo_ingredientes_centavos: int
    custo_embalagem_centavos: int
    custo_total_receita_centavos: int
    custo_porcao_centavos: int
    preco_venda_centavos: int
    cmv_alvo_num: int
    cmv_alvo_den: int
    taxas_impostos_num: int
    taxas_impostos_den: int
    deducao_impostos_centavos: int
    margem_contribuicao_centavos: int
    preco_sugerido_cmv_alvo_centavos: int
    vendas_periodo: int
    faturamento_total_centavos: int
    custo_total_periodo_centavos: int
    margem_total_periodo_centavos: int

    @property
    def cmv_alvo(self) -> Fraction:
        return Fraction(self.cmv_alvo_num, self.cmv_alvo_den)

    @property
    def taxas_impostos(self) -> Fraction:
        return Fraction(self.taxas_impostos_num, self.taxas_impostos_den)

    @property
    def cmv_atual_frac(self) -> Fraction:
        """CMV real atual em fração exata (Custo por Porção / Preço de Venda)."""
        if self.preco_venda_centavos == 0:
            return Fraction(0, 1)
        return Fraction(self.custo_porcao_centavos, self.preco_venda_centavos)

    @property
    def margem_percentual_frac(self) -> Fraction:
        """Margem de contribuição sobre preço de venda."""
        if self.preco_venda_centavos == 0:
            return Fraction(0, 1)
        return Fraction(self.margem_contribuicao_centavos, self.preco_venda_centavos)


def calcular_item_ficha(item: ItemFicha, insumo: Insumo) -> ItemCalculado:
    """Calcula a quantidade bruta consumida e o custo exato em centavos de um ingrediente."""
    # Obter fator de correção (override da receita ou padrão do insumo)
    if item.fator_correcao_override_num is not None and item.fator_correcao_override_den is not None:
        fc = Fraction(item.fator_correcao_override_num, item.fator_correcao_override_den)
    else:
        fc = insumo.fator_correcao

    # Quantidade bruta consumida = quantidade líquida * FC
    qtd_bruta_frac = Fraction(item.quantidade_liquida, 1) * fc

    # Custo exato em centavos = qtd_bruta * (custo_embalagem / quantidade_embalagem)
    custo_frac = qtd_bruta_frac * insumo.custo_unitario_frac

    # Custo em centavos inteiros arredondado para cima (teto para proteção contra subdimensionamento)
    custo_centavos = math.ceil(custo_frac.numerator / custo_frac.denominator)

    return ItemCalculado(
        codigo_insumo=insumo.codigo,
        nome_insumo=insumo.nome,
        unidade=insumo.unidade.value,
        quantidade_liquida=item.quantidade_liquida,
        fator_correcao_num=fc.numerator,
        fator_correcao_den=fc.denominator,
        quantidade_bruta_num=qtd_bruta_frac.numerator,
        quantidade_bruta_den=qtd_bruta_frac.denominator,
        custo_frac_num=custo_frac.numerator,
        custo_frac_den=custo_frac.denominator,
        custo_centavos=custo_centavos,
    )


def calcular_ficha(ficha: FichaTecnica, insumos_map: Dict[str, Insumo]) -> FichaCalculada:
    """Processa a ficha técnica consolidando ingredientes, custos, impostos e preço sugerido."""
    itens_calculados: List[ItemCalculado] = []
    soma_ingredientes_centavos = 0

    for item in ficha.ingredientes:
        insumo = insumos_map[item.codigo_insumo]
        calc = calcular_item_ficha(item, insumo)
        itens_calculados.append(calc)
        soma_ingredientes_centavos += calc.custo_centavos

    custo_total_receita = soma_ingredientes_centavos + ficha.custo_embalagem_centavos

    # Custo da porção unitária = teto(custo_total_receita / rendimento_porcoes)
    custo_porcao = math.ceil(custo_total_receita / ficha.rendimento_porcoes)

    # Dedução de impostos e taxas da venda = teto(preco_venda * taxas_impostos)
    taxa_imposto_frac = ficha.taxas_impostos
    deducao_impostos_centavos = math.ceil(
        (ficha.preco_venda_centavos * taxa_imposto_frac.numerator) / taxa_imposto_frac.denominator
    ) if taxa_imposto_frac > 0 else 0

    # Margem de contribuição unitária = Preço - Custo Porção - Dedução Impostos
    margem_contribuicao = ficha.preco_venda_centavos - custo_porcao - deducao_impostos_centavos

    # Preço sugerido com base no CMV Alvo e taxas
    # Preço * (1 - taxas) * cmv_alvo >= custo_porcao
    # Preço >= custo_porcao / (cmv_alvo * (1 - taxas))
    cmv_alvo = ficha.cmv_alvo
    denominador_preco = cmv_alvo * (Fraction(1, 1) - taxa_imposto_frac)
    if denominador_preco > 0 and custo_porcao > 0:
        frac_preco_sugerido = Fraction(custo_porcao, 1) / denominador_preco
        preco_sugerido = math.ceil(frac_preco_sugerido.numerator / frac_preco_sugerido.denominator)
    else:
        preco_sugerido = custo_porcao

    faturamento_total = ficha.vendas_periodo * ficha.preco_venda_centavos
    custo_total_periodo = ficha.vendas_periodo * custo_porcao
    margem_total_periodo = ficha.vendas_periodo * margem_contribuicao

    return FichaCalculada(
        codigo=ficha.codigo,
        nome=ficha.nome,
        categoria=ficha.categoria,
        rendimento_porcoes=ficha.rendimento_porcoes,
        ingredientes=itens_calculados,
        custo_ingredientes_centavos=soma_ingredientes_centavos,
        custo_embalagem_centavos=ficha.custo_embalagem_centavos,
        custo_total_receita_centavos=custo_total_receita,
        custo_porcao_centavos=custo_porcao,
        preco_venda_centavos=ficha.preco_venda_centavos,
        cmv_alvo_num=ficha.cmv_alvo_num,
        cmv_alvo_den=ficha.cmv_alvo_den,
        taxas_impostos_num=ficha.taxas_impostos_num,
        taxas_impostos_den=ficha.taxas_impostos_den,
        deducao_impostos_centavos=deducao_impostos_centavos,
        margem_contribuicao_centavos=margem_contribuicao,
        preco_sugerido_cmv_alvo_centavos=preco_sugerido,
        vendas_periodo=ficha.vendas_periodo,
        faturamento_total_centavos=faturamento_total,
        custo_total_periodo_centavos=custo_total_periodo,
        margem_total_periodo_centavos=margem_total_periodo,
    )
