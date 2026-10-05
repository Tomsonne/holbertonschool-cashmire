# Conception de l'API

Base : `/api`. Format : JSON, **champs en français**. Authentification : **JWT** stocké dans un cookie `HttpOnly`, sauf mention contraire.
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
| 401 | `non_authentifie` | Jeton absent, invalide ou expiré |
| 404 | `introuvable` | Ressource inexistante **ou appartenant à un autre utilisateur** (on ne révèle pas son existence) |
| 409 | `conflit` | Doublon (email, budget du même mois) |
| 422 | `donnees_invalides` | Données invalides |
| 429 | `trop_de_tentatives` | Trop de tentatives de connexion |
| 500 | `erreur_interne` | Erreur serveur, message générique |

## Routes
La colonne **Connexion requise** indique si l'utilisateur doit être authentifié (cookie JWT valide). Sans connexion, ces routes répondent `401`.

### Système
| Méthode | Route | Connexion requise | Entrée | Sortie | Erreurs |
|---|---|---|---|---|---|
| GET | `/api/health` | Non | | `200 {"statut":"ok","base_de_donnees":"disponible"}` | `503 {"statut":"degrade","base_de_donnees":"indisponible"}` si la base est injoignable |

### Authentification
| Méthode | Route | Connexion requise | Entrée | Sortie | Erreurs |
|---|---|---|---|---|---|
| POST | `/api/authentification/inscription` | Non | `{email, mot_de_passe, nom_affichage}` | `201` utilisateur (sans mot de passe) | 409 email déjà pris, 422 email invalide ou mot de passe trop court (< 10) |
| POST | `/api/authentification/connexion` | Non | `{email, mot_de_passe}` | `200` utilisateur + cookie JWT | 401 identifiants invalides (message identique que l'email existe ou non), 422, 429 |
| POST | `/api/authentification/deconnexion` | Oui | | `204` + cookie effacé | 401 |
| GET | `/api/authentification/moi` | Oui | | `200` utilisateur courant | 401 |

**Déconnexion avec JWT :** la route efface le cookie du navigateur. Le JWT étant sans état, le serveur **n'invalide pas** le jeton : il reste valable jusqu'à son expiration. Pour limiter ce risque, sa durée de vie est courte. C'est une limite connue du MVP, à rappeler dans le README.

### Catégories
| Méthode | Route | Connexion requise | Entrée | Sortie | Erreurs |
|---|---|---|---|---|---|
| GET | `/api/categories` | Oui | | `200` liste des 6 catégories prédéfinies `[{id, nom}]` | 401 |

Les catégories sont prédéfinies, communes à tous et en lecture seule : il n'y a pas de route pour en créer, modifier ou supprimer.

### Dépenses
| Méthode | Route | Connexion requise | Entrée | Sortie | Erreurs |
|---|---|---|---|---|---|
| GET | `/api/depenses?mois=AAAA-MM&categorie_id=&limite=&decalage=` | Oui | | `200 {elements, total}` triées par date décroissante | 401, 422 |
| POST | `/api/depenses` | Oui | `{montant, libelle, date_depense, categorie_id}` | `201` dépense | 401, 404 catégorie inconnue, 422 |
| GET | `/api/depenses/{id}` | Oui | | `200` dépense | 401, 404 |
| PATCH | `/api/depenses/{id}` | Oui | champs à modifier | `200` dépense modifiée | 401, 404, 422 |
| DELETE | `/api/depenses/{id}` | Oui | | `204` | 401, 404 |

**Paramètres de `GET /api/depenses` :**

| Paramètre | Type | Défaut | Règle |
|---|---|---|---|
| `mois` | `AAAA-MM` | aucun | Filtre sur `date_depense`. Sans ce paramètre, **toutes** les dépenses de l'utilisateur sont renvoyées. Format invalide : 422. |
| `categorie_id` | UUID | aucun | Filtre sur une catégorie. UUID mal formé : 422. |
| `limite` | entier | `20` | Entre 1 et **100**. Hors de cet intervalle : 422. |
| `decalage` | entier | `0` | Supérieur ou égal à 0. Valeur négative : 422. |

Les filtres se combinent. Le tri est toujours par `date_depense` décroissante. `total` est le nombre de dépenses correspondant aux filtres, calculé **avant** la pagination : il ne dépend ni de `limite` ni de `decalage`. Une liste vide renvoie `200 {"elements": [], "total": 0}`.

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
- Les routes qui modifient l'état sont protégées contre le CSRF (SameSite + vérification de l'origine).
- Le JWT n'est pas révocable côté serveur : la sécurité repose sur son expiration courte et sur le cookie `HttpOnly`.

> **Task 0 :** seule `GET /api/health` est implémentée. Le reste est la conception pour les tâches suivantes.
