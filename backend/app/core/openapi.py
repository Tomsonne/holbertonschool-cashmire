"""Documentation OpenAPI de l'API (`/docs`, `/openapi.json`).

FastAPI génère l'essentiel (routes, schémas d'entrée et de sortie, paramètres). Ce module complète
ce que le framework ne peut pas deviner, en un seul endroit, sans toucher aux fichiers de routes :
- le cookie d'authentification (schéma de sécurité) et les routes qui l'exigent ;
- les erreurs réelles de l'API : le format unique `{"erreur": {...}}`, et non le format
  `HTTPValidationError` de FastAPI, que nos gestionnaires remplacent ;
- des résumés et descriptions en français, la présentation générale et les limites connues.

Ce qui peut se déduire du code l'est (routes privées, écritures soumises à la vérification de
l'origine, routes à corps JSON) : ces informations ne peuvent pas se périmer. Seuls les textes et les
erreurs « métier » (404, 409, 429) sont écrits ici ; `tests/test_openapi.py` échoue si une route
n'y est pas décrite.
"""

from typing import Any

from fastapi import FastAPI
from fastapi.dependencies.models import Dependant
from fastapi.openapi.utils import get_openapi
from fastapi.routing import APIRoute

from app.core.authentification import utilisateur_courant
from app.core.erreurs import CODES_PAR_STATUT
from app.core.securite import NOM_COOKIE_JWT
from app.schemas.erreur import ReponseErreur

SCHEMA_SECURITE = "cookieJwt"
METHODES_ECRITURE = {"POST", "PUT", "PATCH", "DELETE"}

DESCRIPTION = """\
API de **Cashmire** : suivi de dépenses personnelles et de budgets mensuels par catégorie (euros).

## Authentification
Le jeton est un **JWT** (HS256) porté par le cookie `access_token` (`HttpOnly`, `SameSite=Lax`, 30 minutes,
`Secure` en production). `POST /api/authentification/connexion` le pose ; il n'apparaît jamais dans un
corps JSON. Les routes marquées d'un cadenas exigent ce cookie, sinon `401`.

Depuis cette page : appelez d'abord `/connexion` ; le navigateur garde le cookie et le renvoie aux appels
suivants. Le bouton « Authorize » ne sert pas ici : un navigateur ne permet pas de fixer un cookie à la main.

**Le JWT n'est pas révoqué côté serveur.** `POST /api/authentification/deconnexion` efface seulement le
cookie ; un jeton volé reste valable jusqu'à son expiration.

## Montants
Toujours des **chaînes décimales** (`"12.50"`), jamais des nombres JSON : à l'entrée 2 décimales au plus,
à la sortie exactement 2. Un nombre JSON ou une valeur à 3 décimales est refusé (`422`).

## Erreurs
Format unique : `{"erreur": {"code": "...", "message": "...", "champs": {"champ": "..."}}}` (`champs`
est facultatif). Jamais de trace ni de détail SQL. La valeur envoyée n'est jamais renvoyée.

## Vérification de l'origine
Toute écriture (`POST`, `PUT`, `PATCH`, `DELETE`) dont l'en-tête `Origin` n'est pas dans `ALLOWED_ORIGINS`
reçoit `403 origine_refusee`. Cette page est servie par l'API (origine `http://localhost:8000`), qui n'est
**pas** autorisée par défaut : pour essayer des écritures ici, ajoutez `http://localhost:8000` à
`ALLOWED_ORIGINS` dans `.env` (liste séparée par des virgules) puis redémarrez l'API. Un client de
type `curl` doit envoyer `-H "Origin: http://localhost:5173"`.

## Règles à retenir
- Les **catégories** sont prédéfinies, communes à tous et **en lecture seule** : aucune route d'écriture.
- Chaque utilisateur ne voit que **ses** données : la ressource d'un autre utilisateur répond `404`,
  comme une ressource inexistante.
"""

TAGS = [
    {"name": "systeme", "description": "Supervision de l'API."},
    {"name": "authentification", "description": "Compte, connexion par cookie JWT, déconnexion."},
    {"name": "categories", "description": "Les 6 catégories prédéfinies (lecture seule)."},
    {"name": "depenses", "description": "Dépenses de l'utilisateur connecté."},
    {"name": "budgets", "description": "Budgets mensuels par catégorie, avec leur consommation."},
]

# (méthode, chemin) -> (résumé, description)
OPERATIONS: dict[tuple[str, str], tuple[str, str]] = {
    ("GET", "/api/health"): (
        "Vérifier l'état de l'API",
        "`200` si l'API et la base répondent, `503` si la base est injoignable. Route ouverte.",
    ),
    ("POST", "/api/authentification/inscription"): (
        "Créer un compte",
        "Mot de passe de 10 à 128 caractères, haché avec Argon2id ; email normalisé en minuscules, unique "
        "sans tenir compte de la casse. **Ne connecte pas** l'utilisateur : appeler ensuite `/connexion`.",
    ),
    ("POST", "/api/authentification/connexion"): (
        "Se connecter",
        "Vérifie les identifiants et pose le cookie `access_token`. Même `401` pour un email inconnu et un "
        "mauvais mot de passe. Après 5 échecs en 15 minutes pour un même email : `429`.",
    ),
    ("POST", "/api/authentification/deconnexion"): (
        "Se déconnecter",
        "Efface le cookie. **Le JWT n'est pas révoqué** : il reste valable jusqu'à son expiration (30 min). "
        "Un `401` signifie que la session a déjà expiré.",
    ),
    ("GET", "/api/authentification/moi"): (
        "Consulter l'utilisateur connecté",
        "Renvoie l'utilisateur identifié par le cookie (jamais de mot de passe).",
    ),
    ("GET", "/api/categories"): (
        "Lister les catégories",
        "Les 6 catégories prédéfinies, communes à tous, triées par nom. **Lecture seule** : aucune route "
        "ne permet d'en créer, modifier ou supprimer.",
    ),
    ("POST", "/api/depenses"): (
        "Créer une dépense",
        "Montant strictement positif ; libellé de 1 à 200 caractères ; date du 01/01/2000 à **demain** "
        "inclus. Le propriétaire est toujours l'utilisateur connecté : un `utilisateur_id` envoyé est ignoré.",
    ),
    ("GET", "/api/depenses"): (
        "Lister mes dépenses",
        "Filtres `mois` et `categorie_id` (combinables), pagination `limite`/`decalage`, tri par date "
        "décroissante. `total` compte toutes les dépenses du filtre, **avant** la pagination.",
    ),
    ("GET", "/api/depenses/{depense_id}"): (
        "Consulter une dépense",
        "`404` si la dépense n'existe pas **ou appartient à un autre utilisateur** (même réponse).",
    ),
    ("PATCH", "/api/depenses/{depense_id}"): (
        "Modifier une dépense",
        "Seuls les champs envoyés changent, avec les règles de la création. Champ inconnu, `null` ou corps "
        "vide : `422`. Catégorie inconnue : `404`, et rien n'est modifié.",
    ),
    ("DELETE", "/api/depenses/{depense_id}"): (
        "Supprimer une dépense",
        "`204` sans corps. Suppression définitive ; un second appel répond `404`.",
    ),
    ("GET", "/api/budgets"): (
        "Lister mes budgets",
        "Avec leur consommation du mois : `depense`, `reste` (négatif si dépassé), `pourcentage` et `statut` "
        "(`ok`, `attention` dès le seuil d'alerte, 100 % inclus, `depasse` au-delà de la limite).",
    ),
    ("POST", "/api/budgets"): (
        "Créer un budget",
        "Un seul budget par catégorie et par mois (`409` sinon). Champs inconnus refusés (`422`).",
    ),
    ("GET", "/api/budgets/{budget_id}"): (
        "Consulter un budget",
        "Avec sa consommation. `404` si le budget n'existe pas ou appartient à un autre utilisateur.",
    ),
    ("PATCH", "/api/budgets/{budget_id}"): (
        "Modifier un budget",
        "Limite et/ou seuil d'alerte ; la consommation est recalculée.",
    ),
    ("DELETE", "/api/budgets/{budget_id}"): (
        "Supprimer un budget",
        "`204` sans corps. Les dépenses sont conservées.",
    ),
}

# Erreurs propres à une route, en plus de celles déduites du code (401, 403, 400, 422, 500).
ERREURS_METIER: dict[tuple[str, str], dict[int, str]] = {
    ("POST", "/api/authentification/inscription"): {409: "Un compte existe déjà avec cet email."},
    ("POST", "/api/authentification/connexion"): {
        401: "Email ou mot de passe incorrect (message identique dans les deux cas).",
        429: "Trop de tentatives pour cet email (5 échecs en 15 minutes).",
    },
    ("POST", "/api/depenses"): {404: "Catégorie inconnue."},
    ("GET", "/api/depenses/{depense_id}"): {404: "Dépense inexistante ou appartenant à un autre utilisateur."},
    ("PATCH", "/api/depenses/{depense_id}"): {
        404: "Dépense inexistante ou appartenant à un autre utilisateur, ou catégorie inconnue."
    },
    ("DELETE", "/api/depenses/{depense_id}"): {404: "Dépense inexistante ou appartenant à un autre utilisateur."},
    ("POST", "/api/budgets"): {
        404: "Catégorie inconnue.",
        409: "Un budget existe déjà pour cette catégorie et ce mois.",
    },
    ("GET", "/api/budgets/{budget_id}"): {404: "Budget inexistant ou appartenant à un autre utilisateur."},
    ("PATCH", "/api/budgets/{budget_id}"): {404: "Budget inexistant ou appartenant à un autre utilisateur."},
    ("DELETE", "/api/budgets/{budget_id}"): {404: "Budget inexistant ou appartenant à un autre utilisateur."},
}

DESCRIPTIONS_ERREUR = {
    400: "Requête illisible (corps qui n'est pas du JSON valide).",
    401: "Authentification requise : cookie absent, invalide ou expiré.",
    403: "Origine non autorisée pour une écriture (voir `ALLOWED_ORIGINS`).",
    404: "Introuvable.",
    409: "Conflit.",
    422: "Données invalides : `champs` indique chaque champ fautif, sans renvoyer la valeur envoyée.",
    429: "Trop de tentatives.",
    500: "Erreur interne : message générique, jamais de détail technique.",
}

MESSAGES_EXEMPLE = {
    400: "Le corps de la requête n'est pas un JSON valide.",
    401: "Authentification requise.",
    403: "Origine non autorisée.",
    404: "Ressource introuvable.",
    409: "Conflit.",
    422: "Certaines données sont invalides.",
    429: "Trop de tentatives, réessayez plus tard.",
    500: "Une erreur interne est survenue.",
}

PARAMETRES = {
    "mois": "Mois au format `AAAA-MM` (par exemple `2026-10`).",
    "categorie_id": "Identifiant (UUID) d'une catégorie.",
    "limite": "Nombre de dépenses par page : de 1 à 100 (20 par défaut).",
    "decalage": "Nombre de dépenses à sauter avant la page (0 par défaut) : `decalage = (page - 1) × limite`.",
    "depense_id": "Identifiant (UUID) de la dépense.",
    "budget_id": "Identifiant (UUID) du budget.",
}

# Schémas de corps de PATCH : un champ facultatif ne peut pas valoir `null` (refusé en 422).
SCHEMAS_DE_MODIFICATION = ("DepenseModification", "BudgetModification")


def _exige_connexion(dependant: Dependant) -> bool:
    """Vrai si la route dépend, directement ou non, de `utilisateur_courant`."""
    return any(d.call is utilisateur_courant or _exige_connexion(d) for d in dependant.dependencies)


def _reponse_erreur(statut: int, description: str) -> dict[str, Any]:
    exemple: dict[str, Any] = {"code": CODES_PAR_STATUT[statut], "message": MESSAGES_EXEMPLE[statut]}
    if statut == 422:
        exemple["champs"] = {"montant": "Valeur trop petite."}
    return {
        "description": description,
        "content": {
            "application/json": {
                "schema": {"$ref": "#/components/schemas/ReponseErreur"},
                "example": {"erreur": exemple},
            }
        },
    }


def _documenter_operation(operation: dict[str, Any], route: APIRoute, methode: str) -> None:
    cle = (methode, route.path)
    if cle in OPERATIONS:
        operation["summary"], operation["description"] = OPERATIONS[cle]

    for parametre in operation.get("parameters", []):
        if "description" not in parametre and parametre["name"] in PARAMETRES:
            parametre["description"] = PARAMETRES[parametre["name"]]

    reponses = operation["responses"]
    privee = _exige_connexion(route.dependant)
    if privee:
        operation["security"] = [{SCHEMA_SECURITE: []}]
        reponses["401"] = _reponse_erreur(401, DESCRIPTIONS_ERREUR[401])
    if methode in METHODES_ECRITURE:
        reponses["403"] = _reponse_erreur(403, DESCRIPTIONS_ERREUR[403])
    if route.body_field is not None:
        reponses["400"] = _reponse_erreur(400, DESCRIPTIONS_ERREUR[400])
    if "422" in reponses:
        reponses["422"] = _reponse_erreur(422, DESCRIPTIONS_ERREUR[422])
    for statut, description in ERREURS_METIER.get(cle, {}).items():
        reponses[str(statut)] = _reponse_erreur(statut, description)
    reponses["500"] = _reponse_erreur(500, DESCRIPTIONS_ERREUR[500])
    operation["responses"] = dict(sorted(reponses.items()))


def _retirer_schemas_fastapi(schemas: dict[str, Any], document: dict[str, Any]) -> None:
    """Retire `HTTPValidationError` quand plus aucune réponse n'y renvoie : nos gestionnaires
    remplacent ce format par `ReponseErreur`, il serait trompeur de le laisser."""
    texte = str(document["paths"])
    if "HTTPValidationError" not in texte:
        schemas.pop("HTTPValidationError", None)
        schemas.pop("ValidationError", None)


def _preciser_modifications(schemas: dict[str, Any]) -> None:
    for nom in SCHEMAS_DE_MODIFICATION:
        schema = schemas.get(nom)
        if schema is None:
            continue
        schema["description"] = (
            "Corps d'un `PATCH` : seuls les champs envoyés changent. Au moins un champ ; un champ inconnu "
            "ou valant `null` est refusé (`422`)."
        )
        for propriete, definition in schema.get("properties", {}).items():
            options = [o for o in definition.get("anyOf", []) if o != {"type": "null"}]
            if len(options) == 1 and len(definition["anyOf"]) == 2:
                reste = {k: v for k, v in definition.items() if k not in ("anyOf", "default")}
                schema["properties"][propriete] = {**options[0], **reste}


def construire_openapi(app: FastAPI) -> dict[str, Any]:
    if app.openapi_schema:
        return app.openapi_schema
    document = get_openapi(
        title=app.title,
        version=app.version,
        description=DESCRIPTION,
        routes=app.routes,
        tags=TAGS,
    )
    composants = document.setdefault("components", {})
    schemas = composants.setdefault("schemas", {})

    erreur = ReponseErreur.model_json_schema(ref_template="#/components/schemas/{model}")
    schemas.update(erreur.pop("$defs", {}))
    schemas["ReponseErreur"] = erreur
    composants["securitySchemes"] = {
        SCHEMA_SECURITE: {
            "type": "apiKey",
            "in": "cookie",
            "name": NOM_COOKIE_JWT,
            "description": "JWT posé par `POST /api/authentification/connexion` (HttpOnly, 30 min, non révocable).",
        }
    }

    for route in app.routes:
        if isinstance(route, APIRoute) and route.path.startswith("/api"):
            for methode in sorted(route.methods - {"HEAD", "OPTIONS"}):
                _documenter_operation(document["paths"][route.path][methode.lower()], route, methode)

    _retirer_schemas_fastapi(schemas, document)
    _preciser_modifications(schemas)
    app.openapi_schema = document
    return document


def personnaliser_openapi(app: FastAPI) -> None:
    """À appeler une fois toutes les routes montées."""
    app.openapi = lambda: construire_openapi(app)  # type: ignore[method-assign]
