# Référencement du serveur MCP Heurix dans les annuaires

*Préparé le 25 juillet 2026, après vérification des conditions réelles de
chaque annuaire par recherche web — elles évoluent vite, revérifiez si
plusieurs semaines se sont écoulées.*

---

## Correction d'estimation

J'avais annoncé ce chantier comme « effort quasi nul ». **C'était inexact**,
pour deux raisons que la recherche a révélées :

**1. Les annuaires vérifient en lançant le serveur.** mcp.so, Smithery et
Glama n'indexent pas une description : ils exécutent une commande et
introspectent le processus pour lister les outils exposés. Un zip
téléchargeable depuis heurix.fr ne leur suffit pas — il faut une commande
installable.

→ **Traité** : `pyproject.toml` ajouté, plus la fonction `main()` qui
manquait au point d'entrée. Une fois publié sur PyPI, le serveur se lance
par `uvx heurix-mcp-server`, ce que tout crawler sait faire.

**2. L'annuaire de connecteurs d'Anthropic est hors de portée en l'état.**
C'est la placement à plus fort trafic, mais il exige un transport
**Streamable HTTP** et **OAuth 2.1 avec PKCE**. Le serveur Heurix est en
**stdio** : il ne qualifie pas.

→ **Non traité, et ce n'est pas un oubli.** C'est exactement le chantier
7.4 (transport HTTP) qui a été écarté. Si l'annuaire Anthropic devient un
objectif, il faut le reprendre d'abord.

---

## Ce qui est faisable aujourd'hui

| Annuaire | Transport stdio accepté | Mécanisme |
|---|---|---|
| Registre officiel MCP | Oui | PR sur `github.com/modelcontextprotocol/servers` |
| mcp.so | Oui | Formulaire web |
| Smithery | Oui | CLI `smithery mcp publish` ou tableau de bord |
| Glama | Oui | Indexation automatique depuis GitHub |
| awesome-mcp-servers | Oui | PR sur `github.com/punkpeye/awesome-mcp-servers` |
| **Annuaire Anthropic** | **Non** | Exige Streamable HTTP + OAuth 2.1 |

---

## Étape 0 — Prérequis, dans cet ordre

**a) Créer le dépôt GitHub public** `flahaut-alexis/heurix-mcp-server`.
Les annuaires y cherchent le code source, la licence et le README. Un
serveur sans dépôt public passe difficilement la revue du registre
officiel, qui exige un serveur « réel, fonctionnel et documenté ».

**b) Publier sur PyPI** :
```bash
cd heurix-mcp-server
pip install build twine
python -m build
twine upload dist/*
```

**c) Vérifier que la commande fonctionne** depuis une installation propre :
```bash
uvx heurix-mcp-server
```
Le serveur doit démarrer et attendre sur son entrée standard. C'est
exactement ce que fera le crawler.

---

## Métadonnées à réutiliser partout

Préparez-les une fois, collez-les dans chaque formulaire.

**Nom** : `heurix-mcp-server`

**Une phrase** :
> Recherche et classement de catalogues produits techniques en langage
> naturel — références, dimensions, normes et identifiants reconnus par
> cascade de règles.

**Description longue** :
> Heurix est un moteur de recherche pour catalogues techniques : il
> reconnaît la structure d'une référence produit (diamètre, longueur,
> matière, norme, ISBN, millésime) au lieu de comparer du texte. Ce
> serveur MCP expose trois outils permettant à un agent d'interroger un
> catalogue Heurix en langage naturel : recherche tolérante aux fautes de
> frappe, parcours de catégorie avec classement configurable, et
> statistiques de catalogue. Authentification par clé API, fournie en
> configuration du serveur et jamais transmise en clair dans un appel
> d'outil.

**Outils exposés** : `heurix_search`, `heurix_browse`,
`heurix_catalog_stats`

**Transport** : stdio

**Catégories** : search, e-commerce, data, productivity

**Dépôt** : `https://github.com/flahaut-alexis/heurix-mcp-server`
**Site** : `https://heurix.fr`
**Documentation** : `https://heurix.fr/docs.html#ep-mcp`

**Commande d'installation** : `uvx heurix-mcp-server`

**Variables d'environnement** :
- `HEURIX_API_KEY` — clé API Heurix (obligatoire)
- `HEURIX_API_BASE` — défaut `https://api.heurix.fr`

---

## Soumissions, par ordre de priorité

### 1. Registre officiel MCP — le plus important
C'est la source de confiance : les clients IA y vérifient la légitimité
d'un serveur. Fork de `github.com/modelcontextprotocol/servers`, ajout de
l'entrée dans le README **par ordre alphabétique**, puis PR.

Attendez-vous à une revue exigeante — c'est une barre de qualité, pas un
dépôt ouvert. Le dépôt GitHub et la publication PyPI doivent être en place
avant de soumettre.

### 2. Smithery
```bash
npm install -g @smithery/cli
smithery mcp publish "https://github.com/flahaut-alexis/heurix-mcp-server" -n heurix/heurix-mcp-server
```
Ou par le tableau de bord sur `smithery.ai`.

### 3. mcp.so
Formulaire web sur le site. Collez les métadonnées ci-dessus.

### 4. awesome-mcp-servers
PR sur `github.com/punkpeye/awesome-mcp-servers`, dans la catégorie
recherche ou e-commerce. Lisez leurs règles de contribution avant — les
listes *awesome* refusent souvent les entrées mal formatées.

### 5. Glama
Indexation automatique depuis GitHub, généralement sans démarche. À
vérifier quelques jours après la création du dépôt.

---

## Un point de prudence sur la clé API

Plusieurs annuaires proposent un « essai » de votre serveur depuis leur
interface. **Ne fournissez jamais votre clé de production** dans un
formulaire d'annuaire. Si un annuaire demande des identifiants de test,
créez une clé dédiée sur un catalogue de démonstration, et prévoyez de
pouvoir la révoquer.

Le registre officiel demande d'ailleurs, pour les connecteurs, un compte
de test **prérempli avec des données réalistes** — un compte vide fait
échouer la revue. Le catalogue `quincaillerie-demo` avec ses 66 produits
convient exactement à cet usage.
