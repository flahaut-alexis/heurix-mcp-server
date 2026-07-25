"""
Serveur MCP pour Heurix — chantier 6.1 de la roadmap (24 juillet 2026).

Enveloppe l'API REST Heurix existante en "tools" qu'un agent IA (Claude
Desktop, Cursor, un agent interne via le SDK MCP) peut découvrir et
appeler directement. Pas de nouvelle logique métier ici : une nouvelle
façade sur ce qui existe déjà (recherche, browse, stats catalogue).

Configuration — deux variables d'environnement, jamais codées en dur ni
passées en clair dans un appel de tool :
  HEURIX_API_KEY   votre clé API Heurix (hx_...)
  HEURIX_API_BASE  URL de base de l'API (défaut : https://api.heurix.fr)

Lancement local (test manuel) :
  HEURIX_API_KEY=hx_... python3 server.py

Voir README.md pour la configuration dans Claude Desktop et Cursor.
"""
from __future__ import annotations

import os
import sys

import httpx
from mcp.server.fastmcp import FastMCP

HEURIX_API_KEY = os.environ.get("HEURIX_API_KEY", "").strip()
HEURIX_API_BASE = os.environ.get("HEURIX_API_BASE", "https://api.heurix.fr").rstrip("/")

if not HEURIX_API_KEY:
    print(
        "HEURIX_API_KEY manquante — définissez-la dans la configuration MCP de "
        "votre client (Claude Desktop, Cursor...), jamais en argument de ligne "
        "de commande ni codée en dur dans ce fichier.",
        file=sys.stderr,
    )
    sys.exit(1)

mcp = FastMCP(
    "heurix",
    instructions=(
        "Outils pour interroger un catalogue produit indexé sur Heurix — un "
        "moteur de recherche et de classement pour catalogues techniques "
        "(regex sur références produit, facettes, tri par catégorie). "
        "Commencez par heurix_catalog_stats si vous ne connaissez pas encore "
        "les catalogues, catégories ou attributs disponibles sur ce compte : "
        "les noms de catalogue et de catégorie sont sensibles à la casse et "
        "doivent être exacts, pas devinés."
    ),
)


def _auth_headers() -> dict:
    return {"Authorization": f"Bearer {HEURIX_API_KEY}"}


def _handle_response(r: httpx.Response) -> dict:
    """Ne masque jamais une erreur API derrière un plantage générique — un
    agent doit pouvoir comprendre, et au besoin expliquer à l'utilisateur,
    ce qui s'est mal passé (catalogue introuvable, quota dépassé, accès
    Browse non inclus dans le plan...) plutôt que recevoir une exception
    opaque."""
    if r.status_code >= 400:
        try:
            detail = r.json().get("detail", r.text)
        except Exception:  # noqa: BLE001 — reponse non-JSON, on renvoie le texte brut
            detail = r.text
        return {"error": True, "status_code": r.status_code, "detail": detail}
    return r.json()


async def _get(path: str, params: dict | None = None) -> dict:
    async with httpx.AsyncClient(timeout=15.0) as client:
        r = await client.get(f"{HEURIX_API_BASE}{path}", headers=_auth_headers(), params=params or {})
    return _handle_response(r)


async def _post(path: str, json_body: dict) -> dict:
    async with httpx.AsyncClient(timeout=15.0) as client:
        r = await client.post(f"{HEURIX_API_BASE}{path}", headers=_auth_headers(), json=json_body)
    return _handle_response(r)


@mcp.tool()
async def heurix_search(catalog: str, query: str, filters: list[str] | None = None, limit: int = 10) -> dict:
    """Recherche des produits dans un catalogue Heurix par mot-clé, avec
    tolérance aux fautes de frappe et reconnaissance des références
    techniques (diamètres, longueurs, matières, ISBN...). Utilisez
    heurix_catalog_stats d'abord si le nom exact du catalogue n'est pas
    déjà connu.

    La réponse peut inclure `suggested_category` si un mot de la requête
    recoupe une catégorie Browse connue — utile pour proposer "cherchiez-
    vous plutôt dans telle catégorie ?", ne change jamais les résultats
    eux-mêmes.

    Args:
        catalog: Nom exact du catalogue à interroger.
        query: Texte de recherche, tel qu'un utilisateur le taperait —
            les fautes de frappe et formats différents sont tolérés par
            le moteur, pas la peine de les corriger avant d'appeler.
        filters: Liste optionnelle de filtres exacts sur des annotations
            connues (ex. ["DIAM_M8"]). Laisser vide si incertain plutôt
            que de deviner une valeur.
        limit: Nombre maximal de résultats, entre 1 et 100 (défaut 10).
    """
    return await _post(
        f"/v1/index/{catalog}/search",
        {"q": query, "filters": filters or [], "limit": max(1, min(limit, 100))},
    )


@mcp.tool()
async def heurix_browse(catalog: str, category: str, sort: str = "stock", limit: int = 20) -> dict:
    """Liste les produits d'une catégorie sans recherche textuelle — pour
    une demande du type "montre-moi tous les produits de telle
    catégorie", pas une recherche par mot-clé (utilisez heurix_search
    pour ça). Utilisez heurix_catalog_stats pour découvrir les
    catégories réellement disponibles si elles ne sont pas déjà connues
    — inventer un nom de catégorie renverra une liste vide, pas une erreur.

    Args:
        catalog: Nom exact du catalogue.
        category: Valeur de catégorie exacte, sensible à la casse.
        sort: Stratégie de tri — "stock" (défaut, en stock d'abord),
            "recent", "alphabetical", "price_asc", "price_desc",
            "margin", ou "popular" (popularité réelle, clics et achats).
        limit: Nombre maximal de résultats, entre 1 et 100 (défaut 20).
    """
    return await _get(
        f"/v1/browse/{catalog}/{category}",
        {"sort": sort, "limit": max(1, min(limit, 100))},
    )


@mcp.tool()
async def heurix_catalog_stats(catalog: str | None = None) -> dict:
    """Liste tous les catalogues accessibles avec cette clé API et leurs
    statistiques de base (nombre de produits, pack de règles actif). Si
    `catalog` est précisé, renvoie en plus les catégories Browse
    disponibles pour ce catalogue. À appeler en premier pour découvrir
    ce qui existe, avant une recherche ou un parcours par catégorie.

    Args:
        catalog: Nom d'un catalogue précis (optionnel). Sans ce
            paramètre, liste tous les catalogues du compte.
    """
    if catalog:
        stats = await _get(f"/v1/index/{catalog}/stats")
        if stats.get("error"):
            return stats
        categories = await _get(f"/v1/index/{catalog}/browse-categories")
        # Browse peut ne pas être inclus dans le plan de cette clé — pas une
        # raison de faire échouer tout l'appel, juste une liste vide.
        stats["browse_categories"] = categories.get("categories", []) if not categories.get("error") else []
        return stats
    return await _get("/v1/index/catalogs")


def main() -> None:
    """Point d'entree de la commande `heurix-mcp-server`.

    Declaree dans pyproject.toml sous [project.scripts] : sans cette
    fonction, la commande installee depuis PyPI echouerait a l'import.
    C'est aussi elle que les annuaires MCP lancent pour introspecter le
    serveur et verifier les outils qu'il expose.
    """
    mcp.run(transport="stdio")


if __name__ == "__main__":
    mcp.run(transport="stdio")
