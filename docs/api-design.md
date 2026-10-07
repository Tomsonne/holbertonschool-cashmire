# Conception de l'API

Base : `/api`. Format : JSON, **champs en français**. Authentification : **JWT** stocké dans un cookie `HttpOnly`, sauf mention contraire.
Les montants sont des **chaînes décimales** (`"12.50"`) pour éviter toute perte de précision en JavaScript :
- **en sortie**, toujours avec deux décimales (`"12.50"`, `"300.00"`, `"-44.60"`), jamais un nombre JSON ;
- **en entrée**, une chaîne avec 2 décimales au plus et 10 chiffres au plus avant la virgule (comme `NUMERIC(12,2)`) ; un nombre JSON (`12.5`), une valeur à 3 décimales (`"12.345"`) ou trop grande est refusé en `422` au lieu d'être arrondi ou de faire échouer l'insertion en base ;
- dans le code, les schémas utilisent `Montant` (négatif possible, par exemple un `reste`) ou `MontantPositif` (`app/schemas/montant.py`).
Seule exception de langue : `/api/health`, nom conventionnel des routes de supervision.

## Format d'erreur unique
```json
{ "erreur": { "code": "donnees_invalides", "message": "Le montant doit être supérieur à 0.", "champs": { "montant": "doit être > 0" } } }
```
`champs` est optionnel. Jamais de stack trace ni de détail SQL.

| Statut | `code` | Quand |
|---|---|---|
| 400 | `requete_invalide` | Requête mal formée |
| 401 | `non_authentifie` | Jeton absent, invalide ou expiré |
| 404 | `introuvable` | Ressource inexistante **ou appartenant à un autre utilisateur** (on ne révèle pas son existence) |
| 409 | `conflit` | Doublon (email, budget du même mois) |
| 422 | `donnees_invalides` | Données invalides |
| 429 | `trop_de_tentatives` | Trop de tentatives de connexion |
| 500 | `erreur_interne` | Erreur serveur, message générique |

### Lever une erreur dans une route
Les routes lèvent `ErreurApi` (`app/core/erreurs.py`) ; le `code` est déduit du statut. **`ErreurApi` est réservée aux statuts 4xx** (le message est renvoyé tel quel au client) : un autre statut lève une `ValueError`, et l'erreur 500 est alors gérée par le gestionnaire générique. Une erreur 500 ne se lève jamais à la main.
```python
from app.core.erreurs import ErreurApi

raise ErreurApi(404, "Dépense introuvable.")
raise ErreurApi(409, "Un budget existe déjà ce mois.", champs={"categorie_id": "Déjà budgétée."})
```
Les gestionnaires (`app/core/gestionnaires.py`) couvrent aussi les cas suivants, sans code à écrire dans les routes :
- **Validation Pydantic :** `422 donnees_invalides`, avec `champs` (message français par champ). La valeur envoyée n'est **jamais** renvoyée : sans cela, FastAPI renverrait par exemple le mot de passe saisi.
- **Corps JSON mal formé :** `400 requete_invalide`.
- **Route inconnue, méthode non autorisée (404, 405) :** même format, statut conservé ; le code est `introuvable` pour 404 et `requete_invalide` pour les autres statuts non listés.
- **Exception inattendue :** `500 erreur_interne` avec un message générique ; la trace n'est écrite que dans les journaux du serveur.

## Routes
La colonne **Connexion requise** indique si l'utilisateur doit être authentifié (cookie JWT valide). Sans connexion, ces routes répondent `401`.

### Système
| Méthode | Route | Connexion requise | Entrée | Sortie | Erreurs |
|---|---|---|---|---|---|
| GET | `/api/health` | Non | | `200 {"statut":"ok","base_de_donnees":"disponible"}` | `503 {"statut":"degrade","base_de_donnees":"indisponible"}` si la base est injoignable |

### Authentification
| Méthode | Route | Connexion requise | Entrée | Sortie | Erreurs |
|---|---|---|---|---|---|
| POST | `/api/authentification/inscription` | Non | `{email, mot_de_passe, nom_affichage}` | `201` utilisateur (sans mot de passe) | 409 email déjà pris, 422 email invalide, mot de passe hors de 10 à 128 caractères ou nom d'affichage hors de 1 à 100 caractères |
| POST | `/api/authentification/connexion` | Non | `{email, mot_de_passe}` | `200` utilisateur `{id, email, nom_affichage, date_creation}` + cookie JWT `access_token` | 401 identifiants invalides (message identique que l'email existe ou non), 422 email invalide, mot de passe de plus de 128 caractères ou champ manquant, 429 trop de tentatives |
| POST | `/api/authentification/deconnexion` | Oui | | `204` + cookie effacé | 401 |
| GET | `/api/authentification/moi` | Oui | | `200` utilisateur courant `{id, email, nom_affichage, date_creation}` (sans mot de passe) | 401 |

**Inscription :** la réponse `201` contient `{id, email, nom_affichage, date_creation}` ; jamais de mot de passe ni de hash. L'email est normalisé (espaces retirés, minuscules) ; l'unicité est insensible à la casse. **L'inscription ne connecte pas l'utilisateur** : aucun cookie ni JWT n'est émis, il faut appeler `/connexion` ensuite. Le mot de passe est haché avec Argon2id.

**Connexion :** l'email est normalisé comme à l'inscription. Le mot de passe n'a **aucun minimum** ni règle de composition (la politique de 10 à 128 caractères ne vaut qu'à l'inscription) : seul le maximum de 128 caractères est contrôlé (`422` au-delà). Un mot de passe de 9 caractères est donc simplement incorrect : `401`, pas `422`. Il n'est jamais nettoyé ni tronqué.
- **Cookie :** `access_token`, `HttpOnly`, `SameSite=Lax`, `Path=/`, `Max-Age` de 30 minutes, `Secure` seulement en production. Le jeton n'apparaît jamais dans le corps JSON. Le JWT (HS256) contient `sub` (identifiant de l'utilisateur), `iat` et `exp`. Durée de vie : **30 minutes, sans refresh token** (`JWT_EXPIRE_MINUTES`, strictement positif) ; la même valeur fixe `exp` et `Max-Age`.
- **`401` :** `{"erreur": {"code": "non_authentifie", "message": "Email ou mot de passe incorrect."}}`, sans `champs`, identique pour un email inconnu et un mauvais mot de passe. Un email inconnu déclenche quand même une vérification Argon2 (contre un hash factice) pour ne pas se distinguer par le temps de réponse.
- **`429` :** après **5 échecs en 15 minutes pour un même email** (normalisé, inconnus compris), toute tentative suivante répond `{"erreur": {"code": "trop_de_tentatives", "message": "Trop de tentatives, réessayez plus tard."}}`, sans `Retry-After`. Le contrôle précède tout calcul Argon2 ; seuls les échecs comptent ; une connexion réussie remet le compteur à zéro. Le compteur est **en mémoire**.
- **Clé de signature :** `JWT_SECRET` est obligatoire (32 caractères au moins, aucune valeur par défaut), y compris en développement et pour `migrate`, car la configuration est chargée à chaque démarrage.

**Déconnexion avec JWT :** la route efface le cookie du navigateur. Le JWT étant sans état, le serveur **n'invalide pas** le jeton : il reste valable jusqu'à son expiration. Pour limiter ce risque, sa durée de vie est courte. C'est une limite connue du MVP, à rappeler dans le README.

### Catégories
| Méthode | Route | Connexion requise | Entrée | Sortie | Erreurs |
|---|---|---|---|---|---|
| GET | `/api/categories` | Oui | | `200` liste des 6 catégories prédéfinies `[{id, nom}]` | 401 |

Les catégories sont prédéfinies, communes à tous et en lecture seule : il n'y a pas de route pour en créer, modifier ou supprimer. La liste est triée par nom (ordre alphabétique) et ne contient que `id` et `nom`.

### Dépenses
| Méthode | Route | Connexion requise | Entrée | Sortie | Erreurs |
|---|---|---|---|---|---|
| GET | `/api/depenses?mois=AAAA-MM&categorie_id=&limite=&decalage=` | Oui | | `200 {elements, total}` triées par date décroissante | 401, 422 |
| POST | `/api/depenses` | Oui | `{montant, libelle, date_depense, categorie_id}` | `201 {id, montant, libelle, date_depense, categorie: {id, nom}}` | 401, 404 catégorie inconnue, 422 |
| GET | `/api/depenses/{id}` | Oui | | `200` dépense | 401, 404 |
| PATCH | `/api/depenses/{id}` | Oui | champs à modifier | `200` dépense modifiée | 401, 404, 422 |
| DELETE | `/api/depenses/{id}` | Oui | | `204` | 401, 404 |

**Règles de `POST /api/depenses` :**
- `montant` : `MontantPositif` (chaîne, strictement positif, 2 décimales au plus). Un nombre JSON, `0`, un négatif ou 3 décimales : 422.
- `libelle` : espaces retirés aux extrémités, de 1 à 200 caractères. Vide ou trop long : 422.
- `date_depense` : date ISO (`AAAA-MM-JJ`), du 01/01/2000 à **demain** inclus (un jour de tolérance pour le fuseau horaire de l'utilisateur). Une dépense a déjà eu lieu : le futur est refusé en 422.
- `categorie_id` : UUID d'une des 6 catégories. UUID mal formé : 422 ; catégorie inexistante : **404** `introuvable`.
- Le propriétaire est **toujours l'utilisateur connecté**. Un `utilisateur_id` envoyé par le client est ignoré, et la réponse ne contient jamais d'identifiant d'utilisateur.
- Un corps qui n'est pas du JSON valide : 400. Rien n'est enregistré en cas d'erreur.

**Paramètres de `GET /api/depenses` :**

| Paramètre | Type | Défaut | Règle |
|---|---|---|---|
| `mois` | `AAAA-MM` | aucun | Filtre sur `date_depense`. Sans ce paramètre, **toutes** les dépenses de l'utilisateur sont renvoyées. Format invalide : 422. |
| `categorie_id` | UUID | aucun | Filtre sur une catégorie. UUID mal formé : 422. |
| `limite` | entier | `20` | Entre 1 et **100**. Hors de cet intervalle : 422. |
| `decalage` | entier | `0` | Supérieur ou égal à 0. Valeur négative : 422. |

Les filtres se combinent. Le tri est toujours par `date_depense` décroissante. `total` est le nombre de dépenses correspondant aux filtres, calculé **avant** la pagination : il ne dépend ni de `limite` ni de `decalage`. Une liste vide renvoie `200 {"elements": [], "total": 0}`.

Précisions :
- Les dépenses du même jour sont départagées par date de création puis par identifiant, pour que deux pages successives ne répètent ni n'oublient aucune dépense.
- Un `categorie_id` bien formé mais inconnu n'est pas une erreur : c'est un filtre qui ne trouve rien (`200`, liste vide). Seul un UUID mal formé donne 422.
- Un `decalage` au-delà du total renvoie `elements` vide et le vrai `total`.

**`GET /api/depenses/{id}` :** renvoie la dépense au même format que la création. Une dépense **inexistante** et une dépense **d'un autre utilisateur** donnent exactement la même réponse (`404 introuvable`) : le client ne peut pas deviner qu'un identifiant existe. Identifiant mal formé : 422.

### Budgets
| Méthode | Route | Connexion requise | Entrée | Sortie | Erreurs |
|---|---|---|---|---|---|
| GET | `/api/budgets?mois=AAAA-MM` | Oui | | `200` liste avec consommation : `{id, categorie, mois, montant_limite, depense, reste, pourcentage, seuil_alerte_pct, statut}` | 401, 422 |
| POST | `/api/budgets` | Oui | `{categorie_id, montant_limite, mois, seuil_alerte_pct?}` | `201` budget avec consommation | 401, 404 catégorie inconnue, 409 budget déjà existant ce mois, 422 |
| GET | `/api/budgets/{id}` | Oui | | `200` un budget avec sa consommation | 401, 404 |
| PATCH | `/api/budgets/{id}` | Oui | `{montant_limite?, seuil_alerte_pct?}` | `200` budget modifié avec consommation | 401, 404, 422 |
| DELETE | `/api/budgets/{id}` | Oui | | `204` | 401, 404 |

`statut` ∈ `ok | attention | depasse` (règle de calcul dans `data-model.md`).

## Exemple de réponse budget
```json
{
  "id": "3f2b8c1e-9a4d-4e7b-8d21-5c6f0a1b9e34",
  "categorie": { "id": "…", "nom": "Alimentation" },
  "mois": "2026-10",
  "montant_limite": "300.00",
  "depense": "255.40",
  "reste": "44.60",
  "pourcentage": 85.13,
  "seuil_alerte_pct": 80,
  "statut": "attention"
}
```

## Règles transverses
- Toute requête de lecture ou d'écriture est filtrée par l'utilisateur authentifié (jamais par un `utilisateur_id` envoyé par le client).
- Cookie de session : `HttpOnly`, `SameSite=Lax`, `Secure` en production.
- La protection CSRF prévue combine `SameSite=Lax` et la vérification de l'origine ; cette dernière reste à raccorder.
- Le JWT n'est pas révocable côté serveur : la sécurité repose sur son expiration courte et sur le cookie `HttpOnly`.

> **Implémentation :** `GET /api/health`, `POST /api/authentification/inscription`, `POST /api/authentification/connexion`, `GET /api/authentification/moi` et les cinq routes budgets (`GET /api/budgets`, `POST /api/budgets`, `GET /api/budgets/{id}`, `PATCH /api/budgets/{id}`, `DELETE /api/budgets/{id}`) sont implémentées. La déconnexion, les catégories et les dépenses restent à développer. Les routes budgets utilisent `Depends(utilisateur_courant)` pour identifier leur propriétaire (#19).
>
> **Dépendance `utilisateur_courant` (issue #9) :** `app/core/authentification.py` lit uniquement le cookie `access_token` (jamais l'en-tête `Authorization`), vérifie signature et expiration (HS256 imposé côté serveur ; `exp` et `sub` obligatoires), convertit `sub` en UUID, puis charge l'utilisateur par une requête SQL (jamais depuis la mémoire de la session). Toute route privée l'utilise via `Depends(utilisateur_courant)`. Tous les échecs (cookie absent ou vide, jeton illisible, mauvaise clé, expiré, mauvais algorithme, `exp` ou `sub` absent, `sub` non UUID, utilisateur inexistant) renvoient la **même** `401` : `{"erreur": {"code": "non_authentifie", "message": "Authentification requise."}}`, sans `champs`. Le JWT n'est **pas révocable** avant son expiration : un jeton reste accepté tant que l'utilisateur existe et que `exp` n'est pas dépassé.

## Limites connues (connexion, issue #8)
- Le compteur de tentatives est **par worker uvicorn** et disparaît au redémarrage.
- Un attaquant qui connaît un email peut **bloquer temporairement** la connexion de ce compte (5 échecs suffisent pendant 15 minutes).
- Le JWT **n'est pas révocable** avant son expiration (30 minutes).
- La protection CSRF par vérification de l'origine **n'est pas traitée dans #8** ; seul `SameSite=Lax` s'applique pour l'instant.
- Deux requêtes simultanées sur un même email peuvent passer avant l'enregistrement d'un échec
- La mémoire du limiteur n'a pas de borne dure
