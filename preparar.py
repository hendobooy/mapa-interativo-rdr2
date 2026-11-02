"""Converte os JSONs de pinos e ícones em dados.js.

Assim o mapa abre com dois cliques no index.html, sem precisar de servidor.
As coordenadas dos pinos são convertidas para o sistema do mapa oficial da
Rockstar (o mesmo usado pelo RDR2 Collectors Map).

Uso:
    python preparar.py
"""

import json
import math
import os
import re
from urllib.parse import quote

PASTA = os.path.dirname(os.path.abspath(__file__))

# Os pinos vêm em lat/lng Web Mercator; no zoom 6 o mundo tem 16384 px.
MUNDO_PX_Z6 = 16384

# Conversão de pixel (zoom 6) para as coordenadas do mapa da Rockstar (L.CRS.Simple).
# Calculada por mínimos quadrados casando 636 itens de coleção (pontas de flecha,
# ovos, garrafas, fósseis e flores) com as mesmas posições em
# github.com/jeanropke/RDR2CollectorsMap/data/items.json.
# Erro mediano: 0,04 unidade (~5 px no zoom 7).
CONV_X = (0.01165463803320517, 1.4210493970125113e-06, 0.01625127669082968)
CONV_Y = (-1.4003008887043492e-07, -0.011653624670062923, -0.01790461455339528)

# A origem usa o ícone de chapéu em toda a categoria "Item", que também tem cartas,
# livros, joias etc. O que se veste vai para uma categoria própria (o id é repetido em
# index.html); o resto continua em "Item" com este ícone de bolsa, na mesma cor e
# formato de pino.
VESTIVEL = re.compile(r"\b(hat|helmet|mask|skullcap|sombrero)\b", re.IGNORECASE)
ID_CHAPEUS = 100041
ICONE_ITEM = "data:image/svg+xml," + quote(
    '<svg xmlns="http://www.w3.org/2000/svg" width="33" height="44" viewBox="0 0 33 44">'
    '<path fill="#4d5382" d="M16.5 1C7.5 1 1 8 1 16c0 10 10 19 15.500 27C22 35 32 26 32 16 32 8 25.500 1 16.500 1z"/>'
    '<path fill="#fff" fill-rule="evenodd" d="M12 13a4.500 4.500 0 0 1 9 0h3.500L26 25H7l1.500-12zm2 0h5a2.500 2.500 0 0 0-5 0z"/>'
    "</svg>"
)


def caminho(nome):
    return os.path.join(PASTA, nome)


# Seu progresso pessoal; fica fora do git (ver .gitignore)
ARQ_PROGRESSO = caminho("progresso.json")


def ler_pinos():
    with open(caminho("rdr2map_pinos.json"), encoding="utf-8") as f:
        return json.load(f)


def ler_encontrados():
    """IDs encontrados em progresso.json.

    Se o arquivo ainda não existe, cria a partir do campo "encontrado" de
    rdr2map_pinos.json (onde o progresso ficava antes).
    """
    try:
        with open(ARQ_PROGRESSO, encoding="utf-8") as f:
            return json.load(f)["encontrados"]
    except FileNotFoundError:
        ids = sorted(p["id"] for p in ler_pinos() if p.get("encontrado"))
        with open(ARQ_PROGRESSO, "w", encoding="utf-8") as f:
            json.dump({"encontrados": ids}, f, indent=2)
        return ids


def para_mapa(lat, lng):
    """lat/lng Web Mercator -> (x, y) do mapa da Rockstar."""
    px = (lng + 180) / 360 * MUNDO_PX_Z6
    s = math.sin(math.radians(lat))
    py = (0.5 - math.log((1 + s) / (1 - s)) / (4 * math.pi)) * MUNDO_PX_Z6
    x = CONV_X[0] * px + CONV_X[1] * py + CONV_X[2]
    y = CONV_Y[0] * px + CONV_Y[1] * py + CONV_Y[2]
    return round(x, 4), round(y, 4)


def gerar_dados():
    pinos = ler_pinos()
    with open(caminho("rdr2map_icones.json"), encoding="utf-8") as f:
        icones = json.load(f)

    categorias = {}
    saida = []
    for p in pinos:
        do_item = p["icone"] == "hat"
        vestivel = do_item and VESTIVEL.search(p["titulo"])
        cid = ID_CHAPEUS if vestivel else p["categoria_id"]
        cat = categorias.setdefault(cid, {
            "id": cid,
            "nome": "Chapéus e máscaras" if vestivel else p["categoria"],
            "grupo": p["grupo"],
            "icone": "hat" if vestivel else "item" if do_item else p["icone"],
            "total": 0,
        })
        cat["total"] += 1

        titulo, descricao = p["titulo"], p["descricao"]
        # O site de origem deixou um aviso de "ferramenta quebrada" nesse pino
        if p["icone"] == "madam_nazar" and "Broken" in titulo:
            titulo = "Madam Nazar"
            descricao = "A localização dela muda todos os dias."

        x, y = para_mapa(p["latitude"], p["longitude"])
        icone = p["icone"] if not do_item and p["icone"] != cat["icone"] else 0
        saida.append([p["id"], cid, y, x, titulo, descricao, icone])

    dados = {
        "icones": {**{nome: i["png_base64"] for nome, i in icones.items()}, "item": ICONE_ITEM},
        "categorias": list(categorias.values()),
        "pinos": saida,
        # usado só quando o mapa é aberto sem o servidor.py
        "encontrados": ler_encontrados(),
    }
    with open(caminho("dados.js"), "w", encoding="utf-8") as f:
        f.write("// Gerado por preparar.py - não edite à mão\n")
        f.write("window.RDR2 = ")
        json.dump(dados, f, ensure_ascii=False, separators=(",", ":"))
        f.write(";\n")
    print(f"dados.js: {len(saida)} pinos ({len(dados['encontrados'])} encontrados), "
          f"{len(categorias)} categorias, {len(icones)} ícones")


if __name__ == "__main__":
    gerar_dados()
