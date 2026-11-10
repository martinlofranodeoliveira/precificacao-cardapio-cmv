"""Testes unitários dos modelos de domínio para precificação gastronômica.

LOFRANO TECNOLOGIA.
"""

from fractions import Fraction
import unittest

from precificacao_cardapio.domain import Cardapio, FichaTecnica, Insumo, ItemFicha, UnidadeMedida
from precificacao_cardapio.errors import (
    ERR_CATEGORIA_VAZIA,
    ERR_CODIGO_DUPLICADO,
    ERR_INSUMO_NAO_ENCONTRADO,
    ERR_QUANTIDADE_INVALIDA,
    ERR_VALOR_INVALIDO,
    ErroValidacao,
)


class TestDominio(unittest.TestCase):
    def test_insumo_valido(self) -> None:
        ins = Insumo("INS-01", "Farinha", UnidadeMedida.GRAMA, 1000, 500, 1, 1)
        self.assertEqual(ins.codigo, "INS-01")
        self.assertEqual(ins.nome, "Farinha")
        self.assertEqual(ins.unidade, UnidadeMedida.GRAMA)
        self.assertEqual(ins.quantidade_embalagem, 1000)
        self.assertEqual(ins.custo_embalagem_centavos, 500)
        self.assertEqual(ins.fator_correcao, Fraction(1, 1))
        self.assertEqual(ins.custo_unitario_frac, Fraction(500, 1000))

    def test_insumo_codigo_vazio(self) -> None:
        with self.assertRaises(ErroValidacao) as ctx:
            Insumo("", "Farinha", UnidadeMedida.GRAMA, 1000, 500)
        self.assertEqual(ctx.exception.codigo, ERR_VALOR_INVALIDO)

    def test_insumo_nome_vazio(self) -> None:
        with self.assertRaises(ErroValidacao) as ctx:
            Insumo("INS-01", "   ", UnidadeMedida.GRAMA, 1000, 500)
        self.assertEqual(ctx.exception.codigo, ERR_VALOR_INVALIDO)

    def test_insumo_quantidade_embalagem_invalida(self) -> None:
        with self.assertRaises(ErroValidacao) as ctx:
            Insumo("INS-01", "Farinha", UnidadeMedida.GRAMA, 0, 500)
        self.assertEqual(ctx.exception.codigo, ERR_QUANTIDADE_INVALIDA)

        with self.assertRaises(ErroValidacao) as ctx:
            Insumo("INS-01", "Farinha", UnidadeMedida.GRAMA, -100, 500)
        self.assertEqual(ctx.exception.codigo, ERR_QUANTIDADE_INVALIDA)

    def test_insumo_custo_negativo(self) -> None:
        with self.assertRaises(ErroValidacao) as ctx:
            Insumo("INS-01", "Farinha", UnidadeMedida.GRAMA, 1000, -50)
        self.assertEqual(ctx.exception.codigo, ERR_VALOR_INVALIDO)

    def test_insumo_fator_correcao_menor_que_um(self) -> None:
        with self.assertRaises(ErroValidacao) as ctx:
            Insumo("INS-01", "Farinha", UnidadeMedida.GRAMA, 1000, 500, 90, 100)
        self.assertEqual(ctx.exception.codigo, ERR_VALOR_INVALIDO)

    def test_insumo_fator_correcao_denominador_invalido(self) -> None:
        with self.assertRaises(ErroValidacao) as ctx:
            Insumo("INS-01", "Farinha", UnidadeMedida.GRAMA, 1000, 500, 100, 0)
        self.assertEqual(ctx.exception.codigo, ERR_VALOR_INVALIDO)

    def test_item_ficha_valido(self) -> None:
        it = ItemFicha("INS-01", 250)
        self.assertEqual(it.codigo_insumo, "INS-01")
        self.assertEqual(it.quantidade_liquida, 250)
        self.assertIsNone(it.fator_correcao_override_num)

    def test_item_ficha_quantidade_invalida(self) -> None:
        with self.assertRaises(ErroValidacao) as ctx:
            ItemFicha("INS-01", 0)
        self.assertEqual(ctx.exception.codigo, ERR_QUANTIDADE_INVALIDA)

    def test_item_ficha_override_invalido(self) -> None:
        with self.assertRaises(ErroValidacao) as ctx:
            ItemFicha("INS-01", 100, 80, 100)
        self.assertEqual(ctx.exception.codigo, ERR_VALOR_INVALIDO)

    def test_ficha_tecnica_valida(self) -> None:
        f = FichaTecnica(
            codigo="PRAT-01",
            nome="Bolo",
            categoria="Sobremesas",
            rendimento_porcoes=8,
            ingredientes=[ItemFicha("INS-01", 500)],
            custo_embalagem_centavos=120,
            preco_venda_centavos=4500,
            vendas_periodo=30,
        )
        self.assertEqual(f.codigo, "PRAT-01")
        self.assertEqual(f.rendimento_porcoes, 8)
        self.assertEqual(f.cmv_alvo, Fraction(30, 100))
        self.assertEqual(f.taxas_impostos, Fraction(0, 100))

    def test_ficha_tecnica_categoria_vazia(self) -> None:
        with self.assertRaises(ErroValidacao) as ctx:
            FichaTecnica("PRAT-01", "Bolo", "", 1, [ItemFicha("INS-01", 500)], 0, 1000, 10)
        self.assertEqual(ctx.exception.codigo, ERR_CATEGORIA_VAZIA)

    def test_ficha_tecnica_sem_ingredientes(self) -> None:
        with self.assertRaises(ErroValidacao) as ctx:
            FichaTecnica("PRAT-01", "Bolo", "Doces", 1, [], 0, 1000, 10)
        self.assertEqual(ctx.exception.codigo, ERR_VALOR_INVALIDO)

    def test_cardapio_insumo_inexistente(self) -> None:
        ins = {"INS-01": Insumo("INS-01", "Farinha", UnidadeMedida.GRAMA, 1000, 500)}
        f = FichaTecnica("PRAT-01", "Bolo", "Doces", 1, [ItemFicha("INS-FANTASMA", 500)], 0, 1000, 10)
        with self.assertRaises(ErroValidacao) as ctx:
            Cardapio("Restaurante Teste", "2026-11", ins, [f])
        self.assertEqual(ctx.exception.codigo, ERR_INSUMO_NAO_ENCONTRADO)

    def test_cardapio_fichas_duplicadas(self) -> None:
        ins = {"INS-01": Insumo("INS-01", "Farinha", UnidadeMedida.GRAMA, 1000, 500)}
        f1 = FichaTecnica("PRAT-01", "Bolo", "Doces", 1, [ItemFicha("INS-01", 500)], 0, 1000, 10)
        f2 = FichaTecnica("PRAT-01", "Outro Bolo", "Doces", 1, [ItemFicha("INS-01", 500)], 0, 1000, 10)
        with self.assertRaises(ErroValidacao) as ctx:
            Cardapio("Restaurante Teste", "2026-11", ins, [f1, f2])
        self.assertEqual(ctx.exception.codigo, ERR_CODIGO_DUPLICADO)


    def test_insumo_unidade_invalida_tipo(self) -> None:
        with self.assertRaises(ErroValidacao) as ctx:
            Insumo("INS-01", "Farinha", "quilograma", 1000, 500)  # type: ignore
        self.assertEqual(ctx.exception.codigo, ERR_VALOR_INVALIDO)

    def test_ficha_tecnica_rendimento_invalido(self) -> None:
        with self.assertRaises(ErroValidacao) as ctx:
            FichaTecnica("P1", "Item", "Cat", 0, [ItemFicha("INS-01", 10)], 0, 1000, 10)
        self.assertEqual(ctx.exception.codigo, ERR_VALOR_INVALIDO)

        with self.assertRaises(ErroValidacao) as ctx:
            FichaTecnica("P1", "Item", "Cat", -2, [ItemFicha("INS-01", 10)], 0, 1000, 10)
        self.assertEqual(ctx.exception.codigo, ERR_VALOR_INVALIDO)

    def test_ficha_tecnica_preco_negativo(self) -> None:
        with self.assertRaises(ErroValidacao) as ctx:
            FichaTecnica("P1", "Item", "Cat", 1, [ItemFicha("INS-01", 10)], 0, -500, 10)
        self.assertEqual(ctx.exception.codigo, ERR_VALOR_INVALIDO)

    def test_ficha_tecnica_vendas_negativas(self) -> None:
        with self.assertRaises(ErroValidacao) as ctx:
            FichaTecnica("P1", "Item", "Cat", 1, [ItemFicha("INS-01", 10)], 0, 1000, -5)
        self.assertEqual(ctx.exception.codigo, ERR_VALOR_INVALIDO)

    def test_ficha_tecnica_cmv_alvo_invalido(self) -> None:
        with self.assertRaises(ErroValidacao) as ctx:
            FichaTecnica("P1", "Item", "Cat", 1, [ItemFicha("INS-01", 10)], 0, 1000, 10, 0, 100)
        self.assertEqual(ctx.exception.codigo, ERR_VALOR_INVALIDO)

        with self.assertRaises(ErroValidacao) as ctx:
            FichaTecnica("P1", "Item", "Cat", 1, [ItemFicha("INS-01", 10)], 0, 1000, 10, 30, 0)
        self.assertEqual(ctx.exception.codigo, ERR_VALOR_INVALIDO)

    def test_ficha_tecnica_taxas_invalidas(self) -> None:
        with self.assertRaises(ErroValidacao) as ctx:
            FichaTecnica("P1", "Item", "Cat", 1, [ItemFicha("INS-01", 10)], 0, 1000, 10, 30, 100, -1, 100)
        self.assertEqual(ctx.exception.codigo, ERR_VALOR_INVALIDO)

        with self.assertRaises(ErroValidacao) as ctx:
            FichaTecnica("P1", "Item", "Cat", 1, [ItemFicha("INS-01", 10)], 0, 1000, 10, 30, 100, 10, 0)
        self.assertEqual(ctx.exception.codigo, ERR_VALOR_INVALIDO)

    def test_cardapio_sem_insumos_ou_fichas(self) -> None:
        ins = {"INS-01": Insumo("INS-01", "Farinha", UnidadeMedida.GRAMA, 1000, 500)}
        f = FichaTecnica("P1", "Item", "Cat", 1, [ItemFicha("INS-01", 10)], 0, 1000, 10)

        with self.assertRaises(ErroValidacao):
            Cardapio("Restaurante", "2026", {}, [f])

        with self.assertRaises(ErroValidacao):
            Cardapio("Restaurante", "2026", ins, [])


if __name__ == "__main__":
    unittest.main()
