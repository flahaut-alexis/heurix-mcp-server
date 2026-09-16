"""Ce que les instructions et les docstrings annoncent, contre ce que le
serveur rend reellement.

Releve du 15 septembre 2026 (session de l'article sur les agents) : les
instructions disaient de commencer par heurix_catalog_stats pour connaitre
les « catalogues, catégories ou attributs ». La reponse ne porte aucun
attribut -- un nombre d'annotations, pas une liste, et aucun nom de champ.
Et l'exemple de filtre de la docstring, ["DIAM_M8"], rendait 0.
"""
import asyncio
import json
import re

import pytest

import server


def _executer(coroutine):
    return asyncio.run(coroutine)


# ---------------------------------------------------------------------------
# 1. CE QUE heurix_catalog_stats EST DIT RENDRE
# ---------------------------------------------------------------------------
# Chaque mot que les instructions associent a heurix_catalog_stats doit
# designer quelque chose que SA reponse contient. Un mot sans resolveur est
# une promesse sans objet : le test echoue et dit lequel.
#
# « attributs » N'A PAS DE RESOLVEUR, et c'est le point. `stats` rend
# `annotations: 260` -- un COMPTE -- et aucun nom de champ ni d'annotation.
# Le jour ou un outil en rendra, ce sera un lot a part, et il ajoutera son
# resolveur ici en meme temps que le mot.
RESOLVEURS_STATS = {
    "catalogues": lambda r: [c["catalog"] for c in r["sans_argument"]["catalogs"]],
    "catégories": lambda r: [c["category"] for c in r["avec_catalogue"]["browse_categories"]],
}
MOTS_DE_DECOUVERTE = ("catalogues", "catégories", "attributs", "annotations", "champs")


@pytest.fixture()
def reponses_stats(moteur_simule):
    return {
        "sans_argument": _executer(server.heurix_catalog_stats()),
        "avec_catalogue": _executer(server.heurix_catalog_stats("public-demo")),
    }


def test_les_reponses_de_stats_ne_portent_aucun_nom_d_attribut(reponses_stats, releve):
    """La mesure qui fonde le lot, rejouee sur ce que l'outil rend.

    Temoin de population : le releve prouve que ces noms EXISTENT dans le
    catalogue (ils sont dans les produits rendus par la recherche). Sans ce
    temoin, « absent de stats » serait vrai d'un catalogue qui n'en a pas.
    """
    champs = releve["catalogues"]["public-demo"]["recherches"]["[]"]["champs_du_premier_produit"]
    assert {"diametre", "matiere"} <= set(champs)

    texte = json.dumps(reponses_stats, ensure_ascii=False)
    assert "diametre" not in texte and "matiere" not in texte
    assert isinstance(reponses_stats["avec_catalogue"]["annotations"], int)


@pytest.mark.parametrize("mot", MOTS_DE_DECOUVERTE)
def test_ce_que_les_instructions_disent_de_stats_est_dans_sa_reponse(mot, reponses_stats):
    if mot not in server.mcp.instructions:
        pytest.skip(f"les instructions ne mentionnent pas « {mot} »")
    assert mot in RESOLVEURS_STATS, (
        f"les instructions annoncent des « {mot} » ; heurix_catalog_stats n'en rend aucun. "
        "Retirez le mot, ou ajoutez l'outil ET son resolveur ici."
    )
    assert RESOLVEURS_STATS[mot](reponses_stats), f"« {mot} » : la reponse n'en porte aucun"


# ---------------------------------------------------------------------------
# 2. LES CAPACITES QUE LA PREMIERE PHRASE PRETE AUX OUTILS
# ---------------------------------------------------------------------------
def _parametres_des_outils() -> set[str]:
    outils = _executer(server.mcp.list_tools())
    return {p for t in outils for p in t.inputSchema.get("properties", {})}


def _regex_acceptee(releve) -> bool:
    """Une requete en regex rend-elle ce que rend le motif en clair ?

    Releve : « M8 » rend 66, 61, 141 sur les trois catalogues ; « \\bM8\\b »
    rend 0 partout -- la requete est tokenisee, les metacaracteres deviennent
    des lettres (`tokens: ["bm8", "b"]`). Un agent qui ecrit une regex
    conclut que le catalogue n'a pas de M8.
    """
    return all(c["requetes_libres"]["\\bM8\\b"] > 0 for c in releve["catalogues"].values())


CAPACITES = {
    "regex": lambda releve: _regex_acceptee(releve),
    # L'API connait `facets` ; aucun outil ne le transmet, aucune reponse
    # d'outil n'en porte.
    "facettes": lambda releve: "facets" in _parametres_des_outils(),
    "tri": lambda releve: "sort" in _parametres_des_outils(),
}


@pytest.mark.parametrize("mot", sorted(CAPACITES))
def test_une_capacite_annoncee_est_joignable_par_un_outil(mot, releve):
    if mot not in server.mcp.instructions:
        pytest.skip(f"les instructions ne mentionnent pas « {mot} »")
    assert CAPACITES[mot](releve), (
        f"les instructions pretent aux outils la capacite « {mot} » ; "
        "aucun parametre ne la porte et le releve montre qu'elle ne s'exerce pas."
    )


# ---------------------------------------------------------------------------
# 3. LES FILTRES
# ---------------------------------------------------------------------------
def test_aucune_valeur_de_filtre_ne_marche_partout(releve):
    """La mesure qui interdit un exemple de valeur en dur.

    Memes 800 articles, trois indexations -- et chaque valeur concrete rend
    zero sur au moins une :

                          outillage+champs   mode+champs   demo production
        ["DIAM_M8"]             28              0              56
        ["diametre:M8"]         28             13               0

    L'exemple de la docstring n'etait donc pas « faux » : il etait vrai d'UN
    catalogue, et lu comme vrai de tous.
    """
    catalogues = releve["catalogues"]
    assert len(catalogues) >= 3
    valeurs = [f for f in next(iter(catalogues.values()))["recherches"] if f != "[]"]
    assert valeurs, "releve vide : le test n'aurait rien a mesurer"
    for filtre in valeurs:
        totaux = [c["recherches"][filtre]["total"] for c in catalogues.values()]
        assert min(totaux) == 0, f"{filtre} rend des resultats partout ({totaux}) : il pourrait servir d'exemple"


def test_une_valeur_inconnue_d_un_champ_connu_rend_zero_sans_signal(releve):
    """Le piege que la docstring doit nommer : `filters_unknown` ne signale
    que les CHAMPS et les ANNOTATIONS inconnus, jamais une VALEUR."""
    for nom in ("public-demo", "demo-attributs"):
        r = releve["catalogues"][nom]["recherches"]
        assert r['["matiere:inox"]'] == {**r['["matiere:inox"]'], "total": 0, "filters_unknown": None}
        assert r['["matiere:inox A2"]']["total"] > 0
        assert r['["M8"]']["filters_unknown"] == ["M8"]


def _paragraphe_filters() -> str:
    doc = server.heurix_search.__doc__
    debut = doc.index("filters:")
    return doc[debut:doc.index("limit:", debut)]


def test_la_docstring_ne_montre_aucune_valeur_de_filtre_en_dur():
    """Garde de PROSE : il verrouille la decision que le test du releve fonde.

    Une valeur entre crochets (`["DIAM_M8"]`, `["diametre:M8"]`) se lit comme
    une valeur a recopier. Les formes s'ecrivent avec des noms generiques
    (`champ`, `valeur`, `ANNOTATION`) et disent ou lire les vraies.
    """
    exemples = re.findall(r'\[\s*"([^"]+)"', _paragraphe_filters())
    assert exemples == [], f"valeurs de filtre en dur dans la docstring : {exemples}"


def test_la_docstring_nomme_les_deux_formes_et_ou_les_lire():
    """Garde de PROSE, lui aussi. Les deux formes que le moteur accepte
    (search.py, `_preparer_filtres`) doivent etre nommees, avec l'endroit de
    la reponse ou leurs noms se lisent -- sinon l'agent les devine."""
    p = _paragraphe_filters()
    assert "champ:valeur" in p
    assert "product" in p and "matched" in p
    assert "filters_unknown" in p
