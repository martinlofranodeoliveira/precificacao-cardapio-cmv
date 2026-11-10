"""Exportadores e geradores de relatórios analíticos, CSVs seguros e pacotes determinísticos.

LOFRANO TECNOLOGIA.
"""

from fractions import Fraction
import os
from pathlib import Path
from typing import Any, List, Union
import zipfile

from .domain import Cardapio
from .errors import ERR_ARQUIVO_EXISTENTE, PrecificacaoError
from .menu_matrix import AnaliseCardapio, Quadrante

CARACTERES_INJECAO = ("=", "+", "-", "@", "\t", "\r")


def sanitizar_csv(valor: Any) -> str:
    """Neutraliza tentativa de injeção de fórmulas em planilhas (DDE/CSV injection)."""
    s = str(valor)
    if s and s[0] in CARACTERES_INJECAO:
        return f"'{s}"
    return s


def centavos_para_reais_str(centavos: int) -> str:
    """Converte centavos inteiros para formato monetário brasileiro 'R$ 12,50'."""
    sinal = "-" if centavos < 0 else ""
    abs_cent = abs(centavos)
    inteiro = abs_cent // 100
    resto = abs_cent % 100
    return f"{sinal}R$ {inteiro},{resto:02d}"


def exportar_fichas_csv(analise: AnaliseCardapio, caminho: Union[str, Path]) -> None:
    """Gera CSV sanitizado com a análise consolidada de cada ficha técnica."""
    caminho_p = Path(caminho)
    linhas: List[str] = [
        "codigo;nome;categoria;rendimento;custo_porcao;preco_venda;cmv_atual;cmv_alvo;preco_sugerido;margem_unitaria;vendas;faturamento;margem_total;quadrante;recomendacao"
    ]

    for item in analise.itens:
        f = item.ficha
        cmv_atual_str = f"{f.cmv_atual_frac.numerator * 100 // f.cmv_atual_frac.denominator}%" if f.cmv_atual_frac.denominator > 0 else "0%"
        cmv_alvo_str = f"{f.cmv_alvo_num * 100 // f.cmv_alvo_den}%"

        colunas = [
            sanitizar_csv(f.codigo),
            sanitizar_csv(f.nome),
            sanitizar_csv(f.categoria),
            str(f.rendimento_porcoes),
            centavos_para_reais_str(f.custo_porcao_centavos),
            centavos_para_reais_str(f.preco_venda_centavos),
            cmv_atual_str,
            cmv_alvo_str,
            centavos_para_reais_str(f.preco_sugerido_cmv_alvo_centavos),
            centavos_para_reais_str(f.margem_contribuicao_centavos),
            str(f.vendas_periodo),
            centavos_para_reais_str(f.faturamento_total_centavos),
            centavos_para_reais_str(f.margem_total_periodo_centavos),
            item.quadrante.value,
            sanitizar_csv(item.recomendacao),
        ]
        linhas.append(";".join(colunas))

    conteudo = "\n".join(linhas) + "\n"
    caminho_p.write_text(conteudo, encoding="utf-8")


def exportar_insumos_csv(cardapio: Cardapio, caminho: Union[str, Path]) -> None:
    """Gera CSV sanitizado do cadastro de insumos e fatores de correção."""
    caminho_p = Path(caminho)
    linhas: List[str] = [
        "codigo;nome;unidade;quantidade_embalagem;custo_embalagem;fator_correcao;custo_unitario_frac"
    ]

    for ins in sorted(cardapio.insumos.values(), key=lambda i: i.codigo):
        fc_str = f"{ins.fator_correcao_num}/{ins.fator_correcao_den}"
        custo_unit_str = f"{ins.custo_unitario_frac.numerator}/{ins.custo_unitario_frac.denominator} centavos/{ins.unidade.value}"
        colunas = [
            sanitizar_csv(ins.codigo),
            sanitizar_csv(ins.nome),
            ins.unidade.value,
            str(ins.quantidade_embalagem),
            centavos_para_reais_str(ins.custo_embalagem_centavos),
            fc_str,
            custo_unit_str,
        ]
        linhas.append(";".join(colunas))

    conteudo = "\n".join(linhas) + "\n"
    caminho_p.write_text(conteudo, encoding="utf-8")


def gerar_relatorio_markdown(analise: AnaliseCardapio) -> str:
    """Gera relatório executivo de engenharia de cardápio e CMV."""
    faturamento_str = centavos_para_reais_str(analise.faturamento_total_centavos)
    custo_str = centavos_para_reais_str(analise.custo_total_centavos)
    margem_str = centavos_para_reais_str(analise.margem_total_centavos)
    cmv_ponderado_pct = (
        f"{analise.cmv_medio_ponderado_frac.numerator * 100 // analise.cmv_medio_ponderado_frac.denominator}%"
        if analise.cmv_medio_ponderado_frac.denominator > 0 else "0%"
    )
    margem_ponderada_pct = (
        f"{analise.margem_ponderada_percentual_frac.numerator * 100 // analise.cmv_medio_ponderado_frac.denominator}%"
        if analise.cmv_medio_ponderado_frac.denominator > 0 else "0%"
    )

    linhas = [
        f"# Relatório de Engenharia de Cardápio e CMV — {analise.estabelecimento}",
        f"**Período de Análise:** {analise.periodo}",
        f"**Auditoria e Metodologia:** Matriz Kasavana & Smith (Miller) · LOFRANO TECNOLOGIA",
        "",
        "---",
        "",
        "## 1. Resumo Executivo e Indicadores Globais",
        "",
        f"- **Total de Fichas Técnicas Analisadas:** {analise.total_fichas}",
        f"- **Volume de Porções Comercializadas:** {analise.total_porcoes_vendidas} unidades",
        f"- **Faturamento Bruto Consolidado:** {faturamento_str}",
        f"- **Custo de Mercadorias Vendidas (CMV Global):** {custo_str} ({cmv_ponderado_pct} da receita)",
        f"- **Margem de Contribuição Bruta:** {margem_str}",
        "",
        "### Distribuição dos Itens por Quadrante",
        f"- **⭐ Estrelas (Alta Saída, Alta Margem):** {analise.contagem_quadrantes[Quadrante.ESTRELA]} itens",
        f"- **🐴 Burros de Carga (Alta Saída, Baixa Margem):** {analise.contagem_quadrantes[Quadrante.BURRO_DE_CARGA]} itens",
        f"- **🧩 Quebra-Cabeças (Baixa Saída, Alta Margem):** {analise.contagem_quadrantes[Quadrante.QUEBRA_CABECA]} itens",
        f"- **🐕 Cães (Baixa Saída, Baixa Margem):** {analise.contagem_quadrantes[Quadrante.CAO]} itens",
        "",
        "---",
        "",
        "## 2. Matriz Detalhada de Engenharia de Cardápio",
        "",
        "| Código | Item | Categoria | Vendas | Preço Atual | Custo Porção | CMV Atual | CMV Alvo | Preço Sugerido | Margem Unit. | Quadrante |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]

    for item in analise.itens:
        f = item.ficha
        cmv_atual_str = f"{f.cmv_atual_frac.numerator * 100 // f.cmv_atual_frac.denominator}%" if f.cmv_atual_frac.denominator > 0 else "0%"
        cmv_alvo_str = f"{f.cmv_alvo_num * 100 // f.cmv_alvo_den}%"
        linhas.append(
            f"| `{f.codigo}` | {f.nome} | {f.categoria} | {f.vendas_periodo} | "
            f"{centavos_para_reais_str(f.preco_venda_centavos)} | "
            f"{centavos_para_reais_str(f.custo_porcao_centavos)} | "
            f"{cmv_atual_str} | {cmv_alvo_str} | "
            f"{centavos_para_reais_str(f.preco_sugerido_cmv_alvo_centavos)} | "
            f"{centavos_para_reais_str(f.margem_contribuicao_centavos)} | "
            f"**{item.quadrante.value}** |"
        )

    linhas.extend([
        "",
        "---",
        "",
        "## 3. Recomendações e Plano de Ação Estratégico",
        "",
    ])

    for quad in [Quadrante.ESTRELA, Quadrante.BURRO_DE_CARGA, Quadrante.QUEBRA_CABECA, Quadrante.CAO]:
        itens_quad = [it for it in analise.itens if it.quadrante == quad]
        if not itens_quad:
            continue

        linhas.append(f"### {quad.value} ({len(itens_quad)} itens)")
        linhas.append(f"> {itens_quad[0].recomendacao}")
        linhas.append("")
        for it in itens_quad:
            f = it.ficha
            linhas.append(
                f"- **{f.nome}** (`{f.codigo}`): Vendas: {f.vendas_periodo} un | "
                f"Preço: {centavos_para_reais_str(f.preco_venda_centavos)} | "
                f"Margem Unit.: {centavos_para_reais_str(f.margem_contribuicao_centavos)} | "
                f"Preço Sugerido CMV: {centavos_para_reais_str(f.preco_sugerido_cmv_alvo_centavos)}"
            )
        linhas.append("")

    linhas.extend([
        "---",
        "",
        "## 4. Garantia de Integridade e Aritmética",
        "- **Zero Float**: Todos os custos, preços e saldos são processados em centavos inteiros (`int`) e frações exatas (`Fraction`).",
        "- **Segurança CSV**: Todas as células de texto são higienizadas contra injeção de código em planilhas.",
        "- **Metodologia**: Algoritmo formal de Kasavana & Smith com limiar de 70% da popularidade esperada e média ponderada de margem.",
        "",
        "*LOFRANO TECNOLOGIA — Sistemas de Alta Precisão Contábil e Operacional.*",
    ])

    return "\n".join(linhas) + "\n"


def criar_pacote_zip_deterministico(
    caminho_zip: Union[str, Path],
    arquivos: List[tuple[str, bytes]],
) -> None:
    """Cria arquivo ZIP determinístico e bit-a-bit reprodutível com proteção contra sobrescrita."""
    caminho_p = Path(caminho_zip)
    if caminho_p.exists():
        raise PrecificacaoError(
            f"Arquivo de destino já existe: {caminho_p}",
            ERR_ARQUIVO_EXISTENTE,
        )

    # Modo atômico de abertura exclusivo
    fd = os.open(str(caminho_p), os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0), 0o644)
    with os.fdopen(fd, "wb") as f_out:
        with zipfile.ZipFile(f_out, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            # Data fixa determinística: 2026-11-10 00:00:00
            data_fixa = (2026, 11, 10, 0, 0, 0)
            for nome_arco, dados_bytes in sorted(arquivos, key=lambda x: x[0]):
                zinfo = zipfile.ZipInfo(filename=nome_arco, date_time=data_fixa)
                zinfo.compress_type = zipfile.ZIP_DEFLATED
                zinfo.external_attr = 0o644 << 16
                zf.writestr(zinfo, dados_bytes)
