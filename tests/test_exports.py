"""Testes unitários dos exportadores, sanitização CSV, relatórios e ZIP determinístico.

LOFRANO TECNOLOGIA.
"""

from fractions import Fraction
from pathlib import Path
import tempfile
import unittest
import zipfile

from precificacao_cardapio.calculator import FichaCalculada
from precificacao_cardapio.domain import Cardapio, FichaTecnica, Insumo, ItemFicha, UnidadeMedida
from precificacao_cardapio.errors import ERR_ARQUIVO_EXISTENTE, PrecificacaoError
from precificacao_cardapio.exports import (
    centavos_para_reais_str,
    criar_pacote_zip_deterministico,
    exportar_fichas_csv,
    exportar_insumos_csv,
    gerar_relatorio_markdown,
    sanitizar_csv,
)
from precificacao_cardapio.menu_matrix import classificar_cardapio
from precificacao_cardapio.svg_report import gerar_painel_svg


class TestExports(unittest.TestCase):
    def test_sanitizacao_csv_injecao(self) -> None:
        self.assertEqual(sanitizar_csv("=SOMA(A1:A10)"), "'=SOMA(A1:A10)")
        self.assertEqual(sanitizar_csv("+12345"), "'+12345")
        self.assertEqual(sanitizar_csv("-cmd"), "'-cmd")
        self.assertEqual(sanitizar_csv("@externo"), "'@externo")
        self.assertEqual(sanitizar_csv("\tcmd"), "'\tcmd")
        self.assertEqual(sanitizar_csv("\rcmd"), "'\rcmd")
        self.assertEqual(sanitizar_csv("Filé Mignon"), "Filé Mignon")
        self.assertEqual(sanitizar_csv(1500), "1500")

    def test_conversao_centavos_para_reais(self) -> None:
        self.assertEqual(centavos_para_reais_str(0), "R$ 0,00")
        self.assertEqual(centavos_para_reais_str(10), "R$ 0,10")
        self.assertEqual(centavos_para_reais_str(100), "R$ 1,00")
        self.assertEqual(centavos_para_reais_str(4580), "R$ 45,80")
        self.assertEqual(centavos_para_reais_str(-250), "-R$ 2,50")

    def test_exportacao_csv_e_markdown(self) -> None:
        f = FichaCalculada(
            codigo="PRAT-TESTE",
            nome="=Fórmula Injetada",
            categoria="Geral",
            rendimento_porcoes=1,
            ingredientes=[],
            custo_ingredientes_centavos=1000,
            custo_embalagem_centavos=50,
            custo_total_receita_centavos=1050,
            custo_porcao_centavos=1050,
            preco_venda_centavos=3000,
            cmv_alvo_num=30,
            cmv_alvo_den=100,
            taxas_impostos_num=0,
            taxas_impostos_den=100,
            deducao_impostos_centavos=0,
            margem_contribuicao_centavos=1950,
            preco_sugerido_cmv_alvo_centavos=3500,
            vendas_periodo=10,
            faturamento_total_centavos=30000,
            custo_total_periodo_centavos=10500,
            margem_total_periodo_centavos=19500,
        )

        analise = classificar_cardapio("Restaurante Mock", "2026", [f])

        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = Path(tmpdir) / "fichas.csv"
            exportar_fichas_csv(analise, csv_path)
            conteudo_csv = csv_path.read_text(encoding="utf-8")
            self.assertIn("PRAT-TESTE", conteudo_csv)
            # Conferir neutralização de injeção no nome
            self.assertIn("'=Fórmula Injetada", conteudo_csv)

            # Testar Markdown
            relatorio = gerar_relatorio_markdown(analise)
            self.assertIn("# Relatório de Engenharia de Cardápio", relatorio)
            self.assertIn("Restaurante Mock", relatorio)
            self.assertIn("R$ 300,00", relatorio)

            # Testar SVG
            svg = gerar_painel_svg(analise)
            self.assertTrue(svg.startswith("<svg"))
            self.assertIn("Restaurante Mock", svg)
            self.assertIn("PRAT-TESTE", svg)

    def test_exportar_insumos_csv(self) -> None:
        ins = Insumo("INS-01", "+Insumo Malicioso", UnidadeMedida.GRAMA, 1000, 2000, 110, 100)
        f = FichaTecnica("P1", "Prato", "Cat", 1, [ItemFicha("INS-01", 100)], 0, 1000, 10)
        cardapio = Cardapio("Restaurante", "2026", {"INS-01": ins}, [f])

        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = Path(tmpdir) / "insumos.csv"
            exportar_insumos_csv(cardapio, csv_path)
            txt = csv_path.read_text(encoding="utf-8")
            self.assertIn("INS-01", txt)
            self.assertIn("'+Insumo Malicioso", txt)
            self.assertIn("110/100", txt)

    def test_pacote_zip_deterministico(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            zip_path = Path(tmpdir) / "teste.zip"
            arquivos = [
                ("relatorio.txt", b"Texto de teste deterministico 1"),
                ("dados.bin", b"\x01\x02\x03\x04"),
            ]
            criar_pacote_zip_deterministico(zip_path, arquivos)
            self.assertTrue(zip_path.exists())

            # Conferir atributos internos do ZIP
            with zipfile.ZipFile(zip_path, "r") as zf:
                for zinfo in zf.infolist():
                    self.assertEqual(zinfo.date_time, (2026, 11, 10, 0, 0, 0))

            # Tentar sobrescrever sem permissão deve falhar por proteção atômica O_EXCL
            with self.assertRaises(PrecificacaoError) as ctx:
                criar_pacote_zip_deterministico(zip_path, arquivos)
            self.assertEqual(ctx.exception.codigo, ERR_ARQUIVO_EXISTENTE)


if __name__ == "__main__":
    unittest.main()
