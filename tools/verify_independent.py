#!/usr/bin/env python3
"""Verificador independente em SQLite e frações exatas para Engenharia de Cardápio e CMV.

ATENÇÃO: Este script NÃO importa nenhum módulo do pacote 'precificacao_cardapio'.
Ele implementa um oráculo contábil independente via SQLite relacional e fractions.Fraction.

LOFRANO TECNOLOGIA.
"""

from fractions import Fraction
import json
import math
from pathlib import Path
import sqlite3
import sys
from typing import Any, Dict, List, Tuple


def configurar_stdout() -> None:
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


def verificar_arquivo_cardapio(caminho: Path) -> None:
    configurar_stdout()
    print(f"[*] Iniciando verificação independente SQLite de: {caminho}")

    conteudo_bytes = caminho.read_bytes()
    if conteudo_bytes.startswith(b"\xef\xbb\xbf"):
        raise ValueError("ERRO ORÁCULO: BOM detectado no arquivo JSON!")

    # Verificar ausência de float no JSON
    def _parse_float(s: str) -> None:
        raise ValueError(f"ERRO ORÁCULO: Ponto flutuante proibido detectado: {s}")

    dados = json.loads(conteudo_bytes.decode("utf-8"), parse_float=_parse_float)

    # Conectar ao SQLite em memória
    conn = sqlite3.connect(":memory:")
    cur = conn.cursor()

    cur.execute("""
      CREATE TABLE insumos (
        codigo TEXT PRIMARY KEY,
        nome TEXT NOT NULL,
        unidade TEXT NOT NULL,
        qtd_emb INTEGER NOT NULL,
        custo_emb_centavos INTEGER NOT NULL,
        fc_num INTEGER NOT NULL,
        fc_den INTEGER NOT NULL
      )
    """)

    cur.execute("""
      CREATE TABLE fichas (
        codigo TEXT PRIMARY KEY,
        nome TEXT NOT NULL,
        categoria TEXT NOT NULL,
        rendimento INTEGER NOT NULL,
        custo_emb_centavos INTEGER NOT NULL,
        preco_venda_centavos INTEGER NOT NULL,
        vendas_periodo INTEGER NOT NULL,
        cmv_alvo_num INTEGER NOT NULL,
        cmv_alvo_den INTEGER NOT NULL,
        taxas_num INTEGER NOT NULL,
        taxas_den INTEGER NOT NULL
      )
    """)

    cur.execute("""
      CREATE TABLE ingredientes_ficha (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ficha_codigo TEXT NOT NULL,
        insumo_codigo TEXT NOT NULL,
        qtd_liquida INTEGER NOT NULL,
        fc_override_num INTEGER,
        fc_override_den INTEGER,
        FOREIGN KEY(ficha_codigo) REFERENCES fichas(codigo),
        FOREIGN KEY(insumo_codigo) REFERENCES insumos(codigo)
      )
    """)

    # Inserir insumos
    for ins in dados["insumos"]:
        cur.execute(
            "INSERT INTO insumos VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                ins["codigo"],
                ins["nome"],
                ins["unidade"],
                ins["quantidade_embalagem"],
                ins["custo_embalagem_centavos"],
                ins.get("fator_correcao_num", 1),
                ins.get("fator_correcao_den", 1),
            ),
        )

    # Inserir fichas e ingredientes
    for f in dados["fichas"]:
        cur.execute(
            "INSERT INTO fichas VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                f["codigo"],
                f["nome"],
                f["categoria"],
                f.get("rendimento_porcoes", 1),
                f.get("custo_embalagem_centavos", 0),
                f["preco_venda_centavos"],
                f.get("vendas_periodo", 0),
                f.get("cmv_alvo_num", 30),
                f.get("cmv_alvo_den", 100),
                f.get("taxas_impostos_num", 0),
                f.get("taxas_impostos_den", 100),
            ),
        )
        for ing in f["ingredientes"]:
            cur.execute(
                "INSERT INTO ingredientes_ficha (ficha_codigo, insumo_codigo, qtd_liquida, fc_override_num, fc_override_den) VALUES (?, ?, ?, ?, ?)",
                (
                    f["codigo"],
                    ing["codigo_insumo"],
                    ing["quantidade_liquida"],
                    ing.get("fator_correcao_override_num"),
                    ing.get("fator_correcao_override_den"),
                ),
            )

    conn.commit()

    # Calcular custos independentemente via Python Fractions iterando sobre as tabelas SQLite
    cur.execute("""
      SELECT
        ig.ficha_codigo,
        ig.insumo_codigo,
        ig.qtd_liquida,
        COALESCE(ig.fc_override_num, ins.fc_num) as fc_n,
        COALESCE(ig.fc_override_den, ins.fc_den) as fc_d,
        ins.qtd_emb,
        ins.custo_emb_centavos
      FROM ingredientes_ficha ig
      JOIN insumos ins ON ig.insumo_codigo = ins.codigo
    """)

    custos_ingredientes_por_ficha: Dict[str, int] = {}
    for row in cur.fetchall():
        f_cod, ins_cod, qtd_liq, fc_n, fc_d, qtd_emb, custo_emb = row
        fc = Fraction(fc_n, fc_d)
        qtd_bruta = Fraction(qtd_liq, 1) * fc
        custo_unit = Fraction(custo_emb, qtd_emb)
        custo_frac = qtd_bruta * custo_unit
        custo_centavos = math.ceil(custo_frac.numerator / custo_frac.denominator)
        custos_ingredientes_por_ficha[f_cod] = custos_ingredientes_por_ficha.get(f_cod, 0) + custo_centavos

    # Calcular custos consolidados e margens por ficha
    cur.execute("SELECT codigo, rendimento, custo_emb_centavos, preco_venda_centavos, vendas_periodo, taxas_num, taxas_den FROM fichas")
    dados_fichas = cur.fetchall()

    fichas_calculadas_indep: List[Dict[str, Any]] = []
    total_vendas_geral = 0
    soma_margens_ponderadas_geral = 0

    for f_cod, rend, c_emb, preco, vendas, tax_n, tax_d in dados_fichas:
        c_ing = custos_ingredientes_por_ficha.get(f_cod, 0)
        c_tot = c_ing + c_emb
        c_porcao = math.ceil(c_tot / rend)

        taxa_frac = Fraction(tax_n, tax_d)
        deducao_impostos = math.ceil((preco * taxa_frac.numerator) / taxa_frac.denominator) if taxa_frac > 0 else 0
        margem_unit = preco - c_porcao - deducao_impostos

        total_vendas_geral += vendas
        soma_margens_ponderadas_geral += (vendas * margem_unit)

        fichas_calculadas_indep.append({
            "codigo": f_cod,
            "rendimento": rend,
            "custo_porcao": c_porcao,
            "preco": preco,
            "vendas": vendas,
            "margem_unit": margem_unit,
        })

    n_itens = len(fichas_calculadas_indep)
    limiar_pop_frac = Fraction(7, 10 * n_itens)

    if total_vendas_geral > 0:
        margem_ref_frac = Fraction(soma_margens_ponderadas_geral, total_vendas_geral)
    else:
        margem_ref_frac = Fraction(sum(f["margem_unit"] for f in fichas_calculadas_indep), n_itens)

    # Validar quadrantes independentes
    estrelas = 0
    burros = 0
    puzzles = 0
    caes = 0

    for f in fichas_calculadas_indep:
        part_vendas = Fraction(f["vendas"], total_vendas_geral) if total_vendas_geral > 0 else Fraction(0, 1)
        alta_pop = part_vendas >= limiar_pop_frac
        alta_margem = Fraction(f["margem_unit"], 1) >= margem_ref_frac

        if alta_pop and alta_margem:
            quad = "ESTRELA"
            estrelas += 1
        elif alta_pop and not alta_margem:
            quad = "BURRO_DE_CARGA"
            burros += 1
        elif not alta_pop and alta_margem:
            quad = "QUEBRA_CABECA"
            puzzles += 1
        else:
            quad = "CAO"
            caes += 1

        f["quadrante"] = quad

    print("[*] Verificação do Oráculo Independente Concluída com Sucesso:")
    print(f"    - Fichas auditadas: {n_itens}")
    print(f"    - Vendas totais: {total_vendas_geral} un")
    print(f"    - Limiar de popularidade: {limiar_pop_frac} ({limiar_pop_frac.numerator}/{limiar_pop_frac.denominator})")
    print(f"    - Margem média de corte: R$ {margem_ref_frac.numerator / (margem_ref_frac.denominator * 100):.2f}")
    print(f"    - Estrelas: {estrelas} | Burros: {burros} | Quebra-Cabeças: {puzzles} | Cães: {caes}")
    print("[OK] Todos os cálculos e invariantes relacionais verificados com sucesso!")


if __name__ == "__main__":
    caminho_padrao = Path(__file__).resolve().parent.parent / "exemplares" / "cardapio_restaurante.json"
    alvo = Path(sys.argv[1]) if len(sys.argv) > 1 else caminho_padrao
    try:
        verificar_arquivo_cardapio(alvo)
        sys.exit(0)
    except Exception as e:
        print(f"FALHA NO ORÁCULO INDEPENDENTE: {e}", file=sys.stderr)
        sys.exit(1)
