#!/usr/bin/env python3
"""Gera artefatos visuais (SVG e PNG via Chrome Headless), relatórios e arquivos de release.

LOFRANO TECNOLOGIA.
"""

import hashlib
import os
from pathlib import Path
import subprocess
import sys

# Adicionar src ao sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from precificacao_cardapio.calculator import calcular_ficha
from precificacao_cardapio.codecs import carregar_cardapio, serializar_json_canonico, analise_para_dict
from precificacao_cardapio.exports import (
    criar_pacote_zip_deterministico,
    exportar_fichas_csv,
    exportar_insumos_csv,
    gerar_relatorio_markdown,
)
from precificacao_cardapio.menu_matrix import classificar_cardapio
from precificacao_cardapio.svg_report import gerar_painel_svg


def main() -> int:
    raiz = Path(__file__).resolve().parent.parent
    exemplar = raiz / "exemplares" / "cardapio_restaurante.json"
    docs_dir = raiz / "docs"
    docs_dir.mkdir(exist_ok=True)
    release_dir = raiz / "release" / "v1.0.0"
    release_dir.mkdir(parents=True, exist_ok=True)

    print(f"[*] Processando cardápio exemplar: {exemplar}")
    cardapio = carregar_cardapio(exemplar)
    fichas_calc = [calcular_ficha(f, cardapio.insumos) for f in cardapio.fichas]
    analise = classificar_cardapio(cardapio.nome_estabelecimento, cardapio.periodo, fichas_calc)

    # 1. Gerar SVG
    svg_conteudo = gerar_painel_svg(analise)
    svg_path = docs_dir / "exemplo.svg"
    svg_path.write_text(svg_conteudo, encoding="utf-8")
    print(f"[OK] SVG gerado: {svg_path}")

    # 2. Renderizar PNG via Chrome Headless em 1440x900
    png_path = docs_dir / "exemplo.png"
    print(f"[*] Renderizando PNG 1440x900 via Chrome headless...")
    cmd_chrome = [
        "google-chrome",
        "--headless=new",
        "--disable-gpu",
        "--no-sandbox",
        "--window-size=1440,900",
        f"--screenshot={png_path}",
        str(svg_path.resolve()),
    ]
    res = subprocess.run(cmd_chrome, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"Aviso: google-chrome retornou {res.returncode}: {res.stderr}", file=sys.stderr)
        # Tentar chromium se google-chrome falhar
        cmd_chromium = [
            "chromium",
            "--headless=new",
            "--disable-gpu",
            "--no-sandbox",
            "--window-size=1440,900",
            f"--screenshot={png_path}",
            str(svg_path.resolve()),
        ]
        res2 = subprocess.run(cmd_chromium, capture_output=True, text=True)
        if res2.returncode != 0:
            print(f"Falha ao gerar screenshot com chromium: {res2.stderr}", file=sys.stderr)
    print(f"[OK] PNG gerado: {png_path} ({png_path.stat().st_size} bytes)")

    # 3. Gerar pacote ZIP
    zip_path = release_dir / "exemplo-cardapio.zip"
    if zip_path.exists():
        zip_path.unlink()

    tmp_fichas_csv = Path("/tmp/fichas_temp.csv")
    tmp_insumos_csv = Path("/tmp/insumos_temp.csv")
    exportar_fichas_csv(analise, tmp_fichas_csv)
    exportar_insumos_csv(cardapio, tmp_insumos_csv)

    analise_dict = analise_para_dict(analise)
    analise_json_bytes = serializar_json_canonico(analise_dict).encode("utf-8")
    relatorio_md_bytes = gerar_relatorio_markdown(analise).encode("utf-8")

    arquivos_zip = [
        ("entrada.json", exemplar.read_bytes()),
        ("analise_cardapio.json", analise_json_bytes),
        ("fichas_tecnicas.csv", tmp_fichas_csv.read_bytes()),
        ("insumos.csv", tmp_insumos_csv.read_bytes()),
        ("relatorio.md", relatorio_md_bytes),
        ("painel.svg", svg_conteudo.encode("utf-8")),
    ]
    criar_pacote_zip_deterministico(zip_path, arquivos_zip)
    if tmp_fichas_csv.exists():
        tmp_fichas_csv.unlink()
    if tmp_insumos_csv.exists():
        tmp_insumos_csv.unlink()
    print(f"[OK] ZIP determinístico gerado: {zip_path}")

    # Copiar PNG para a pasta de release
    rel_png = release_dir / "exemplo.png"
    rel_png.write_bytes(png_path.read_bytes())

    # 4. Construir wheel e sdist
    print("[*] Construindo pacotes com setuptools.build_meta...")
    dist_dir = raiz / "dist"
    dist_dir.mkdir(exist_ok=True)
    import setuptools.build_meta as b
    b.build_sdist(str(dist_dir))
    b.build_wheel(str(dist_dir))
    for item in dist_dir.glob("*"):
        alvo = release_dir / item.name
        alvo.write_bytes(item.read_bytes())
        print(f"[OK] Pacote copiado para release: {alvo.name}")

    # 5. Gerar SHA256SUMS
    print("[*] Gerando SHA256SUMS...")
    linhas_sha = []
    for p in sorted(release_dir.iterdir()):
        if p.name == "SHA256SUMS":
            continue
        h = hashlib.sha256(p.read_bytes()).hexdigest()
        linhas_sha.append(f"{h}  {p.name}")

    sha_file = release_dir / "SHA256SUMS"
    sha_file.write_text("\n".join(linhas_sha) + "\n", encoding="utf-8")
    print(f"[OK] SHA256SUMS gerado em: {sha_file}")
    print(sha_file.read_text(encoding="utf-8"))

    return 0


if __name__ == "__main__":
    sys.exit(main())
