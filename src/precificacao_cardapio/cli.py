"""Interface de Linha de Comando (CLI) para precificação gastronômica e engenharia de cardápio.

LOFRANO TECNOLOGIA.
"""

import argparse
from pathlib import Path
import sys
from typing import List, Optional

from .calculator import calcular_ficha
from .codecs import (
    analise_para_dict,
    carregar_cardapio,
    decodificar_json_canonico,
    serializar_json_canonico,
)
from .errors import PrecificacaoError
from .exports import (
    centavos_para_reais_str,
    criar_pacote_zip_deterministico,
    exportar_fichas_csv,
    exportar_insumos_csv,
    gerar_fichas_csv_str,
    gerar_insumos_csv_str,
    gerar_relatorio_markdown,
)
from .menu_matrix import classificar_cardapio
from .svg_report import gerar_painel_svg

VERSAO = "1.0.0"


def configurar_stdout_utf8() -> None:
    """Garante saída segura em UTF-8 nos consoles do Windows e Linux."""
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    if hasattr(sys.stderr, "reconfigure"):
        try:
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


EXEMPLO_CARDAPIO_JSON = """{
  "nome_estabelecimento": "Bistrô & Trattoria Lofrano",
  "periodo": "Outubro/2026",
  "insumos": [
    {
      "codigo": "INS-FIL-MIGNON",
      "nome": "Filé Mignon Bovino Limpo",
      "unidade": "g",
      "quantidade_embalagem": 1000,
      "custo_embalagem_centavos": 7800,
      "fator_correcao_num": 110,
      "fator_correcao_den": 100
    },
    {
      "codigo": "INS-ARROZ-ARB",
      "nome": "Arroz Arbóreo Italiano",
      "unidade": "g",
      "quantidade_embalagem": 1000,
      "custo_embalagem_centavos": 2200,
      "fator_correcao_num": 1,
      "fator_correcao_den": 1
    },
    {
      "codigo": "INS-PARMESAO",
      "nome": "Queijo Parmesão Grana",
      "unidade": "g",
      "quantidade_embalagem": 1000,
      "custo_embalagem_centavos": 11000,
      "fator_correcao_num": 105,
      "fator_correcao_den": 100
    },
    {
      "codigo": "INS-MANTEIGA",
      "nome": "Manteiga Extra sem Sal",
      "unidade": "g",
      "quantidade_embalagem": 500,
      "custo_embalagem_centavos": 2600,
      "fator_correcao_num": 1,
      "fator_correcao_den": 1
    },
    {
      "codigo": "INS-COGUMELOS",
      "nome": "Mix de Cogumelos Frescos",
      "unidade": "g",
      "quantidade_embalagem": 400,
      "custo_embalagem_centavos": 2800,
      "fator_correcao_num": 120,
      "fator_correcao_den": 100
    },
    {
      "codigo": "INS-SALMAO",
      "nome": "Salmão Fresco em Filé",
      "unidade": "g",
      "quantidade_embalagem": 1000,
      "custo_embalagem_centavos": 9500,
      "fator_correcao_num": 115,
      "fator_correcao_den": 100
    },
    {
      "codigo": "INS-MASSA-TAL",
      "nome": "Massa Fresca Tagliolini",
      "unidade": "g",
      "quantidade_embalagem": 500,
      "custo_embalagem_centavos": 1400,
      "fator_correcao_num": 1,
      "fator_correcao_den": 1
    },
    {
      "codigo": "INS-CREME-LEITE",
      "nome": "Creme de Leite Fresco",
      "unidade": "ml",
      "quantidade_embalagem": 500,
      "custo_embalagem_centavos": 1800,
      "fator_correcao_num": 1,
      "fator_correcao_den": 1
    },
    {
      "codigo": "INS-MASCARPONE",
      "nome": "Queijo Mascarpone Italiano",
      "unidade": "g",
      "quantidade_embalagem": 500,
      "custo_embalagem_centavos": 4200,
      "fator_correcao_num": 1,
      "fator_correcao_den": 1
    },
    {
      "codigo": "INS-BISCOITO-CHAMP",
      "nome": "Biscoito Champagne",
      "unidade": "g",
      "quantidade_embalagem": 300,
      "custo_embalagem_centavos": 1200,
      "fator_correcao_num": 1,
      "fator_correcao_den": 1
    },
    {
      "codigo": "INS-CAFE-GRAOS",
      "nome": "Café Especial em Grãos",
      "unidade": "g",
      "quantidade_embalagem": 1000,
      "custo_embalagem_centavos": 8500,
      "fator_correcao_num": 1,
      "fator_correcao_den": 1
    },
    {
      "codigo": "INS-LIMPA-TRUFA",
      "nome": "Azeite Trufado Branco",
      "unidade": "ml",
      "quantidade_embalagem": 250,
      "custo_embalagem_centavos": 8500,
      "fator_correcao_num": 1,
      "fator_correcao_den": 1
    },
    {
      "codigo": "INS-PAO-CIABATTA",
      "nome": "Pão Ciabatta Artesanal",
      "unidade": "g",
      "quantidade_embalagem": 400,
      "custo_embalagem_centavos": 1200,
      "fator_correcao_num": 1,
      "fator_correcao_den": 1
    },
    {
      "codigo": "INS-TOMATE-ITAL",
      "nome": "Tomate Italiano Maduro",
      "unidade": "g",
      "quantidade_embalagem": 1000,
      "custo_embalagem_centavos": 900,
      "fator_correcao_num": 120,
      "fator_correcao_den": 100
    },
    {
      "codigo": "INS-SEMOLA-POLENTA",
      "nome": "Sêmola de Milho para Polenta",
      "unidade": "g",
      "quantidade_embalagem": 1000,
      "custo_embalagem_centavos": 800,
      "fator_correcao_num": 1,
      "fator_correcao_den": 1
    }
  ],
  "fichas": [
    {
      "codigo": "PRAT-BRUSCHETTA-TOMATE",
      "nome": "Bruschetta Tradicional de Tomate",
      "categoria": "Entradas",
      "rendimento_porcoes": 1,
      "custo_embalagem_centavos": 100,
      "preco_venda_centavos": 2400,
      "vendas_periodo": 60,
      "cmv_alvo_num": 25,
      "cmv_alvo_den": 100,
      "taxas_impostos_num": 12,
      "taxas_impostos_den": 100,
      "ingredientes": [
        { "codigo_insumo": "INS-PAO-CIABATTA", "quantidade_liquida": 120 },
        { "codigo_insumo": "INS-TOMATE-ITAL", "quantidade_liquida": 150 },
        { "codigo_insumo": "INS-PARMESAO", "quantidade_liquida": 30 }
      ]
    },
    {
      "codigo": "PRAT-POLENTA-TRUFADA",
      "nome": "Polenta Cremosa Trufada",
      "categoria": "Entradas",
      "rendimento_porcoes": 1,
      "custo_embalagem_centavos": 100,
      "preco_venda_centavos": 5800,
      "vendas_periodo": 85,
      "cmv_alvo_num": 22,
      "cmv_alvo_den": 100,
      "taxas_impostos_num": 12,
      "taxas_impostos_den": 100,
      "ingredientes": [
        { "codigo_insumo": "INS-SEMOLA-POLENTA", "quantidade_liquida": 100 },
        { "codigo_insumo": "INS-PARMESAO", "quantidade_liquida": 40 },
        { "codigo_insumo": "INS-LIMPA-TRUFA", "quantidade_liquida": 10 }
      ]
    },
    {
      "codigo": "PRAT-RISOTO-COGUMELO",
      "nome": "Risoto de Cogumelos Trufado",
      "categoria": "Pratos Principais",
      "rendimento_porcoes": 1,
      "custo_embalagem_centavos": 150,
      "preco_venda_centavos": 7800,
      "vendas_periodo": 340,
      "cmv_alvo_num": 28,
      "cmv_alvo_den": 100,
      "taxas_impostos_num": 12,
      "taxas_impostos_den": 100,
      "ingredientes": [
        { "codigo_insumo": "INS-ARROZ-ARB", "quantidade_liquida": 120 },
        { "codigo_insumo": "INS-COGUMELOS", "quantidade_liquida": 100 },
        { "codigo_insumo": "INS-PARMESAO", "quantidade_liquida": 40 },
        { "codigo_insumo": "INS-MANTEIGA", "quantidade_liquida": 30 },
        { "codigo_insumo": "INS-LIMPA-TRUFA", "quantidade_liquida": 10 }
      ]
    },
    {
      "codigo": "PRAT-MIGNON-MOLHO",
      "nome": "Medalhão de Mignon ao Poivre",
      "categoria": "Pratos Principais",
      "rendimento_porcoes": 1,
      "custo_embalagem_centavos": 200,
      "preco_venda_centavos": 9200,
      "vendas_periodo": 410,
      "cmv_alvo_num": 30,
      "cmv_alvo_den": 100,
      "taxas_impostos_num": 12,
      "taxas_impostos_den": 100,
      "ingredientes": [
        { "codigo_insumo": "INS-FIL-MIGNON", "quantidade_liquida": 220 },
        { "codigo_insumo": "INS-MANTEIGA", "quantidade_liquida": 25 },
        { "codigo_insumo": "INS-CREME-LEITE", "quantidade_liquida": 60 }
      ]
    },
    {
      "codigo": "PRAT-SALMAO-GRELHADO",
      "nome": "Salmão com Crosta de Parmesão",
      "categoria": "Pratos Principais",
      "rendimento_porcoes": 1,
      "custo_embalagem_centavos": 200,
      "preco_venda_centavos": 8900,
      "vendas_periodo": 120,
      "cmv_alvo_num": 30,
      "cmv_alvo_den": 100,
      "taxas_impostos_num": 12,
      "taxas_impostos_den": 100,
      "ingredientes": [
        { "codigo_insumo": "INS-SALMAO", "quantidade_liquida": 200 },
        { "codigo_insumo": "INS-PARMESAO", "quantidade_liquida": 35 },
        { "codigo_insumo": "INS-MANTEIGA", "quantidade_liquida": 20 }
      ]
    },
    {
      "codigo": "PRAT-MASSA-TRUFA",
      "nome": "Tagliolini na Manteiga Trufada",
      "categoria": "Massas",
      "rendimento_porcoes": 1,
      "custo_embalagem_centavos": 150,
      "preco_venda_centavos": 6200,
      "vendas_periodo": 290,
      "cmv_alvo_num": 25,
      "cmv_alvo_den": 100,
      "taxas_impostos_num": 12,
      "taxas_impostos_den": 100,
      "ingredientes": [
        { "codigo_insumo": "INS-MASSA-TAL", "quantidade_liquida": 180 },
        { "codigo_insumo": "INS-MANTEIGA", "quantidade_liquida": 40 },
        { "codigo_insumo": "INS-PARMESAO", "quantidade_liquida": 30 },
        { "codigo_insumo": "INS-LIMPA-TRUFA", "quantidade_liquida": 8 }
      ]
    },
    {
      "codigo": "PRAT-TIRAMISU",
      "nome": "Tiramisù Clássico Italiano",
      "categoria": "Sobremesas",
      "rendimento_porcoes": 6,
      "custo_embalagem_centavos": 300,
      "preco_venda_centavos": 3200,
      "vendas_periodo": 280,
      "cmv_alvo_num": 22,
      "cmv_alvo_den": 100,
      "taxas_impostos_num": 12,
      "taxas_impostos_den": 100,
      "ingredientes": [
        { "codigo_insumo": "INS-MASCARPONE", "quantidade_liquida": 350 },
        { "codigo_insumo": "INS-CREME-LEITE", "quantidade_liquida": 200 },
        { "codigo_insumo": "INS-BISCOITO-CHAMP", "quantidade_liquida": 150 },
        { "codigo_insumo": "INS-CAFE-GRAOS", "quantidade_liquida": 40 }
      ]
    },
    {
      "codigo": "PRAT-ESPRESSO-DOSE",
      "nome": "Café Espresso Especial",
      "categoria": "Bebidas",
      "rendimento_porcoes": 1,
      "custo_embalagem_centavos": 30,
      "preco_venda_centavos": 900,
      "vendas_periodo": 520,
      "cmv_alvo_num": 20,
      "cmv_alvo_den": 100,
      "taxas_impostos_num": 12,
      "taxas_impostos_den": 100,
      "ingredientes": [
        { "codigo_insumo": "INS-CAFE-GRAOS", "quantidade_liquida": 18 }
      ]
    }
  ]
}
"""


def executar_analise(
    caminho_entrada: Path,
    saida_dir: Optional[Path] = None,
    saida_zip: Optional[Path] = None,
) -> int:
    """Executa a análise completa de um arquivo de cardápio."""
    configurar_stdout_utf8()

    try:
        cardapio = carregar_cardapio(caminho_entrada)
        print(f"Carregado cardapio: '{cardapio.nome_estabelecimento}' ({cardapio.periodo})")
        print(f"Insumos cadastrados: {len(cardapio.insumos)} | Fichas tecnicas: {len(cardapio.fichas)}")

        # Calcular fichas
        fichas_calculadas = [calcular_ficha(f, cardapio.insumos) for f in cardapio.fichas]

        # Classificar na Matriz Kasavana & Smith
        analise = classificar_cardapio(
            estabelecimento=cardapio.nome_estabelecimento,
            periodo=cardapio.periodo,
            fichas_calculadas=fichas_calculadas,
        )

        # Exibir resumo em console
        fat_fmt = centavos_para_reais_str(analise.faturamento_total_centavos)
        cmv_fmt = centavos_para_reais_str(analise.custo_total_centavos)
        mg_fmt = centavos_para_reais_str(analise.margem_total_centavos)
        cmv_pct = (
            f"{analise.cmv_medio_ponderado_frac.numerator * 100 // analise.cmv_medio_ponderado_frac.denominator}%"
            if analise.cmv_medio_ponderado_frac.denominator > 0 else "0%"
        )

        print("\n--- RESUMO DE ENGENHARIA DE CARDÁPIO ---")
        print(f"Faturamento Total: {fat_fmt}")
        print(f"Custo Total (CMV Consolidado): {cmv_fmt} ({cmv_pct})")
        print(f"Margem de Contribuição Consolidada: {mg_fmt}")
        print("Distribuição Kasavana & Smith:")
        for q, qtd in analise.contagem_quadrantes.items():
            print(f"  - {q.value}: {qtd} itens")

        # Gerar artefatos
        analise_dict = analise_para_dict(analise)
        analise_json_bytes = serializar_json_canonico(analise_dict).encode("utf-8")
        relatorio_md_bytes = gerar_relatorio_markdown(analise).encode("utf-8")
        painel_svg_bytes = gerar_painel_svg(analise).encode("utf-8")

        # Salvar em pasta se solicitado
        if saida_dir:
            saida_dir.mkdir(parents=True, exist_ok=True)
            (saida_dir / "analise_cardapio.json").write_bytes(analise_json_bytes)
            (saida_dir / "relatorio.md").write_bytes(relatorio_md_bytes)
            (saida_dir / "painel.svg").write_bytes(painel_svg_bytes)
            exportar_fichas_csv(analise, saida_dir / "fichas_tecnicas.csv")
            exportar_insumos_csv(cardapio, saida_dir / "insumos.csv")
            print(f"\nArtefatos gerados na pasta: {saida_dir.resolve()}")

        # Salvar pacote ZIP se solicitado
        if saida_zip:
            fichas_csv_bytes = gerar_fichas_csv_str(analise).encode("utf-8")
            insumos_csv_bytes = gerar_insumos_csv_str(cardapio).encode("utf-8")

            arquivos_zip = [
                ("entrada.json", caminho_entrada.read_bytes()),
                ("analise_cardapio.json", analise_json_bytes),
                ("fichas_tecnicas.csv", fichas_csv_bytes),
                ("insumos.csv", insumos_csv_bytes),
                ("relatorio.md", relatorio_md_bytes),
                ("painel.svg", painel_svg_bytes),
            ]
            criar_pacote_zip_deterministico(saida_zip, arquivos_zip)
            print(f"Pacote ZIP determinístico gerado: {saida_zip.resolve()}")

        return 0

    except PrecificacaoError as e:
        print(f"Erro de processamento: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Erro inesperado: {e}", file=sys.stderr)
        return 2


def main(argv: Optional[List[str]] = None) -> int:
    """Ponto de entrada principal da CLI."""
    configurar_stdout_utf8()

    parser = argparse.ArgumentParser(
        prog="precificacao-cardapio",
        description="Engenharia de Cardápio, Ficha Técnica Gastronômica e CMV Alvo (LOFRANO TECNOLOGIA).",
    )
    parser.add_argument("-v", "--versao", action="store_true", help="Exibe a versão do programa.")

    subparsers = parser.add_subparsers(dest="comando", help="Comandos disponíveis")

    # Subcomando analisar
    parser_analisar = subparsers.add_parser("analisar", help="Analisa custos, fichas técnicas e matriz de cardápio.")
    parser_analisar.add_argument("arquivo", type=str, help="Caminho do arquivo JSON de cardápio e insumos.")
    parser_analisar.add_argument("--saida-dir", type=str, default=None, help="Diretório de saída para os artefatos.")
    parser_analisar.add_argument("--zip", type=str, default=None, help="Caminho para gerar o pacote ZIP determinístico.")

    # Subcomando exemplo
    parser_exemplo = subparsers.add_parser("exemplo", help="Exporta modelo canônico de cardápio para demonstração.")
    parser_exemplo.add_argument("--saida", type=str, default=None, help="Arquivo de destino do exemplo.")

    # Subcomando versao
    subparsers.add_parser("versao", help="Exibe a versão instalada.")

    args = parser.parse_args(argv)

    if args.versao or args.comando == "versao":
        print(f"precificacao-cardapio {VERSAO}")
        return 0

    if args.comando == "exemplo":
        conteudo = EXEMPLO_CARDAPIO_JSON
        if args.saida:
            Path(args.saida).write_text(conteudo, encoding="utf-8")
            print(f"Exemplo canônico gravado em: {args.saida}")
        else:
            print(conteudo)
        return 0

    if args.comando == "analisar":
        caminho_in = Path(args.arquivo)
        caminho_dir = Path(args.saida_dir) if args.saida_dir else None
        caminho_zip = Path(args.zip) if args.zip else None
        return executar_analise(caminho_in, saida_dir=caminho_dir, saida_zip=caminho_zip)

    # Se nenhum comando foi informado
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
