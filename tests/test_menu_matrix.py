"""Testes unitários da Matriz de Engenharia de Cardápio (Kasavana & Smith / Miller).

LOFRANO TECNOLOGIA.
"""

from fractions import Fraction
import unittest

from precificacao_cardapio.calculator import FichaCalculada, ItemCalculado
from precificacao_cardapio.menu_matrix import (
    Quadrante,
    classificar_cardapio,
)


class TestMenuMatrix(unittest.TestCase):
    def _criar_ficha_dummy(
        self,
        codigo: str,
        vendas: int,
        preco: int,
        custo_porcao: int,
        margem: int,
    ) -> FichaCalculada:
        return FichaCalculada(
            codigo=codigo,
            nome=f"Prato {codigo}",
            categoria="Geral",
            rendimento_porcoes=1,
            ingredientes=[],
            custo_ingredientes_centavos=custo_porcao,
            custo_embalagem_centavos=0,
            custo_total_receita_centavos=custo_porcao,
            custo_porcao_centavos=custo_porcao,
            preco_venda_centavos=preco,
            cmv_alvo_num=30,
            cmv_alvo_den=100,
            taxas_impostos_num=0,
            taxas_impostos_den=100,
            deducao_impostos_centavos=0,
            margem_contribuicao_centavos=margem,
            preco_sugerido_cmv_alvo_centavos=preco,
            vendas_periodo=vendas,
            faturamento_total_centavos=vendas * preco,
            custo_total_periodo_centavos=vendas * custo_porcao,
            margem_total_periodo_centavos=vendas * margem,
        )

    def test_classificacao_quatro_quadrantes(self) -> None:
        # Criamos 4 pratos para que N = 4.
        # Limiar de popularidade Kasavana & Smith: 7 / (10 * 4) = 7/40 = 17.5%
        # Vendas totais = 100
        # Prato 1: 30 vendas (> 17.5%), Margem 4000 (> ref) -> ESTRELA
        # Prato 2: 30 vendas (> 17.5%), Margem 1000 (< ref) -> BURRO DE CARGA
        # Prato 3: 10 vendas (< 17.5%), Margem 4000 (> ref) -> QUEBRA CABEÇA
        # Prato 4: 10 vendas (< 17.5%), Margem 1000 (< ref) -> CÃO
        # Margem ponderada = (30*4000 + 30*1000 + 10*4000 + 10*1000) / 80
        # = (120000 + 30000 + 40000 + 10000) / 80 = 200000 / 80 = 2500 centavos
        f_estrela = self._criar_ficha_dummy("P1", 30, 5000, 1000, 4000)
        f_burro = self._criar_ficha_dummy("P2", 30, 2000, 1000, 1000)
        f_puzzle = self._criar_ficha_dummy("P3", 10, 5000, 1000, 4000)
        f_cao = self._criar_ficha_dummy("P4", 10, 2000, 1000, 1000)

        analise = classificar_cardapio(
            "Restaurante Teste",
            "Outubro/2026",
            [f_estrela, f_burro, f_puzzle, f_cao],
        )

        mapa_quadrantes = {it.ficha.codigo: it.quadrante for it in analise.itens}
        self.assertEqual(mapa_quadrantes["P1"], Quadrante.ESTRELA)
        self.assertEqual(mapa_quadrantes["P2"], Quadrante.BURRO_DE_CARGA)
        self.assertEqual(mapa_quadrantes["P3"], Quadrante.QUEBRA_CABECA)
        self.assertEqual(mapa_quadrantes["P4"], Quadrante.CAO)

        self.assertEqual(analise.contagem_quadrantes[Quadrante.ESTRELA], 1)
        self.assertEqual(analise.contagem_quadrantes[Quadrante.BURRO_DE_CARGA], 1)
        self.assertEqual(analise.contagem_quadrantes[Quadrante.QUEBRA_CABECA], 1)
        self.assertEqual(analise.contagem_quadrantes[Quadrante.CAO], 1)

    def test_popularidade_exatamente_no_limite(self) -> None:
        # N = 2 -> limiar = 7 / (10 * 2) = 7/20 = 35%
        # Vendas totais = 20 -> 35% = 7 vendas
        # Se um prato tem exatamente 7 vendas: 7/20 >= 7/20 -> Alta Popularidade
        f1 = self._criar_ficha_dummy("P1", 7, 3000, 1000, 2000)
        f2 = self._criar_ficha_dummy("P2", 13, 3000, 1000, 2000)

        analise = classificar_cardapio("Teste", "2026", [f1, f2])
        it1 = next(it for it in analise.itens if it.ficha.codigo == "P1")
        self.assertTrue(it1.alta_popularidade)

    def test_vendas_zeradas_em_todos_itens(self) -> None:
        # Se ninguém vendeu nada no período, nenhum prato tem alta popularidade
        f1 = self._criar_ficha_dummy("P1", 0, 4000, 1000, 3000)
        f2 = self._criar_ficha_dummy("P2", 0, 2000, 1000, 1000)

        analise = classificar_cardapio("Teste", "2026", [f1, f2])
        self.assertEqual(analise.total_porcoes_vendidas, 0)
        self.assertEqual(analise.faturamento_total_centavos, 0)
        # Margem de referência média simples = (3000 + 1000) / 2 = 2000
        # P1 (3000 >= 2000, alta margem, baixa pop) -> QUEBRA CABEÇA
        # P2 (1000 < 2000, baixa margem, baixa pop) -> CÃO
        mapa = {it.ficha.codigo: it.quadrante for it in analise.itens}
        self.assertEqual(mapa["P1"], Quadrante.QUEBRA_CABECA)
        self.assertEqual(mapa["P2"], Quadrante.CAO)

    def test_recomendacoes_estrategicas_presentes(self) -> None:
        f = self._criar_ficha_dummy("P1", 50, 4000, 1000, 3000)
        analise = classificar_cardapio("Teste", "2026", [f])
        it = analise.itens[0]
        self.assertIn("padrão de ficha técnica", it.recomendacao)


    def test_classificar_cardapio_lista_vazia(self) -> None:
        with self.assertRaises(ValueError):
            classificar_cardapio("Restaurante", "2026", [])


if __name__ == "__main__":
    unittest.main()
