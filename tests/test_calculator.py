"""Testes unitários do motor de cálculo de custos, CMV e margem de contribuição.

LOFRANO TECNOLOGIA.
"""

from fractions import Fraction
import unittest

from precificacao_cardapio.calculator import calcular_ficha, calcular_item_ficha
from precificacao_cardapio.domain import FichaTecnica, Insumo, ItemFicha, UnidadeMedida


class TestCalculator(unittest.TestCase):
    def setUp(self) -> None:
        self.insumo_trigo = Insumo("INS-TRIGO", "Farinha de Trigo", UnidadeMedida.GRAMA, 1000, 500)
        self.insumo_carne = Insumo("INS-CARNE", "Carne Bovina", UnidadeMedida.GRAMA, 1000, 4000, 125, 100)
        self.insumo_oleo = Insumo("INS-OLEO", "Azeite de Oliva", UnidadeMedida.MILILITRO, 500, 2500)
        self.insumos_map = {
            "INS-TRIGO": self.insumo_trigo,
            "INS-CARNE": self.insumo_carne,
            "INS-OLEO": self.insumo_oleo,
        }

    def test_calcular_item_sem_perda(self) -> None:
        item = ItemFicha("INS-TRIGO", 200)
        calc = calcular_item_ficha(item, self.insumo_trigo)
        # 200g * (500 centavos / 1000g) = 100 centavos
        self.assertEqual(calc.quantidade_liquida, 200)
        self.assertEqual(calc.quantidade_bruta_frac, Fraction(200, 1))
        self.assertEqual(calc.custo_frac, Fraction(100, 1))
        self.assertEqual(calc.custo_centavos, 100)

    def test_calcular_item_com_fator_correcao(self) -> None:
        # Carne com FC = 125/100 (perda de 20% na limpeza)
        # Qtd liquida = 200g -> Qtd bruta = 200 * 125/100 = 250g
        # Custo: 250g * (4000 centavos / 1000g) = 1000 centavos
        item = ItemFicha("INS-CARNE", 200)
        calc = calcular_item_ficha(item, self.insumo_carne)
        self.assertEqual(calc.quantidade_bruta_frac, Fraction(250, 1))
        self.assertEqual(calc.custo_frac, Fraction(1000, 1))
        self.assertEqual(calc.custo_centavos, 1000)

    def test_calcular_item_com_arredondamento_teto(self) -> None:
        # Insumo de R$ 10,00 (1000 centavos) por 300g -> custo unit = 10/3 centavos/g
        # Consumo de 10g -> 100/3 centavos = 33.333... centavos
        # Teto (ceil) deve resultar em 34 centavos
        ins = Insumo("INS-ESPECIFICO", "Item", UnidadeMedida.GRAMA, 300, 1000)
        item = ItemFicha("INS-ESPECIFICO", 10)
        calc = calcular_item_ficha(item, ins)
        self.assertEqual(calc.custo_frac, Fraction(100, 3))
        self.assertEqual(calc.custo_centavos, 34)

    def test_calcular_item_override_fc(self) -> None:
        # Override de FC para 150/100
        item = ItemFicha("INS-CARNE", 200, 150, 100)
        calc = calcular_item_ficha(item, self.insumo_carne)
        # 200 * 150/100 = 300g bruta
        # 300g * 4 centavos/g = 1200 centavos
        self.assertEqual(calc.quantidade_bruta_frac, Fraction(300, 1))
        self.assertEqual(calc.custo_centavos, 1200)

    def test_calcular_ficha_completa(self) -> None:
        ficha = FichaTecnica(
            codigo="PRAT-BIFE",
            nome="Bife com Molho",
            categoria="Pratos",
            rendimento_porcoes=1,
            ingredientes=[
                ItemFicha("INS-CARNE", 200),  # custo: 1000
                ItemFicha("INS-OLEO", 20),    # 20 * 2500/500 = 100
            ],
            custo_embalagem_centavos=50,
            preco_venda_centavos=3000,
            vendas_periodo=50,
            cmv_alvo_num=30,
            cmv_alvo_den=100,
            taxas_impostos_num=10,
            taxas_impostos_den=100,
        )

        calc = calcular_ficha(ficha, self.insumos_map)
        self.assertEqual(calc.custo_ingredientes_centavos, 1100)
        self.assertEqual(calc.custo_embalagem_centavos, 50)
        self.assertEqual(calc.custo_total_receita_centavos, 1150)
        self.assertEqual(calc.custo_porcao_centavos, 1150)

        # Taxas de 10% sobre 3000 centavos = 300 centavos
        self.assertEqual(calc.deducao_impostos_centavos, 300)
        # Margem de contribuição: 3000 - 1150 - 300 = 1550 centavos
        self.assertEqual(calc.margem_contribuicao_centavos, 1550)

        # CMV real: 1150 / 3000 = 23/60 (~38.3%)
        self.assertEqual(calc.cmv_atual_frac, Fraction(1150, 3000))

        # Preço sugerido para CMV 30% com taxas de 10%:
        # Preço >= custo_porcao / (cmv_alvo * (1 - taxas))
        # Denominador: (30/100) * (90/100) = 27/100
        # Preço = ceil(1150 / (27/100)) = ceil(115000 / 27) = ceil(4259.259) = 4260 centavos
        self.assertEqual(calc.preco_sugerido_cmv_alvo_centavos, 4260)

        # Totais do período (50 vendas)
        self.assertEqual(calc.faturamento_total_centavos, 50 * 3000)
        self.assertEqual(calc.custo_total_periodo_centavos, 50 * 1150)
        self.assertEqual(calc.margem_total_periodo_centavos, 50 * 1550)

    def test_calcular_ficha_rendimento_multiplo(self) -> None:
        # Ficha com rendimento de 4 porções
        ficha = FichaTecnica(
            codigo="PRAT-TORTA",
            nome="Torta Salgada",
            categoria="Tortas",
            rendimento_porcoes=4,
            ingredientes=[
                ItemFicha("INS-TRIGO", 600),  # custo: 300
                ItemFicha("INS-CARNE", 400),  # 400 * 1.25 * 4 = 2000
            ],
            custo_embalagem_centavos=100,  # total receita = 2400
            preco_venda_centavos=1200,      # preço por porção
            vendas_periodo=20,
        )
        calc = calcular_ficha(ficha, self.insumos_map)
        # Custo por porção = 2400 / 4 = 600 centavos
        self.assertEqual(calc.custo_porcao_centavos, 600)
        self.assertEqual(calc.margem_contribuicao_centavos, 600)


    def test_calcular_ficha_margem_negativa(self) -> None:
        # Preço de venda menor que custo -> margem negativa
        ficha = FichaTecnica(
            codigo="PRAT-PREJUIZO",
            nome="Prato Deficitário",
            categoria="Geral",
            rendimento_porcoes=1,
            ingredientes=[ItemFicha("INS-CARNE", 500)],  # custo: 2500
            custo_embalagem_centavos=100,               # custo total = 2600
            preco_venda_centavos=2000,                  # venda por 2000
            vendas_periodo=5,
        )
        calc = calcular_ficha(ficha, self.insumos_map)
        self.assertEqual(calc.custo_porcao_centavos, 2600)
        self.assertEqual(calc.margem_contribuicao_centavos, -600)
        self.assertEqual(calc.margem_total_periodo_centavos, -3000)

    def test_calcular_ficha_preco_zero(self) -> None:
        # Ficha degustação / cortesia com preço zero
        ficha = FichaTecnica(
            codigo="PRAT-CORTESIA",
            nome="Degustação",
            categoria="Cortesia",
            rendimento_porcoes=1,
            ingredientes=[ItemFicha("INS-TRIGO", 100)],  # custo = 50 centavos
            custo_embalagem_centavos=0,
            preco_venda_centavos=0,
            vendas_periodo=10,
            cmv_alvo_num=30,
            cmv_alvo_den=100,
        )
        calc = calcular_ficha(ficha, self.insumos_map)
        self.assertEqual(calc.cmv_atual_frac, Fraction(0, 1))
        self.assertEqual(calc.margem_percentual_frac, Fraction(0, 1))
        # Preço sugerido para 30% de CMV com custo 50: ceil(50 / 0.30) = 167 centavos
        self.assertEqual(calc.preco_sugerido_cmv_alvo_centavos, 167)


if __name__ == "__main__":
    unittest.main()
