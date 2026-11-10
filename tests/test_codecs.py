"""Testes unitários dos codecs canônicos JSON e proteção contra float e aninhamento.

LOFRANO TECNOLOGIA.
"""

from fractions import Fraction
import tempfile
import unittest

from precificacao_cardapio.codecs import (
    carregar_cardapio,
    decodificar_json_canonico,
    serializar_json_canonico,
)
from precificacao_cardapio.errors import (
    ERR_BOM_PROIBIDO,
    ERR_CHAVE_DUPLICADA,
    ERR_FLOAT_PROIBIDO,
    ERR_JSON_INVALIDO,
    ERR_PROFUNDIDADE_EXCEDIDA,
    ErroCodec,
)


class TestCodecs(unittest.TestCase):
    def test_decodificacao_valida(self) -> None:
        json_str = '{"estabelecimento": "Bistrô", "ano": 2026, "itens": [1, 2, 3]}'
        dados = decodificar_json_canonico(json_str)
        self.assertEqual(dados["estabelecimento"], "Bistrô")
        self.assertEqual(dados["ano"], 2026)
        self.assertEqual(dados["itens"], [1, 2, 3])

    def test_rejeicao_bom_bytes(self) -> None:
        payload = b"\xef\xbb\xbf{\"status\": \"ok\"}"
        with self.assertRaises(ErroCodec) as ctx:
            decodificar_json_canonico(payload)
        self.assertEqual(ctx.exception.codigo, ERR_BOM_PROIBIDO)

    def test_rejeicao_bom_str(self) -> None:
        payload = "\ufeff{\"status\": \"ok\"}"
        with self.assertRaises(ErroCodec) as ctx:
            decodificar_json_canonico(payload)
        self.assertEqual(ctx.exception.codigo, ERR_BOM_PROIBIDO)

    def test_rejeicao_chaves_duplicadas(self) -> None:
        payload = '{"chave": 1, "outra": 2, "chave": 3}'
        with self.assertRaises(ErroCodec) as ctx:
            decodificar_json_canonico(payload)
        self.assertEqual(ctx.exception.codigo, ERR_CHAVE_DUPLICADA)

    def test_rejeicao_float_decimal(self) -> None:
        payload = '{"preco": 12.50}'
        with self.assertRaises(ErroCodec) as ctx:
            decodificar_json_canonico(payload)
        self.assertEqual(ctx.exception.codigo, ERR_FLOAT_PROIBIDO)

    def test_rejeicao_float_notacao_cientifica(self) -> None:
        payload = '{"fator": 1e-3}'
        with self.assertRaises(ErroCodec) as ctx:
            decodificar_json_canonico(payload)
        self.assertEqual(ctx.exception.codigo, ERR_FLOAT_PROIBIDO)

    def test_rejeicao_profundidade_excessiva(self) -> None:
        # Construir aninhamento > 32
        d: dict = {"nivel": 0}
        curr = d
        for i in range(1, 35):
            curr["proximo"] = {"nivel": i}
            curr = curr["proximo"]

        payload = serializar_json_canonico(d)
        with self.assertRaises(ErroCodec) as ctx:
            decodificar_json_canonico(payload)
        self.assertEqual(ctx.exception.codigo, ERR_PROFUNDIDADE_EXCEDIDA)

    def test_serializacao_deterministica(self) -> None:
        obj = {"z": 10, "a": Fraction(1, 3), "m": 5}
        saida = serializar_json_canonico(obj)
        linhas = saida.strip().split("\n")
        self.assertTrue(linhas[1].strip().startswith('"a":'))
        self.assertTrue(linhas[-2].strip().startswith('"z":'))

    def test_serializacao_rejeita_float(self) -> None:
        with self.assertRaises(ErroCodec) as ctx:
            serializar_json_canonico({"valor": 12.5})
        self.assertEqual(ctx.exception.codigo, ERR_FLOAT_PROIBIDO)

    def test_carregar_cardapio_arquivo_real(self) -> None:
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            f.write("""{
              "nome_estabelecimento": "Casa Lofrano",
              "periodo": "2026",
              "insumos": [
                {
                  "codigo": "I1",
                  "nome": "Trigo",
                  "unidade": "g",
                  "quantidade_embalagem": 1000,
                  "custo_embalagem_centavos": 400
                }
              ],
              "fichas": [
                {
                  "codigo": "F1",
                  "nome": "Pao",
                  "categoria": "Padaria",
                  "rendimento_porcoes": 1,
                  "preco_venda_centavos": 200,
                  "vendas_periodo": 100,
                  "ingredientes": [
                    { "codigo_insumo": "I1", "quantidade_liquida": 200 }
                  ]
                }
              ]
            }""")
            f.flush()
            cardapio = carregar_cardapio(f.name)
            self.assertEqual(cardapio.nome_estabelecimento, "Casa Lofrano")
            self.assertEqual(len(cardapio.insumos), 1)
            self.assertEqual(len(cardapio.fichas), 1)


if __name__ == "__main__":
    unittest.main()
