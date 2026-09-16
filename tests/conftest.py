"""Fixtures de la suite du serveur MCP Heurix.

CE QUE CETTE SUITE GARDE. Les instructions et les docstrings de ce fichier
ne sont pas de la documentation : ce sont les SEULES phrases qu'un modele
lit avant de choisir un outil et d'en composer les arguments. Une phrase
qui annonce ce que le serveur ne rend pas n'est pas une imprecision de
prose, c'est une entree fausse donnee a un agent -- qui cherchera, ne
trouvera pas, et devinera.

D'OU VIENT `reponses_moteur.json`. D'un releve, jamais d'une main. Il est
regenere par `tests/enregistrer_releve.py` contre un moteur qui tourne, et
sa cle `provenance` dit quel arbre, quel jour, quels catalogues. Un jeu
d'essai ecrit ici aurait repondu ce que la suite voulait entendre : c'est
exactement le piege que ce lot corrige ailleurs.

CE QU'ELLE NE GARDE PAS, et il faut le dire. Deux des quatre tests portent
sur la PROSE (« ce mot figure-t-il », « cet exemple figure-t-il »), pas sur
un comportement. Ils verrouillent une DECISION -- celle de ne plus ecrire
de valeur de filtre en dur -- et la mesure qui la justifie est portee par
le test voisin, `test_aucune_valeur_de_filtre_ne_marche_partout`. Un
lecteur qui ne verrait que le garde de prose le prendrait pour un caprice
de style ; il ne l'est pas, et c'est le releve qui le dit.
"""
import json
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)

# AVANT L'IMPORT DE `server`, et pas dans une fixture : le module sort en
# `sys.exit(1)` quand HEURIX_API_KEY manque, donc l'import lui-meme echoue.
# La valeur n'est jamais envoyee nulle part -- le moteur est simule.
os.environ.setdefault("HEURIX_API_KEY", "hx_suite_de_tests")

import server  # noqa: E402 — voir la ligne au-dessus

with open(os.path.join(RACINE, "tests", "reponses_moteur.json"), encoding="utf-8") as f:
    RELEVE = json.load(f)


@pytest.fixture(scope="session")
def releve() -> dict:
    return RELEVE


class _Rejoueur(BaseHTTPRequestHandler):
    """Rejoue le releve, et REFUSE ce qu'il ne connait pas.

    Un 404 sur une route non relevee vaut mieux qu'une reponse plausible
    inventee : si un outil se met a appeler autre chose, la suite doit le
    voir, pas le couvrir.
    """

    def do_GET(self) -> None:  # noqa: N802 — nom impose par BaseHTTPRequestHandler
        corps = self._corps()
        self.send_response(200 if corps is not None else 404)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(corps if corps is not None else {"detail": self.path}).encode())

    def _corps(self):
        chemin = self.path.split("?")[0]
        if chemin == "/v1/index/catalogs":
            return RELEVE["catalogs_endpoint"]
        morceaux = chemin.strip("/").split("/")
        if len(morceaux) == 4 and morceaux[:2] == ["v1", "index"]:
            catalogue = RELEVE["catalogues"].get(morceaux[2], {})
            if morceaux[3] == "stats":
                return catalogue.get("stats")
            if morceaux[3] == "browse-categories":
                return catalogue.get("browse_categories")
        return None

    def log_message(self, *args) -> None:
        pass


@pytest.fixture()
def moteur_simule(monkeypatch):
    """Sert le releve en HTTP et branche `server` dessus, le temps du test."""
    httpd = HTTPServer(("127.0.0.1", 0), _Rejoueur)
    fil = threading.Thread(target=httpd.serve_forever, daemon=True)
    fil.start()
    monkeypatch.setattr(server, "HEURIX_API_BASE", f"http://127.0.0.1:{httpd.server_port}")
    try:
        yield
    finally:
        httpd.shutdown()
        httpd.server_close()
