"""Gerador de painel analítico SVG vetorial (1440x900) para Engenharia de Cardápio e CMV.

LOFRANO TECNOLOGIA.
"""

from fractions import Fraction
import html
from typing import List

from .exports import centavos_para_reais_str
from .menu_matrix import AnaliseCardapio, Quadrante


def gerar_painel_svg(analise: AnaliseCardapio) -> str:
    """Gera visualização SVG completa em 1440x900 da matriz de cardápio e CMV."""
    w = 1440
    h = 900

    faturamento_str = centavos_para_reais_str(analise.faturamento_total_centavos)
    custo_str = centavos_para_reais_str(analise.custo_total_centavos)
    margem_str = centavos_para_reais_str(analise.margem_total_centavos)
    cmv_pct = (
        f"{analise.cmv_medio_ponderado_frac.numerator * 100 // analise.cmv_medio_ponderado_frac.denominator}%"
        if analise.cmv_medio_ponderado_frac.denominator > 0 else "0%"
    )

    qtd_estrelas = analise.contagem_quadrantes[Quadrante.ESTRELA]
    qtd_burros = analise.contagem_quadrantes[Quadrante.BURRO_DE_CARGA]
    qtd_puzzles = analise.contagem_quadrantes[Quadrante.QUEBRA_CABECA]
    qtd_caes = analise.contagem_quadrantes[Quadrante.CAO]

    # Dimensões do gráfico de dispersão (Scatter Plot)
    gx = 50
    gy = 200
    gw = 820
    gh = 530

    # Determinar limites para mapeamento no gráfico
    max_vendas = max((it.ficha.vendas_periodo for it in analise.itens), default=100)
    if max_vendas <= 0:
        max_vendas = 100
    max_vendas = int(max_vendas * 1.15)  # folga de 15%

    max_margem = max((it.ficha.margem_contribuicao_centavos for it in analise.itens), default=5000)
    min_margem = min((it.ficha.margem_contribuicao_centavos for it in analise.itens), default=0)
    if min_margem > 0:
        min_margem = 0
    if max_margem <= min_margem:
        max_margem = min_margem + 5000
    faixa_margem = max_margem - min_margem

    # Linhas de referência no gráfico
    # Limiar de vendas absoluto aproximado = limiar_pop_frac * total_vendas
    if analise.itens and analise.total_porcoes_vendidas > 0:
        limiar_vendas_frac = analise.itens[0].limiar_popularidade_frac * analise.total_porcoes_vendidas
        vendas_corte = round(limiar_vendas_frac.numerator / limiar_vendas_frac.denominator)
    else:
        vendas_corte = max_vendas // 2

    margem_corte = analise.itens[0].margem_media_referencia_centavos if analise.itens else 0

    # Coordenadas em pixels das linhas de corte
    def x_pixel(v: int) -> float:
        ratio = max(0.0, min(1.0, v / max_vendas))
        return gx + ratio * gw

    def y_pixel(m: int) -> float:
        ratio = max(0.0, min(1.0, (m - min_margem) / faixa_margem))
        return (gy + gh) - ratio * gh

    px_corte_x = x_pixel(vendas_corte)
    px_corte_y = y_pixel(margem_corte)

    cores_quadrante = {
        Quadrante.ESTRELA: ("#10b981", "#064e3b"),
        Quadrante.BURRO_DE_CARGA: ("#38bdf8", "#0c4a6e"),
        Quadrante.QUEBRA_CABECA: ("#fbbf24", "#78350f"),
        Quadrante.CAO: ("#f87171", "#7f1d1d"),
    }

    pontos_svg: List[str] = []
    for it in analise.itens:
        f = it.ficha
        cx = x_pixel(f.vendas_periodo)
        cy = y_pixel(f.margem_contribuicao_centavos)
        cor_borda, cor_fundo = cores_quadrante[it.quadrante]
        preco_fmt = centavos_para_reais_str(f.preco_venda_centavos)
        mc_fmt = centavos_para_reais_str(f.margem_contribuicao_centavos)

        pontos_svg.append(f"""
          <g class="ponto-item">
            <circle cx="{cx:.1f}" cy="{cy:.1f}" r="11" fill="{cor_borda}" fill-opacity="0.25" stroke="{cor_borda}" stroke-width="2.5" />
            <circle cx="{cx:.1f}" cy="{cy:.1f}" r="4" fill="{cor_borda}" />
            <text x="{cx + 14:.1f}" y="{cy + 4:.1f}" font-family="sans-serif" font-size="11" font-weight="600" fill="#f8fafc">
              {html.escape(f.codigo)}
            </text>
            <title>{html.escape(f.nome)} ({html.escape(f.codigo)})&#10;Vendas: {f.vendas_periodo} un&#10;Preço: {preco_fmt}&#10;Margem: {mc_fmt}&#10;Quadrante: {it.quadrante.value}</title>
          </g>
        """)

    # Tabela lateral dos principais itens
    tabela_itens_svg: List[str] = []
    ty_inicio = 260
    for idx, it in enumerate(analise.itens[:10]):
        f = it.ficha
        cor_badge, _ = cores_quadrante[it.quadrante]
        y_pos = ty_inicio + (idx * 45)
        tabela_itens_svg.append(f"""
          <g transform="translate(900, {y_pos})">
            <rect x="0" y="0" width="490" height="38" rx="6" fill="#1e293b" fill-opacity="0.6" stroke="#334155" stroke-width="1" />
            <rect x="0" y="0" width="4" height="38" rx="2" fill="{cor_badge}" />
            <text x="14" y="24" font-family="sans-serif" font-size="12" font-weight="700" fill="#f1f5f9">
              {html.escape(f.codigo)} · {html.escape(f.nome[:22])}
            </text>
            <text x="260" y="24" font-family="sans-serif" font-size="11" fill="#94a3b8">
              {f.vendas_periodo} un | {centavos_para_reais_str(f.preco_venda_centavos)}
            </text>
            <rect x="390" y="9" width="90" height="20" rx="4" fill="{cor_badge}" fill-opacity="0.18" stroke="{cor_badge}" stroke-width="1" />
            <text x="435" y="23" font-family="sans-serif" font-size="9" font-weight="700" text-anchor="middle" fill="{cor_badge}">
              {it.quadrante.value[:10]}
            </text>
          </g>
        """)

    svg_content = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}">
  <defs>
    <linearGradient id="bg-grad" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#0f172a" />
      <stop offset="100%" stop-color="#020617" />
    </linearGradient>
    <linearGradient id="card-grad" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#1e293b" />
      <stop offset="100%" stop-color="#0f172a" />
    </linearGradient>
  </defs>

  <!-- Fundo Principal -->
  <rect width="{w}" height="{h}" fill="url(#bg-grad)" />

  <!-- Cabeçalho -->
  <g transform="translate(50, 40)">
    <text x="0" y="28" font-family="sans-serif" font-size="24" font-weight="800" fill="#f8fafc" letter-spacing="0.5">
      LOFRANO TECNOLOGIA · ENGENHARIA DE CARDÁPIO &amp; CMV ALVO
    </text>
    <text x="0" y="52" font-family="sans-serif" font-size="13" font-weight="500" fill="#94a3b8">
      Matriz Kasavana &amp; Smith (Miller) · Custos em Centavos Inteiros e Frações Racionais Exatas (Zero Float)
    </text>
    <g transform="translate(980, 0)">
      <rect x="0" y="8" width="360" height="42" rx="8" fill="#1e293b" stroke="#334155" stroke-width="1" />
      <text x="180" y="26" font-family="sans-serif" font-size="11" font-weight="600" text-anchor="middle" fill="#38bdf8">
        {html.escape(analise.estabelecimento)}
      </text>
      <text x="180" y="42" font-family="sans-serif" font-size="11" text-anchor="middle" fill="#94a3b8">
        Período: {html.escape(analise.periodo)} · 10/11/2026
      </text>
    </g>
  </g>

  <!-- 4 Cards de Indicadores (KPIs) -->
  <g transform="translate(50, 115)">
    <!-- Card 1: Faturamento -->
    <g transform="translate(0, 0)">
      <rect width="310" height="68" rx="8" fill="url(#card-grad)" stroke="#334155" stroke-width="1" />
      <text x="18" y="24" font-family="sans-serif" font-size="11" font-weight="600" fill="#94a3b8">FATURAMENTO TOTAL</text>
      <text x="18" y="52" font-family="sans-serif" font-size="20" font-weight="800" fill="#38bdf8">{faturamento_str}</text>
    </g>
    <!-- Card 2: CMV Global -->
    <g transform="translate(340, 0)">
      <rect width="310" height="68" rx="8" fill="url(#card-grad)" stroke="#334155" stroke-width="1" />
      <text x="18" y="24" font-family="sans-serif" font-size="11" font-weight="600" fill="#94a3b8">CMV MÉDIO PONDERADO</text>
      <text x="18" y="52" font-family="sans-serif" font-size="20" font-weight="800" fill="#f59e0b">{cmv_pct} <tspan font-size="12" font-weight="500" fill="#94a3b8">({custo_str})</tspan></text>
    </g>
    <!-- Card 3: Margem Contribuição -->
    <g transform="translate(680, 0)">
      <rect width="310" height="68" rx="8" fill="url(#card-grad)" stroke="#334155" stroke-width="1" />
      <text x="18" y="24" font-family="sans-serif" font-size="11" font-weight="600" fill="#94a3b8">MARGEM CONTRIBUIÇÃO TOTAL</text>
      <text x="18" y="52" font-family="sans-serif" font-size="20" font-weight="800" fill="#10b981">{margem_str}</text>
    </g>
    <!-- Card 4: Matriz Quadrantes -->
    <g transform="translate(1020, 0)">
      <rect width="320" height="68" rx="8" fill="url(#card-grad)" stroke="#334155" stroke-width="1" />
      <text x="18" y="24" font-family="sans-serif" font-size="11" font-weight="600" fill="#94a3b8">DISTRIBUIÇÃO MATRIZ</text>
      <text x="18" y="52" font-family="sans-serif" font-size="13" font-weight="700" fill="#f8fafc">
        ⭐ {qtd_estrelas}  🐴 {qtd_burros}  🧩 {qtd_puzzles}  🐕 {qtd_caes}
      </text>
    </g>
  </g>

  <!-- Área do Gráfico Scatter Plot -->
  <g transform="translate(0, 0)">
    <!-- Fundo do Gráfico -->
    <rect x="{gx}" y="{gy}" width="{gw}" height="{gh}" rx="8" fill="#0b1120" stroke="#1e293b" stroke-width="1.5" />

    <!-- 4 Áreas de Fundo de Quadrantes -->
    <!-- Superior Esquerdo: QUEBRA-CABEÇA -->
    <rect x="{gx}" y="{gy}" width="{px_corte_x - gx}" height="{px_corte_y - gy}" fill="#78350f" fill-opacity="0.08" />
    <text x="{gx + 20}" y="{gy + 30}" font-family="sans-serif" font-size="13" font-weight="800" fill="#fbbf24" fill-opacity="0.6">
      🧩 QUEBRA-CABEÇA (Alta Margem, Baixa Venda)
    </text>

    <!-- Superior Direito: ESTRELA -->
    <rect x="{px_corte_x}" y="{gy}" width="{gx + gw - px_corte_x}" height="{px_corte_y - gy}" fill="#064e3b" fill-opacity="0.08" />
    <text x="{gx + gw - 20}" y="{gy + 30}" font-family="sans-serif" font-size="13" font-weight="800" text-anchor="end" fill="#10b981" fill-opacity="0.8">
      ⭐ ESTRELA (Alta Margem, Alta Venda)
    </text>

    <!-- Inferior Esquerdo: CÃO -->
    <rect x="{gx}" y="{px_corte_y}" width="{px_corte_x - gx}" height="{gy + gh - px_corte_y}" fill="#7f1d1d" fill-opacity="0.08" />
    <text x="{gx + 20}" y="{gy + gh - 20}" font-family="sans-serif" font-size="13" font-weight="800" fill="#f87171" fill-opacity="0.6">
      🐕 CÃO / ABACAXI (Baixa Margem, Baixa Venda)
    </text>

    <!-- Inferior Direito: BURRO DE CARGA -->
    <rect x="{px_corte_x}" y="{px_corte_y}" width="{gx + gw - px_corte_x}" height="{gy + gh - px_corte_y}" fill="#0c4a6e" fill-opacity="0.08" />
    <text x="{gx + gw - 20}" y="{gy + gh - 20}" font-family="sans-serif" font-size="13" font-weight="800" text-anchor="end" fill="#38bdf8" fill-opacity="0.8">
      🐴 BURRO DE CARGA (Baixa Margem, Alta Venda)
    </text>

    <!-- Linhas Divisórias Tracejadas -->
    <line x1="{px_corte_x}" y1="{gy}" x2="{px_corte_x}" y2="{gy + gh}" stroke="#475569" stroke-width="1.5" stroke-dasharray="6,4" />
    <line x1="{gx}" y1="{px_corte_y}" x2="{gx + gw}" y2="{px_corte_y}" stroke="#475569" stroke-width="1.5" stroke-dasharray="6,4" />

    <!-- Rótulos dos Eixos -->
    <text x="{gx + gw // 2}" y="{gy + gh + 32}" font-family="sans-serif" font-size="12" font-weight="700" text-anchor="middle" fill="#94a3b8">
      POPULARIDADE (VOLUME DE VENDAS NO PERÍODO) →
    </text>
    <text transform="rotate(-90)" x="-{gy + gh // 2}" y="{gx - 18}" font-family="sans-serif" font-size="12" font-weight="700" text-anchor="middle" fill="#94a3b8">
      MARGEM DE CONTRIBUIÇÃO UNITÁRIA (R$) →
    </text>

    <!-- Pontos do Cardápio -->
    {"".join(pontos_svg)}
  </g>

  <!-- Painel Lateral: Tabela de Itens e Decisões -->
  <g transform="translate(0, 0)">
    <rect x="890" y="{gy}" width="500" height="{gh}" rx="8" fill="#0b1120" stroke="#1e293b" stroke-width="1.5" />
    <text x="910" y="{gy + 34}" font-family="sans-serif" font-size="14" font-weight="800" fill="#f8fafc">
      CLASSIFICAÇÃO OPERACIONAL E PREÇOS
    </text>
    <text x="910" y="{gy + 52}" font-family="sans-serif" font-size="11" fill="#64748b">
      Ranking de itens, margem de contribuição e ações imediatas
    </text>
    {"".join(tabela_itens_svg)}
  </g>

  <!-- Rodapé de Auditoria e Integridade -->
  <g transform="translate(50, 785)">
    <rect width="1340" height="75" rx="8" fill="#0f172a" stroke="#1e293b" stroke-width="1" />
    <text x="24" y="28" font-family="sans-serif" font-size="12" font-weight="700" fill="#38bdf8">
      GARANTIA DE INTEGRIDADE CONTÁBIL &amp; ARITMÉTICA
    </text>
    <text x="24" y="48" font-family="sans-serif" font-size="11" fill="#94a3b8">
      • Zero float: todos os custos, preços e rateios em centavos inteiros (int) e frações exatas (Fraction).
    </text>
    <text x="24" y="64" font-family="sans-serif" font-size="11" fill="#94a3b8">
      • Metodologia Kasavana &amp; Smith: limiar de popularidade a 70% da média ponderada e margem referencial contra média do mix.
    </text>
    <text x="1316" y="46" font-family="sans-serif" font-size="11" font-weight="700" text-anchor="end" fill="#64748b">
      LOFRANO TECNOLOGIA
    </text>
  </g>
</svg>
"""
    return svg_content
