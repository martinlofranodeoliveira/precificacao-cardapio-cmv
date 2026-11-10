"""Testes unitários da interface CLI de precificação e engenharia de cardápio.

LOFRANO TECNOLOGIA.
"""

import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from precificacao_cardapio.cli import main


class TestCLI(unittest.TestCase):
    def test_versao(self) -> None:
        with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
            code = main(["versao"])
            self.assertEqual(code, 0)
            self.assertIn("1.0.0", mock_out.getvalue())

        with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
            code = main(["-v"])
            self.assertEqual(code, 0)
            self.assertIn("1.0.0", mock_out.getvalue())

    def test_exemplo_stdout(self) -> None:
        with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
            code = main(["exemplo"])
            self.assertEqual(code, 0)
            self.assertIn("Bistrô & Trattoria Lofrano", mock_out.getvalue())
            self.assertIn("PRAT-RISOTO-COGUMELO", mock_out.getvalue())

    def test_exemplo_saida_arquivo(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            out_file = Path(tmpdir) / "exemplo.json"
            code = main(["exemplo", "--saida", str(out_file)])
            self.assertEqual(code, 0)
            self.assertTrue(out_file.exists())
            conteudo = out_file.read_text(encoding="utf-8")
            self.assertIn("Bistrô & Trattoria Lofrano", conteudo)

    def test_analisar_cardapio_completo(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_p = Path(tmpdir)
            json_in = tmp_p / "cardapio.json"
            main(["exemplo", "--saida", str(json_in)])

            out_dir = tmp_p / "saida"
            out_zip = tmp_p / "pacote.zip"

            with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
                code = main([
                    "analisar",
                    str(json_in),
                    "--saida-dir",
                    str(out_dir),
                    "--zip",
                    str(out_zip),
                ])
                self.assertEqual(code, 0)
                out_txt = mock_out.getvalue()
                self.assertIn("RESUMO DE ENGENHARIA DE CARDÁPIO", out_txt)
                self.assertIn("Faturamento Total:", out_txt)

            # Verificar arquivos gerados no diretório
            self.assertTrue((out_dir / "analise_cardapio.json").exists())
            self.assertTrue((out_dir / "relatorio.md").exists())
            self.assertTrue((out_dir / "painel.svg").exists())
            self.assertTrue((out_dir / "fichas_tecnicas.csv").exists())
            self.assertTrue((out_dir / "insumos.csv").exists())

            # Verificar pacote ZIP
            self.assertTrue(out_zip.exists())

    def test_analisar_arquivo_inexistente(self) -> None:
        with patch("sys.stderr", new_callable=io.StringIO) as mock_err:
            code = main(["analisar", "/caminho/fantasma/inexistente.json"])
            self.assertNotEqual(code, 0)
            self.assertIn("Erro", mock_err.getvalue())


if __name__ == "__main__":
    unittest.main()
