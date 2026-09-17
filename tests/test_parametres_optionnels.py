"""Un parametre optionnel doit pouvoir etre omis, quel que soit le client.

Releve du 17 septembre 2026, Claude.app 2.110.1 (onglet Code). L'app
reexpose nos outils a la session par un serveur MCP interne, et reconstruit
un schema Zod depuis notre JSON Schema (.vite/build/index.chunk-BehGPm8o.js
dans app.asar) : tout `default` present, meme `null`, devient
`.prefault(default)`. Ce champ est construit par le Zod 4.5.4 de l'app,
puis valide par le Zod 4.4.3 embarque dans le SDK TypeScript, qui ne
connait pas l'`optin: "defaulted"` de 4.5.4 et exige la cle. Resultat,
mesure dans la session et reproduit hors session avec ces deux versions :

    heurix_catalog_stats {}                       refuse (expected nonoptional)
    heurix_catalog_stats {"catalog": ""}          accepte
    heurix_search sans filters ni limit           refuse sur les deux
    heurix_browse sans sort ni limit              refuse sur les deux
    meme parametre, SANS cle `default`            accepte

Le type ne compte pas : `sort: str = "stock"` garde `type: string` et il est
refuse. Le contournement envisage, `catalog: str = ""`, l'etait donc aussi.

Ce que ces tests gardent : aucun parametre non requis ne publie `default`,
et les valeurs par defaut restent appliquees cote serveur -- le SDK Python
officiel (1.30.0 et 2.2.0) et le SDK TypeScript (1.30.0) acceptent `{}`
avec ou sans la cle, mesure le meme jour.
"""
import asyncio
import json

import pytest

import server


def _executer(coroutine):
    return asyncio.run(coroutine)


def _appeler(outil, arguments):
    return json.loads(_executer(server.mcp.call_tool(outil, arguments))[0].text)


def _outils():
    return _executer(server.mcp.list_tools())


@pytest.mark.parametrize("outil", [t.name for t in _outils()])
def test_aucun_parametre_optionnel_ne_publie_de_default(outil):
    schema = next(t for t in _outils() if t.name == outil).inputSchema
    requis = set(schema.get("required", []))
    fautifs = sorted(p for p, s in schema["properties"].items() if p not in requis and "default" in s)
    assert fautifs == [], (
        f"{outil} publie `default` sur {fautifs} : Claude.app 2.110.1 refuse alors l'appel qui les omet. "
        "Retirez la cle du schema avec `SANS_DEFAUT` (server.py), la valeur Python reste appliquee."
    )


def test_stats_sans_argument_liste_les_catalogues(moteur_simule, releve):
    assert _appeler("heurix_catalog_stats", {}) == releve["catalogs_endpoint"]


@pytest.mark.parametrize("argument", [None, ""])
def test_stats_lit_null_et_vide_comme_une_absence(argument, moteur_simule, releve):
    """`null` est ce qu'envoie un client en mode strict (OpenAI Agents rend
    `catalog` requis et garde `null` dans le type). `""` est ce qu'envoie un
    agent qui a appris le contournement : le moteur n'a aucune route pour un
    nom vide, ce n'est jamais un catalogue."""
    assert _appeler("heurix_catalog_stats", {"catalog": argument}) == releve["catalogs_endpoint"]


def test_les_valeurs_par_defaut_restent_appliquees(monkeypatch):
    appels = []

    async def _capturer(path, corps=None):
        appels.append((path, corps))
        return {}

    monkeypatch.setattr(server, "_get", _capturer)
    monkeypatch.setattr(server, "_post", _capturer)
    _appeler("heurix_search", {"catalog": "c", "query": "vis"})
    _appeler("heurix_browse", {"catalog": "c", "category": "k"})
    assert appels == [
        ("/v1/index/c/search", {"q": "vis", "filters": [], "limit": 10}),
        ("/v1/browse/c/k", {"sort": "stock", "limit": 20}),
    ]
