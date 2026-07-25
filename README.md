# Serveur MCP Heurix

Permet à un agent IA (Claude Desktop, Cursor, ou tout autre client MCP)
d'interroger directement un catalogue Heurix — recherche, parcours par
catégorie, statistiques — sans que l'agent ait à connaître l'API REST.
Chantier 6.1 de la roadmap, 24 juillet 2026.

Trois tools exposés :
- **`heurix_search`** — recherche par mot-clé, tolérante aux fautes de frappe
- **`heurix_browse`** — liste les produits d'une catégorie, avec tri (stock, prix, popularité...)
- **`heurix_catalog_stats`** — liste les catalogues et leurs catégories disponibles

Une fine couche au-dessus de l'API REST Heurix existante — aucune nouvelle
logique métier, juste une nouvelle façade que les agents IA savent parler
nativement.

## Installation

```bash
pip install -r requirements.txt
```

Testable en local avant de le brancher à un client :
```bash
HEURIX_API_KEY=hx_votre_cle python3 server.py
```
(Le serveur attend alors une connexion MCP sur stdin/stdout — `Ctrl+C` pour arrêter. C'est normal qu'il ne "fasse rien" visuellement : un client MCP doit s'y connecter pour que quoi que ce soit se passe.)

## Configuration dans Claude Desktop

1. Ouvrez Claude Desktop → **Réglages → Développeur → Modifier la configuration** (ça crée le fichier s'il n'existe pas encore)
2. Le fichier se trouve à :
   - macOS : `~/Library/Application Support/Claude/claude_desktop_config.json`
   - Windows : `%APPDATA%\Claude\claude_desktop_config.json`
3. Ajoutez (ou complétez s'il existe déjà d'autres serveurs) :

```json
{
  "mcpServers": {
    "heurix": {
      "command": "/usr/bin/python3",
      "args": ["/chemin/complet/vers/heurix-mcp-server/server.py"],
      "env": {
        "HEURIX_API_KEY": "hx_votre_cle_api",
        "HEURIX_API_BASE": "https://api.heurix.fr"
      }
    }
  }
}
```

**Important** : utilisez le **chemin complet** vers `python3` (`which python3` dans un terminal pour le trouver), pas juste `python3` — Claude Desktop lance la configuration avec un PATH minimal, une commande courte qui fonctionne dans votre terminal peut échouer silencieusement ici. Même chose pour le chemin vers `server.py` : complet, pas relatif.

4. Redémarrez Claude Desktop entièrement (pas juste fermer la fenêtre)
5. Un nouvel outil (icône 🔌 ou menu MCP selon la version) doit lister `heurix_search`, `heurix_browse`, `heurix_catalog_stats`

## Configuration dans Cursor

Même structure de fichier, deux emplacements possibles :
- `.cursor/mcp.json` à la racine d'un projet (pour un serveur propre à ce projet)
- `~/.cursor/mcp.json` (global, disponible dans tous les projets)

```json
{
  "mcpServers": {
    "heurix": {
      "command": "/usr/bin/python3",
      "args": ["/chemin/complet/vers/heurix-mcp-server/server.py"],
      "env": {
        "HEURIX_API_KEY": "hx_votre_cle_api",
        "HEURIX_API_BASE": "https://api.heurix.fr"
      }
    }
  }
}
```

Ensuite : **Réglages Cursor → Tools & MCP**, vérifiez que "Enable MCP Servers" est coché, et que `heurix` apparaît avec un point vert (connecté). Si rien n'apparaît après un redémarrage, le panneau **Output → MCP** affiche les logs bruts du serveur — souvent plus parlant que l'interface elle-même pour diagnostiquer.

## Exemple concret

**Ce qu'un utilisateur tape dans Claude Desktop**, sans rien connaître de l'API Heurix :

> J'ai un catalogue Heurix qui s'appelle quincaillerie-demo. Est-ce que j'ai des vis M8 en stock, et à quel prix ?

**Ce qui se passe côté agent** (invisible pour l'utilisateur, montré ici pour comprendre) :
1. Claude appelle `heurix_search(catalog="quincaillerie-demo", query="vis M8")`
2. Le serveur MCP relaie vers `POST https://api.heurix.fr/v1/index/quincaillerie-demo/search`
3. La réponse JSON (hits, scores, stock, prix) revient à Claude

**Réponse type de Claude Desktop à l'utilisateur** :

> Oui, vous avez deux références de vis M8 en stock dans quincaillerie-demo :
>
> - **Vis M8 x 20 - Inox A2** — 120 en stock, 5,90 €
> - **Vis M8 x 30 - Inox A2** — 45 en stock, 7,90 €
>
> Voulez-vous que je regarde aussi si l'une d'elles a un stock faible, ou que je compare avec une autre référence ?

Aucune ligne de code, aucun appel curl — l'utilisateur pose une question en
langage naturel, l'agent fait le pont vers l'API.

## Sécurité

`HEURIX_API_KEY` vit uniquement dans la configuration du client MCP (fichier
local sur la machine de l'utilisateur), jamais en argument de ligne de
commande, jamais transmise en clair dans un appel de tool — le serveur la
lit une fois au démarrage depuis l'environnement et l'utilise pour chaque
appel à l'API Heurix.
