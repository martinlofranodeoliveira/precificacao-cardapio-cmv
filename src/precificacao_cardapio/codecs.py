"""Codec JSON canônico e determinístico para fichas técnicas e análise de cardápio.

Regras canônicas LOFRANO TECNOLOGIA:
- Rejeição estrita de BOM (\xef\xbb\xbf).
- Rejeição estrita de chaves duplicadas em objetos JSON.
- Rejeição estrita de tipos numéricos com ponto flutuante (float).
- Limite máximo de profundidade de aninhamento (<= 32).
- Serialização determinística com chaves ordenadas e indentação padrão de 2 espaços.
"""

from fractions import Fraction
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Union

from .domain import Cardapio, FichaTecnica, Insumo, ItemFicha, UnidadeMedida
from .errors import (
    ERR_BOM_PROIBIDO,
    ERR_CHAVE_DUPLICADA,
    ERR_FLOAT_PROIBIDO,
    ERR_JSON_INVALIDO,
    ERR_PROFUNDIDADE_EXCEDIDA,
    ErroCodec,
)
from .menu_matrix import AnaliseCardapio

LIMITE_PROFUNDIDADE_MAXIMA = 32


def _verificar_profundidade(obj: Any, nivel_atual: int = 0) -> None:
    if nivel_atual > LIMITE_PROFUNDIDADE_MAXIMA:
        raise ErroCodec(
            f"Profundidade de aninhamento do JSON excedeu o limite máximo de {LIMITE_PROFUNDIDADE_MAXIMA}.",
            ERR_PROFUNDIDADE_EXCEDIDA,
        )
    if isinstance(obj, dict):
        for v in obj.values():
            _verificar_profundidade(v, nivel_atual + 1)
    elif isinstance(obj, list):
        for item in obj:
            _verificar_profundidade(item, nivel_atual + 1)


def _object_pairs_hook_sem_duplicadas(pairs: List[tuple]) -> Dict[str, Any]:
    resultado: Dict[str, Any] = {}
    for chave, valor in pairs:
        if chave in resultado:
            raise ErroCodec(
                f"Chave duplicada encontrada no JSON: '{chave}'.",
                ERR_CHAVE_DUPLICADA,
            )
        resultado[chave] = valor
    return resultado


def _parse_float_proibido(valor_str: str) -> None:
    raise ErroCodec(
        f"Uso de ponto flutuante (float) é proibido pelo padrão de integridade: '{valor_str}'. "
        "Utilize inteiros (centavos, gramas, mililitros ou numeradores/denominadores fracionários).",
        ERR_FLOAT_PROIBIDO,
    )


def decodificar_json_canonico(texto_ou_bytes: Union[str, bytes]) -> Any:
    """Decodifica texto ou bytes JSON sob regras canônicas restritas."""
    if isinstance(texto_ou_bytes, bytes):
        if texto_ou_bytes.startswith(b"\xef\xbb\xbf"):
            raise ErroCodec("Byte Order Mark (BOM) UTF-8 detectado e proibido.", ERR_BOM_PROIBIDO)
        try:
            texto = texto_ou_bytes.decode("utf-8")
        except UnicodeDecodeError as e:
            raise ErroCodec(f"Erro na decodificação UTF-8: {e}", ERR_JSON_INVALIDO)
    else:
        if texto_ou_bytes.startswith("\ufeff"):
            raise ErroCodec("Byte Order Mark (BOM) UTF-8 detectado e proibido.", ERR_BOM_PROIBIDO)
        texto = texto_ou_bytes

    try:
        dados = json.loads(
            texto,
            object_pairs_hook=_object_pairs_hook_sem_duplicadas,
            parse_float=_parse_float_proibido,
        )
    except json.JSONDecodeError as e:
        raise ErroCodec(f"Sintaxe JSON inválida: {e}", ERR_JSON_INVALIDO)

    _verificar_profundidade(dados)
    return dados


def _verificar_sem_float(obj: Any) -> None:
    if isinstance(obj, float):
        raise ErroCodec("Tentativa de serializar float detectada.", ERR_FLOAT_PROIBIDO)
    if isinstance(obj, dict):
        for v in obj.values():
            _verificar_sem_float(v)
    elif isinstance(obj, (list, tuple)):
        for item in obj:
            _verificar_sem_float(item)


def serializar_json_canonico(obj: Any) -> str:
    """Serializa estruturas para JSON canônico determinístico com indentação 2."""
    _verificar_sem_float(obj)

    def _converter(o: Any) -> Any:
        if isinstance(o, Fraction):
            return {"num": o.numerator, "den": o.denominator}
        if isinstance(o, float):
            raise ErroCodec("Tentativa de serializar float detectada.", ERR_FLOAT_PROIBIDO)
        raise TypeError(f"Objeto do tipo {type(o)} não é serializável.")

    return json.dumps(
        obj,
        indent=2,
        sort_keys=True,
        ensure_ascii=False,
        default=_converter,
    ) + "\n"


def carregar_cardapio(caminho: Union[str, Path]) -> Cardapio:
    """Lê e valida um arquivo JSON de cardápio e insumos."""
    caminho_p = Path(caminho)
    if not caminho_p.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {caminho}")

    conteudo_bytes = caminho_p.read_bytes()
    dados = decodificar_json_canonico(conteudo_bytes)

    if not isinstance(dados, dict):
        raise ErroCodec("O nó raiz do arquivo deve ser um objeto JSON.", ERR_JSON_INVALIDO)

    nome_estabelecimento = dados.get("nome_estabelecimento")
    periodo = dados.get("periodo")
    insumos_brutos = dados.get("insumos")
    fichas_brutas = dados.get("fichas")

    if not isinstance(nome_estabelecimento, str) or not nome_estabelecimento.strip():
        raise ErroCodec("Campo 'nome_estabelecimento' é obrigatório e deve ser texto.", ERR_JSON_INVALIDO)
    if not isinstance(periodo, str) or not periodo.strip():
        raise ErroCodec("Campo 'periodo' é obrigatório e deve ser texto.", ERR_JSON_INVALIDO)
    if not isinstance(insumos_brutos, list):
        raise ErroCodec("Campo 'insumos' deve ser uma lista de insumos cadastrados.", ERR_JSON_INVALIDO)
    if not isinstance(fichas_brutas, list):
        raise ErroCodec("Campo 'fichas' deve ser uma lista de fichas técnicas.", ERR_JSON_INVALIDO)

    # Decodificar Insumos
    mapa_insumos: Dict[str, Insumo] = {}
    for idx, item in enumerate(insumos_brutos):
        if not isinstance(item, dict):
            raise ErroCodec(f"Insumo no índice {idx} deve ser um objeto JSON.", ERR_JSON_INVALIDO)
        cod = item.get("codigo")
        nome = item.get("nome")
        unidade_str = item.get("unidade")
        qtd_emb = item.get("quantidade_embalagem")
        custo_emb = item.get("custo_embalagem_centavos")
        fc_num = item.get("fator_correcao_num", 1)
        fc_den = item.get("fator_correcao_den", 1)

        try:
            unidade = UnidadeMedida(unidade_str)
        except ValueError:
            raise ErroCodec(f"Unidade desconhecida no insumo '{cod}': '{unidade_str}'.", ERR_JSON_INVALIDO)

        insumo = Insumo(
            codigo=cod,
            nome=nome,
            unidade=unidade,
            quantidade_embalagem=qtd_emb,
            custo_embalagem_centavos=custo_emb,
            fator_correcao_num=fc_num,
            fator_correcao_den=fc_den,
        )
        if insumo.codigo in mapa_insumos:
            raise ErroCodec(f"Código de insumo duplicado: '{insumo.codigo}'.", ERR_CHAVE_DUPLICADA)
        mapa_insumos[insumo.codigo] = insumo

    # Decodificar Fichas Técnicas
    lista_fichas: List[FichaTecnica] = []
    for idx, item in enumerate(fichas_brutas):
        if not isinstance(item, dict):
            raise ErroCodec(f"Ficha técnica no índice {idx} deve ser um objeto JSON.", ERR_JSON_INVALIDO)
        cod = item.get("codigo")
        nome = item.get("nome")
        categoria = item.get("categoria")
        rendimento = item.get("rendimento_porcoes", 1)
        custo_emb = item.get("custo_embalagem_centavos", 0)
        preco_venda = item.get("preco_venda_centavos", 0)
        vendas = item.get("vendas_periodo", 0)
        cmv_alvo_num = item.get("cmv_alvo_num", 30)
        cmv_alvo_den = item.get("cmv_alvo_den", 100)
        taxas_num = item.get("taxas_impostos_num", 0)
        taxas_den = item.get("taxas_impostos_den", 100)
        ingredientes_brutos = item.get("ingredientes", [])

        if not isinstance(ingredientes_brutos, list):
            raise ErroCodec(f"Ingredientes da ficha '{cod}' deve ser uma lista.", ERR_JSON_INVALIDO)

        lista_ingredientes: List[ItemFicha] = []
        for i_idx, ing in enumerate(ingredientes_brutos):
            if not isinstance(ing, dict):
                raise ErroCodec(f"Ingrediente {i_idx} da ficha '{cod}' deve ser objeto JSON.", ERR_JSON_INVALIDO)
            cod_ins = ing.get("codigo_insumo")
            qtd_liq = ing.get("quantidade_liquida")
            fc_ov_num = ing.get("fator_correcao_override_num")
            fc_ov_den = ing.get("fator_correcao_override_den")
            lista_ingredientes.append(
                ItemFicha(
                    codigo_insumo=cod_ins,
                    quantidade_liquida=qtd_liq,
                    fator_correcao_override_num=fc_ov_num,
                    fator_correcao_override_den=fc_ov_den,
                )
            )

        ficha = FichaTecnica(
            codigo=cod,
            nome=nome,
            categoria=categoria,
            rendimento_porcoes=rendimento,
            ingredientes=lista_ingredientes,
            custo_embalagem_centavos=custo_emb,
            preco_venda_centavos=preco_venda,
            vendas_periodo=vendas,
            cmv_alvo_num=cmv_alvo_num,
            cmv_alvo_den=cmv_alvo_den,
            taxas_impostos_num=taxas_num,
            taxas_impostos_den=taxas_den,
        )
        lista_fichas.append(ficha)

    return Cardapio(
        nome_estabelecimento=nome_estabelecimento,
        periodo=periodo,
        insumos=mapa_insumos,
        fichas=lista_fichas,
    )


def analise_para_dict(analise: AnaliseCardapio) -> Dict[str, Any]:
    """Converte a estrutura da análise em um dicionário canônico determinístico."""
    itens_json = []
    for item in analise.itens:
        f = item.ficha
        itens_json.append({
            "codigo": f.codigo,
            "nome": f.nome,
            "categoria": f.categoria,
            "rendimento_porcoes": f.rendimento_porcoes,
            "custo_ingredientes_centavos": f.custo_ingredientes_centavos,
            "custo_embalagem_centavos": f.custo_embalagem_centavos,
            "custo_total_receita_centavos": f.custo_total_receita_centavos,
            "custo_porcao_centavos": f.custo_porcao_centavos,
            "preco_venda_centavos": f.preco_venda_centavos,
            "cmv_atual_percentual": f"{f.cmv_atual_frac.numerator * 100 // f.cmv_atual_frac.denominator}%" if f.cmv_atual_frac.denominator > 0 else "0%",
            "cmv_atual_frac": {"num": f.cmv_atual_frac.numerator, "den": f.cmv_atual_frac.denominator},
            "cmv_alvo_percentual": f"{f.cmv_alvo_num * 100 // f.cmv_alvo_den}%",
            "cmv_alvo_frac": {"num": f.cmv_alvo_num, "den": f.cmv_alvo_den},
            "margem_contribuicao_centavos": f.margem_contribuicao_centavos,
            "preco_sugerido_cmv_alvo_centavos": f.preco_sugerido_cmv_alvo_centavos,
            "vendas_periodo": f.vendas_periodo,
            "faturamento_total_centavos": f.faturamento_total_centavos,
            "custo_total_periodo_centavos": f.custo_total_periodo_centavos,
            "margem_total_periodo_centavos": f.margem_total_periodo_centavos,
            "quadrante": item.quadrante.value,
            "alta_popularidade": item.alta_popularidade,
            "alta_margem": item.alta_margem,
            "participacao_vendas_frac": {
                "num": item.participacao_vendas_frac.numerator,
                "den": item.participacao_vendas_frac.denominator,
            },
            "recomendacao": item.recomendacao,
            "ingredientes": [
                {
                    "codigo_insumo": ing.codigo_insumo,
                    "nome_insumo": ing.nome_insumo,
                    "unidade": ing.unidade,
                    "quantidade_liquida": ing.quantidade_liquida,
                    "fator_correcao_num": ing.fator_correcao_num,
                    "fator_correcao_den": ing.fator_correcao_den,
                    "quantidade_bruta_num": ing.quantidade_bruta_num,
                    "quantidade_bruta_den": ing.quantidade_bruta_den,
                    "custo_centavos": ing.custo_centavos,
                }
                for ing in f.ingredientes
            ],
        })

    return {
        "estabelecimento": analise.estabelecimento,
        "periodo": analise.periodo,
        "total_fichas": analise.total_fichas,
        "total_porcoes_vendidas": analise.total_porcoes_vendidas,
        "faturamento_total_centavos": analise.faturamento_total_centavos,
        "custo_total_centavos": analise.custo_total_centavos,
        "margem_total_centavos": analise.margem_total_centavos,
        "cmv_medio_ponderado_percentual": (
            f"{analise.cmv_medio_ponderado_frac.numerator * 100 // analise.cmv_medio_ponderado_frac.denominator}%"
            if analise.cmv_medio_ponderado_frac.denominator > 0 else "0%"
        ),
        "cmv_medio_ponderado_frac": {
            "num": analise.cmv_medio_ponderado_frac.numerator,
            "den": analise.cmv_medio_ponderado_frac.denominator,
        },
        "contagem_quadrantes": {
            k.value: v for k, v in analise.contagem_quadrantes.items()
        },
        "itens": itens_json,
    }
