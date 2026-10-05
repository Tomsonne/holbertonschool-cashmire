# Conception de l'API

Base : `/api`. Format : JSON, **champs en français**. Authentification : cookie `HttpOnly` (JWT), sauf mention contraire.
Les montants sont des **chaînes décimales** (`"12.50"`) pour éviter toute perte de précision en JavaScript.
Seule exception de langue : `/api/health`, nom conventionnel des routes de supervision.

## Format d'erreur unique
```json
{ "erreur": { "code": "donnees_invalides", "message": "Le montant doit être supérieur à 0.", "champs": { "montant": "doit être > 0" } } }
```
`champs` est optionnel. Jamais de stack trace ni de détail SQL.

| Statut | `code` | Quand |
|---|---|---|
| 400 | `requete_invalide` | Requête mal formée |
| 401 | `non_authentifie` | Pas de session ou session expirée |
| 404 | `introuvable` | Ressource inexistante **ou appartenant à un autre utilisateur** (on ne révèle pas son existence) |
| 409 | `conflit` | Doublon (email, budget du même mois) |
| 422 | `donnees_invalides` | Données invalides |
| 429 | `trop_de_tentatives` | Trop de tentatives de connexion |
| 500 | `erreur_interne` | Erreur serveur, message générique |

## Routes

### Système
| Méthode | Route | Auth | Sortie |
|---|---|---|---|
| GET | `/api/health` | non | `200 {"statut":"ok","base_de_donnees":"disponible"}` ; `503 {"statut":"degrade","base_de_donnees":"indisponible"}` si la base est injoignable |

### Authentification
| Méthode | Route | Entrée | Sortie | Erreurs |
|---|---|---|---|---|
| POST | `/api/authentification/inscription` | `{email, mot_de_passe, nom_affichage}` | `201` utilisateur (sans mot de passe) | 409 email déjà pris, 422 email invalide ou mot de passe trop court (< 10) |
| POST | `/api/authentification/connexion` | `{email, mot_de_passe}` | `200` utilisateur + cookie | 401 identifiants invalides (message identique que l'email existe ou non), 429 |
| POST | `/api/authentification/deconnexion` | | `204` | |
| GET | `/api/authentification/moi` | | `200` utilisateur courant | 401 |

### Catégories
| Méthode | Route | Entrée | Sortie | Erreurs |
|---|---|---|---|---|
| GET | `/api/categories` | | `200` liste des 6 catégories prédéfinies `[{id, nom}]` | 401 |

Les catégories sont prédéfinies, communes à tous et en lecture seule : il n'y a pas de route pour en créer, modifier ou supprimer.

### Dépenses
| Méthode | Route | Entrée | Sortie | Erreurs |
|---|---|---|---|---|
| GET | `/api/depenses?mois=AAAA-MM&categorie_id=&limite=&decalage=` | | `200 {elements, total}` triées par date décroissante | 401, 422 |
| POST | `/api/depenses` | `{montant, libelle, date_depense, categorie_id}` | `201` dépense | 401, 404 catégorie inconnue, 422 |
| GET | `/api/depenses/{id}` | | `200` | 401, 404 |
| PATCH | `/api/depenses/{id}` | champs à modifier | `200` | 401, 404, 422 |
| DELETE | `/api/depenses/{id}` | | `204` | 401, 404 |

### Budgets
| Méthode | Route | Entrée | Sortie | Erreurs |
|---|---|---|---|---|
| GET | `/api/budgets?mois=AAAA-MM` | | `200` liste avec consommation : `{id, categorie, montant_limite, depense, reste, pourcentage, statut}` | 401, 422 |
| POST | `/api/budgets` | `{categorie_id, montant_limite, mois, seuil_alerte_pct?}` | `201` | 401, 404 catégorie inconnue, 409 budget déjà existant ce mois, 422 |
| PATCH | `/api/budgets/{id}` | `{montant_limite?, seuil_alerte_pct?}` | `200` | 401, 404, 422 |
| DELETE | `/api/budgets/{id}` | | `204` | 401, 404 |

`statut` ∈ `ok | attention | depasse` (règle dans [data-model.md](data-model.md)).

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
- Cookies de session : `HttpOnly`, `SameSite=Lax`, `Secure` en production.
- Les routes qui modifient l'état sont protégées contre le CSRF (SameSite + vérification de l'origine).

> **Task 0 :** seule `GET /api/health` est implémentée. Le reste est la conception pour les tâches suivantes.
