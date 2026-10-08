"""Documentation OpenAPI et cohérence documents / code (#29).

Deux familles de tests :
- l'OpenAPI (`/openapi.json`, `/docs`) décrit toutes les routes, le cookie, les montants en chaînes
  et les erreurs réelles de l'API ;
- les documents `docs/api-design.md` et `docs/data-model.md` disent la même chose que le code.

Les tests sur les documents lisent le dossier `docs/` : dans le conteneur de test, il faut le monter
(`-v "$PWD/docs:/docs:ro"`, voir le README) ; sans lui ils sont ignorés avec un message explicite.
La CI, qui exécute les tests depuis le dépôt, les lance toujours.
"""

import importlib.util
import re
from datetime import date
from pathlib import Path

import pytest
from fastapi.routing import APIRoute

from app.core.erreurs import CODES_PAR_STATUT
from app.core.openapi import OPERATIONS
from app.core.securite import NOM_COOKIE_JWT
from app.db.base import Base
from app.main import app
from app.models import budget, categorie, depense, utilisateur  # noqa: F401  (tables dans Base.metadata)

ORIGINE = "http://localhost:5173"
ROUTES_PUBLIQUES = {
    ("GET", "/api/health"),
    ("POST", "/api/authentification/inscription"),
    ("POST", "/api/authentification/connexion"),
}
CHAMPS_MONTANT = {"montant", "montant_limite", "depense", "reste"}


def _routes_de_l_api():
    for route in app.routes:
        if isinstance(route, APIRoute) and route.path.startswith("/api"):
            for methode in sorted(route.methods - {"HEAD", "OPTIONS"}):
                yield methode, route.path


@pytest.fixture(scope="module")
def openapi() -> dict:
    return app.openapi()


def _normaliser(chemin: str) -> str:
    """`/api/depenses/{id}` et `/api/depenses/{depense_id}` désignent la même route."""
    return re.sub(r"\{[^}]+\}", "{}", chemin)


# === OpenAPI ===================================================================================


def test_openapi_et_la_page_docs_sont_servis(client):
    assert client.get("/openapi.json").status_code == 200
    assert client.get("/docs").status_code == 200


def test_la_presentation_rappelle_les_regles_essentielles(openapi):
    description = openapi["info"]["description"]
    for attendu in ("JWT", "n'est pas révoqué", "lecture seule", "chaînes décimales", "ALLOWED_ORIGINS"):
        assert attendu in description, attendu
    assert {t["name"] for t in openapi["tags"]} == {
        "systeme", "authentification", "categories", "depenses", "budgets"
    }
    assert all(t["description"] for t in openapi["tags"])


def test_chaque_route_implementee_est_decrite_et_chaque_description_a_sa_route(openapi):
    routes = set(_routes_de_l_api())
    assert routes == set(OPERATIONS), (
        f"routes sans description : {sorted(routes - set(OPERATIONS))} ; "
        f"descriptions sans route : {sorted(set(OPERATIONS) - routes)}"
    )
    for (methode, chemin), (resume, description) in OPERATIONS.items():
        operation = openapi["paths"][chemin][methode.lower()]
        assert operation["summary"] == resume
        assert operation["description"] == description
        assert resume and description


def test_le_cookie_est_declare_comme_schema_de_securite(openapi):
    schema = openapi["components"]["securitySchemes"]["cookieJwt"]
    assert schema["type"] == "apiKey"
    assert schema["in"] == "cookie"
    assert schema["name"] == NOM_COOKIE_JWT


def test_seules_les_routes_privees_declarent_la_securite(openapi):
    for methode, chemin in _routes_de_l_api():
        operation = openapi["paths"][chemin][methode.lower()]
        if (methode, chemin) in ROUTES_PUBLIQUES:
            assert "security" not in operation, (methode, chemin)
        else:
            assert operation["security"] == [{"cookieJwt": []}], (methode, chemin)


def test_les_erreurs_sont_documentees_avec_le_format_de_l_api(openapi):
    schemas = openapi["components"]["schemas"]
    assert "ReponseErreur" in schemas and "DetailErreur" in schemas
    # Le format d'erreur de FastAPI n'est pas celui que renvoient nos gestionnaires.
    assert "HTTPValidationError" not in schemas
    assert "HTTPValidationError" not in str(openapi["paths"])

    for methode, chemin in _routes_de_l_api():
        reponses = openapi["paths"][chemin][methode.lower()]["responses"]
        assert "500" in reponses
        if (methode, chemin) not in ROUTES_PUBLIQUES:
            assert "401" in reponses, (methode, chemin)
        if methode in {"POST", "PUT", "PATCH", "DELETE"}:
            assert "403" in reponses, (methode, chemin)
        for statut, reponse in reponses.items():
            if int(statut) >= 400 and (methode, chemin, statut) != ("GET", "/api/health", "503"):
                reference = reponse["content"]["application/json"]["schema"]["$ref"]
                assert reference == "#/components/schemas/ReponseErreur", (methode, chemin, statut)


@pytest.mark.parametrize(
    ("methode", "chemin", "statuts"),
    [
        ("POST", "/api/authentification/inscription", {"409", "422"}),
        ("POST", "/api/authentification/connexion", {"401", "429", "422"}),
        ("POST", "/api/depenses", {"404", "422", "400"}),
        ("GET", "/api/depenses/{depense_id}", {"404", "422"}),
        ("PATCH", "/api/depenses/{depense_id}", {"404", "422", "400"}),
        ("DELETE", "/api/depenses/{depense_id}", {"404"}),
        ("POST", "/api/budgets", {"404", "409", "422"}),
        ("GET", "/api/budgets/{budget_id}", {"404"}),
        ("PATCH", "/api/budgets/{budget_id}", {"404", "422"}),
        ("DELETE", "/api/budgets/{budget_id}", {"404"}),
    ],
)
def test_les_erreurs_metier_de_chaque_route_sont_documentees(openapi, methode, chemin, statuts):
    reponses = openapi["paths"][chemin][methode.lower()]["responses"]
    assert statuts <= set(reponses)


def test_les_statuts_documentes_sont_ceux_que_l_api_renvoie_vraiment(client, openapi):
    """On provoque quelques erreurs et on vérifie qu'elles figurent dans l'OpenAPI."""
    inconnu = "00000000-0000-4000-8000-000000000000"
    cas = [
        # (méthode, route documentée, requête réelle, statut attendu)
        ("GET", "/api/depenses", dict(url="/api/depenses"), 401),
        ("GET", "/api/budgets/{budget_id}", dict(url=f"/api/budgets/{inconnu}"), 401),
        ("POST", "/api/authentification/connexion",
         dict(url="/api/authentification/connexion", json={"email": "a@b.fr", "mot_de_passe": "x"},
              headers={"Origin": "http://autre-site.example"}), 403),
        ("POST", "/api/authentification/connexion",
         dict(url="/api/authentification/connexion", json={"email": "a@b.fr", "mot_de_passe": "x"}), 401),
        ("POST", "/api/authentification/connexion",
         dict(url="/api/authentification/connexion", content="{pas du json",
              headers={"Content-Type": "application/json"}), 400),
        ("POST", "/api/authentification/connexion",
         dict(url="/api/authentification/connexion", json={"email": "pas-un-email", "mot_de_passe": "x"}), 422),
    ]
    for methode, route, requete, attendu in cas:
        url = requete.pop("url")
        reponse = client.request(methode, url, **requete)
        assert reponse.status_code == attendu, (methode, url, reponse.text)
        assert str(attendu) in openapi["paths"][route][methode.lower()]["responses"], (methode, route, attendu)
        # Le corps renvoyé a bien la forme documentée.
        assert reponse.json()["erreur"]["code"] == CODES_PAR_STATUT[attendu]


def test_tous_les_montants_sont_des_chaines(openapi):
    trouves = 0
    for nom, schema in openapi["components"]["schemas"].items():
        for champ, definition in schema.get("properties", {}).items():
            if champ in CHAMPS_MONTANT:
                trouves += 1
                texte = str(definition)
                assert "'type': 'string'" in texte, (nom, champ)
                assert "'type': 'number'" not in texte, (nom, champ)
    assert trouves >= 8  # garde-fou : le parcours a bien trouvé les champs d'argent


def test_les_corps_de_modification_n_acceptent_ni_null_ni_champ_inconnu(openapi):
    for nom in ("DepenseModification", "BudgetModification"):
        schema = openapi["components"]["schemas"][nom]
        assert schema["additionalProperties"] is False, nom
        for champ, definition in schema["properties"].items():
            assert "anyOf" not in definition, (nom, champ)
            assert "null" not in str(definition.get("type")), (nom, champ)


def test_les_parametres_de_la_liste_des_depenses_sont_decrits(openapi):
    parametres = {p["name"]: p for p in openapi["paths"]["/api/depenses"]["get"]["parameters"]}
    assert set(parametres) == {"mois", "categorie_id", "limite", "decalage"}
    assert all(p.get("description") for p in parametres.values())
    assert parametres["limite"]["schema"]["minimum"] == 1
    assert parametres["limite"]["schema"]["maximum"] == 100
    assert parametres["limite"]["schema"]["default"] == 20
    assert parametres["decalage"]["schema"]["minimum"] == 0


# === Cohérence des documents avec le code ======================================================

DOSSIER_DOCS = Path(__file__).resolve().parents[2] / "docs"


def _lire_doc(nom: str) -> str:
    fichier = DOSSIER_DOCS / nom
    if not fichier.exists():
        pytest.skip(f"{fichier} introuvable : monter le dossier docs (-v \"$PWD/docs:/docs:ro\").")
    return fichier.read_text(encoding="utf-8")


def test_les_routes_de_api_design_sont_exactement_celles_de_l_application():
    documentees = set()
    for ligne in _lire_doc("api-design.md").splitlines():
        trouve = re.match(r"^\| (GET|POST|PUT|PATCH|DELETE) \| `(/api[^`]*)` \|", ligne)
        if trouve:
            documentees.add((trouve.group(1), _normaliser(trouve.group(2).split("?")[0])))
    reelles = {(m, _normaliser(p)) for m, p in _routes_de_l_api()}
    assert documentees == reelles, (
        f"dans le document seulement : {sorted(documentees - reelles)} ; "
        f"dans le code seulement : {sorted(reelles - documentees)}"
    )


def test_les_codes_d_erreur_de_api_design_sont_ceux_du_code():
    documentes = {
        int(m.group(1)): m.group(2)
        for ligne in _lire_doc("api-design.md").splitlines()
        if (m := re.match(r"^\| (\d{3}) \| `([a-z_]+)` \|", ligne))
    }
    assert documentes == CODES_PAR_STATUT


def test_les_erreurs_listees_par_route_dans_api_design_sont_celles_de_l_openapi(openapi):
    """La colonne « Erreurs » du contrat doit lister les mêmes statuts que l'OpenAPI, route par route.

    Les statuts généraux (400 corps illisible, 403 origine, 500) sont décrits dans les sections
    transverses du document ; seuls les statuts propres à une route figurent dans le tableau.
    """
    statuts_de_route = {401, 404, 409, 422, 429, 503}
    reelles = {
        (methode, _normaliser(chemin)): {int(s) for s in openapi["paths"][chemin][methode.lower()]["responses"]}
        for methode, chemin in _routes_de_l_api()
    }
    verifiees = 0
    for ligne in _lire_doc("api-design.md").splitlines():
        trouve = re.match(r"^\| (GET|POST|PUT|PATCH|DELETE) \| `(/api[^`]*)` \|", ligne)
        if not trouve:
            continue
        cle = (trouve.group(1), _normaliser(trouve.group(2).split("?")[0]))
        colonne_erreurs = [c.strip() for c in ligne.strip().strip("|").split("|")][-1]
        documentes = {int(code) for code in re.findall(r"\b([45]\d\d)\b", colonne_erreurs)}
        assert documentes == reelles[cle] & statuts_de_route, (
            f"{cle} : le contrat liste {sorted(documentes)}, l'OpenAPI {sorted(reelles[cle] & statuts_de_route)}"
        )
        verifiees += 1
    assert verifiees == 16


def test_les_presentations_signalent_l_exception_de_health_et_le_repli_sur_referer(openapi):
    description = openapi["info"]["description"]
    assert "GET /api/health" in description and "propre format" in description
    assert "Referer" in description
    assert "par défaut" in description  # la durée du JWT est un réglage, pas une constante


def _tables_du_diagramme(texte: str) -> dict[str, set[str]]:
    tables: dict[str, set[str]] = {}
    courante = None
    for ligne in texte.splitlines():
        debut = re.match(r"^\s{4}([A-Z_]+) \{$", ligne)
        if debut:
            courante = debut.group(1).lower()
            tables[courante] = set()
        elif courante and re.match(r"^\s{4}\}$", ligne):
            courante = None
        elif courante:
            colonne = re.match(r"^\s+\w+ (\w+)", ligne)
            if colonne:
                tables[courante].add(colonne.group(1))
    return tables


def test_le_diagramme_de_data_model_decrit_les_tables_et_colonnes_reelles():
    documentees = _tables_du_diagramme(_lire_doc("data-model.md"))
    reelles = {t.name: {c.name for c in t.columns} for t in Base.metadata.sorted_tables}
    assert documentees == reelles


def test_les_six_categories_de_data_model_sont_celles_de_la_migration():
    migration = Path(__file__).resolve().parents[1] / "migrations" / "versions" / "0001_initial_schema.py"
    spec = importlib.util.spec_from_file_location("migration_0001", migration)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    noms = {nom for _, nom in module.CATEGORIES}
    texte = _lire_doc("data-model.md")
    assert len(noms) == 6
    for nom in noms:
        assert nom in texte, nom


# === Exemples d'erreur : les messages documentés sont les messages réels =======================


def _exemple(openapi, methode, chemin, statut):
    reponse = openapi["paths"][chemin][methode.lower()]["responses"][str(statut)]
    return reponse["content"]["application/json"]["example"]["erreur"]


def test_les_descriptions_de_reponse_sont_en_francais(openapi):
    texte = str(openapi["paths"])
    for anglais in ("Successful Response", "Validation Error", "Service Unavailable"):
        assert anglais not in texte, anglais


def test_les_exemples_d_erreur_de_l_openapi_sont_les_messages_reels_de_l_api(client, openapi):
    inconnu = "00000000-0000-4000-8000-000000000000"
    inscription = "/api/authentification/inscription"
    connexion = "/api/authentification/connexion"
    identifiants = {"email": "ada@example.com", "mot_de_passe": "un-mot-de-passe-long"}
    cas = []  # (méthode, route documentée, statut attendu, réponse réelle)

    # Sans connexion
    cas.append(("GET", "/api/depenses", 401, client.get("/api/depenses")))
    cas.append(("POST", connexion, 400, client.post(
        connexion, content="{pas du json", headers={"Content-Type": "application/json"})))
    cas.append(("POST", connexion, 403, client.post(
        connexion, json=identifiants, headers={"Origin": "http://autre-site.example"})))
    cas.append(("POST", connexion, 401, client.post(connexion, json=identifiants)))
    cas.append(("POST", connexion, 422, client.post(
        connexion, json={"email": "pas-un-email", "mot_de_passe": "x"})))
    cas.append(("POST", inscription, 422, client.post(
        inscription, json={**identifiants, "email": "pas-un-email", "nom_affichage": "Ada"})))
    for _ in range(5):
        client.post(connexion, json={"email": "bloque@example.com", "mot_de_passe": "x"})
    cas.append(("POST", connexion, 429, client.post(
        connexion, json={"email": "bloque@example.com", "mot_de_passe": "x"})))

    # Inscription en double, puis connexion
    assert client.post(inscription, json={**identifiants, "nom_affichage": "Ada"}).status_code == 201
    cas.append(("POST", inscription, 409, client.post(
        inscription, json={**identifiants, "nom_affichage": "Ada"})))
    assert client.post(connexion, json=identifiants).status_code == 200
    categorie = client.get("/api/categories").json()[0]["id"]
    aujourd_hui = date.today().isoformat()
    depense = {"montant": "1.00", "libelle": "x", "date_depense": aujourd_hui, "categorie_id": inconnu}
    budget = {"categorie_id": inconnu, "montant_limite": "10.00", "mois": "2026-10"}

    # Connecté : ressources inconnues
    cas.append(("POST", "/api/depenses", 404, client.post("/api/depenses", json=depense)))
    cas.append(("POST", "/api/budgets", 404, client.post("/api/budgets", json=budget)))
    cas.append(("GET", "/api/depenses/{depense_id}", 404, client.get(f"/api/depenses/{inconnu}")))
    cas.append(("PATCH", "/api/depenses/{depense_id}", 404, client.patch(
        f"/api/depenses/{inconnu}", json={"libelle": "x"})))
    cas.append(("DELETE", "/api/depenses/{depense_id}", 404, client.delete(f"/api/depenses/{inconnu}")))
    cas.append(("GET", "/api/budgets/{budget_id}", 404, client.get(f"/api/budgets/{inconnu}")))
    cas.append(("PATCH", "/api/budgets/{budget_id}", 404, client.patch(
        f"/api/budgets/{inconnu}", json={"seuil_alerte_pct": 50})))
    cas.append(("DELETE", "/api/budgets/{budget_id}", 404, client.delete(f"/api/budgets/{inconnu}")))
    valide = {"categorie_id": categorie, "montant_limite": "10.00", "mois": "2026-10"}
    assert client.post("/api/budgets", json=valide).status_code == 201
    cas.append(("POST", "/api/budgets", 409, client.post("/api/budgets", json=valide)))

    # Connecté : données invalides (la validation passe avant la recherche de la ressource)
    cas.append(("GET", "/api/depenses", 422, client.get("/api/depenses", params={"limite": 500})))
    cas.append(("GET", "/api/depenses/{depense_id}", 422, client.get("/api/depenses/pas-un-uuid")))
    cas.append(("DELETE", "/api/depenses/{depense_id}", 422, client.delete("/api/depenses/pas-un-uuid")))
    cas.append(("POST", "/api/depenses", 422, client.post(
        "/api/depenses", json={**depense, "categorie_id": categorie, "montant": "0"})))
    cas.append(("PATCH", "/api/depenses/{depense_id}", 422, client.patch(
        f"/api/depenses/{inconnu}", json={"montant": "0"})))
    cas.append(("GET", "/api/budgets", 422, client.get("/api/budgets", params={"mois": "2026-13"})))
    cas.append(("GET", "/api/budgets/{budget_id}", 422, client.get("/api/budgets/pas-un-uuid")))
    cas.append(("DELETE", "/api/budgets/{budget_id}", 422, client.delete("/api/budgets/pas-un-uuid")))
    cas.append(("POST", "/api/budgets", 422, client.post(
        "/api/budgets", json={**valide, "montant_limite": "0"})))
    cas.append(("PATCH", "/api/budgets/{budget_id}", 422, client.patch(
        f"/api/budgets/{inconnu}", json={"seuil_alerte_pct": 500})))

    assert len(cas) == 27  # garde-fou : tous les cas ci-dessus ont bien été construits
    for methode, route, statut, reponse in cas:
        assert reponse.status_code == statut, (methode, route, statut, reponse.text)
        reel = reponse.json()["erreur"]
        exemple = _exemple(openapi, methode, route, statut)
        assert reel["code"] == exemple["code"], (methode, route, statut)
        assert reel["message"] == exemple["message"], (methode, route, statut, reel["message"])
        assert set(reel.get("champs") or {}) == set(exemple.get("champs") or {}), (methode, route, statut)
