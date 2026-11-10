"""precificacao_cardapio — Engenharia de cardápio, ficha técnica e CMV alvo.

LOFRANO TECNOLOGIA.
"""

from .calculator import FichaCalculada, ItemCalculado, calcular_ficha, calcular_item_ficha
from .codecs import carregar_cardapio, decodificar_json_canonico, serializar_json_canonico
from .domain import Cardapio, FichaTecnica, Insumo, ItemFicha, UnidadeMedida
from .errors import ErroCodec, ErroValidacao, PrecificacaoError
from .menu_matrix import AnaliseCardapio, ItemMatriz, Quadrante, classificar_cardapio

__version__ = "1.0.0"
__author__ = "Martin Lofrano"

__all__ = [
    "__version__",
    "Cardapio",
    "FichaTecnica",
    "Insumo",
    "ItemFicha",
    "UnidadeMedida",
    "ItemCalculado",
    "FichaCalculada",
    "calcular_item_ficha",
    "calcular_ficha",
    "Quadrante",
    "ItemMatriz",
    "AnaliseCardapio",
    "classificar_cardapio",
    "carregar_cardapio",
    "decodificar_json_canonico",
    "serializar_json_canonico",
    "PrecificacaoError",
    "ErroValidacao",
    "ErroCodec",
]
