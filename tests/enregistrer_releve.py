"""Regenere `tests/reponses_moteur.json` depuis un moteur qui tourne.

Deux sources, et la troisieme colonne du releve depend des deux :

  1. un moteur LOCAL (heurix-engine) portant deux catalogues construits avec
     les memes articles et deux packs differents :
       deploy/generer_catalogue.py --nombre 800 --graine 42 --sortie c.json
       POST /v1/index/public-demo/items     {"rulepack": "outillage", "items": ...}
       POST /v1/index/demo-attributs/items  {"rulepack": "mode", "items": ...}
     la cle doit avoir un plan Browse (PUT /v1/admin/keys/{cle}/browse-plan) ;
  2. le catalogue de demonstration de PRODUCTION, par sa route publique sans
     cle -- lecture seule, plafonnee a 20 resultats.

Usage :
  KEY=hx_... HEURIX_LOCAL=http://127.0.0.1:8731 python3 tests/enregistrer_releve.py tests/reponses_moteur.json

Pensez a mettre a jour les dates d'`origine` ci-dessous : elles datent le releve.
"""
import json, os, sys, urllib.request

LOCAL = os.environ.get("HEURIX_LOCAL", "http://127.0.0.1:8731")
KEY = os.environ["KEY"]
FILTRES = [[], ["DIAM_M8"], ["M8"], ["inox"], ["diametre:M8"], ["matiere:inox"], ["matiere:inox A2"]]

def poster(url, corps, entetes):
    req = urllib.request.Request(url, data=json.dumps(corps).encode(), method="POST",
                                 headers={"Content-Type": "application/json", **entetes})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)

def obtenir(url, entetes):
    req = urllib.request.Request(url, headers=entetes)
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)

REQUETES = ["M8", r"\bM8\b", "^VIS-8", "vis inox", "vsi inox", "9782070368228"]


def requetes_libres(faire):
    """Meme moteur, memes articles : seule la forme de la requete change."""
    return {q: faire([], q)["total"] for q in REQUETES}


def recherches(faire):
    out = {}
    for f in FILTRES:
        d = faire(f, "vis")
        premier = (d.get("hits") or [{}])[0]
        out[json.dumps(f)] = {
            "total": d["total"],
            "filters_unknown": d.get("filters_unknown"),
            "champs_du_premier_produit": sorted((premier.get("product") or {}).keys()),
            "matched_du_premier": premier.get("matched", []),
        }
    return out

def _local(nom, ent):
    return lambda f, q: poster(f"{LOCAL}/v1/index/{nom}/search", {"q": q, "limit": 1, "filters": f}, ent)


def _prod(f, q):
    return poster("https://api.heurix.fr/v1/public-demo/search?vertical=outillage",
                  {"q": q, "limit": 1, "filters": f}, {})


catalogues = {}
for nom in ("public-demo", "demo-attributs"):
    ent = {"Authorization": f"Bearer {KEY}"}
    catalogues[nom] = {
        "origine": "moteur local, arbre cbfc93d, 16 septembre 2026",
        "stats": obtenir(f"{LOCAL}/v1/index/{nom}/stats", ent),
        "browse_categories": obtenir(f"{LOCAL}/v1/index/{nom}/browse-categories", ent),
        "recherches": recherches(_local(nom, ent)),
        "requetes_libres": requetes_libres(_local(nom, ent)),
    }

catalogues["public-demo (api.heurix.fr)"] = {
    "origine": "api.heurix.fr, /v1/public-demo/search?vertical=outillage, git_sha cbfc93d, 16 septembre 2026",
    "recherches": recherches(_prod),
    "requetes_libres": requetes_libres(_prod),
}

sortie = {
    "provenance": (
        "Reponses reellement rendues par le moteur Heurix, relevees le 16 septembre 2026. "
        "Les deux premiers catalogues portent les MEMES 800 articles (deploy/generer_catalogue.py, "
        "graine 42) indexes avec deux packs de regles differents ; le troisieme est le catalogue "
        "de demonstration de production, joint sans cle par sa route publique. "
        "Rien n'est invente : ce fichier est un releve, pas un jeu d'essai ecrit a la main."
    ),
    "catalogs_endpoint": obtenir(f"{LOCAL}/v1/index/catalogs", {"Authorization": f"Bearer {KEY}"}),
    "catalogues": catalogues,
}
json.dump(sortie, open(sys.argv[1], "w"), ensure_ascii=False, indent=2)
print("ecrit:", sys.argv[1])
