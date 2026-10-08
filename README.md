# Cashmire

Socle pédagogique full-stack pour la gestion des dépenses : Svelte/TypeScript, FastAPI, SQLAlchemy et PostgreSQL. L’API de santé, l’inscription, la connexion, la déconnexion, la route de l’utilisateur connecté et les routes de création, consultation, modification et suppression des budgets mensuels sont implémentées. Les autres routes métier restent à développer.

## Prérequis

- Docker Desktop avec Docker Compose v2
- Git

## Démarrage

```sh
cp .env.example .env
docker compose up --build
```

Ouvrir http://localhost:5173 : la gestion des budgets est également accessible sur http://localhost:5173/budgets, et la synthèse mensuelle sur http://localhost:5173/synthese. Un formulaire de connexion utilise le cookie JWT de l'API ; il faut disposer d'un compte créé par `POST /api/authentification/inscription` (accessible dans la documentation API). L'ancien écran de santé reste accessible sur http://localhost:5173/etat-technique. L’API est accessible sur http://localhost:8000/api/health et sa documentation sur http://localhost:8000/docs. Le frontend appelle `/api` en chemin relatif. Vite relaie ces requêtes vers le service `api` sur le réseau Compose ; le navigateur ne connaît pas le nom Docker `api`.

La synthèse lit les budgets et toutes les pages de `GET /api/depenses` pour calculer ses totaux sur le mois choisi.

Compose attend PostgreSQL, exécute `alembic upgrade head` dans le service `migrate`, puis démarre l’API après la réussite des migrations. Les données persistent dans `postgres_data`.

## Configuration

Les paramètres sont listés dans `.env.example`. Les valeurs sont factices et locales. `JWT_SECRET` est obligatoire et doit contenir au moins 32 caractères, y compris en développement et lors des migrations. `JWT_EXPIRE_MINUTES` doit être positif ; sa valeur par défaut est de 30 minutes. `ALLOWED_ORIGINS` liste les origines autorisées à écrire dans l’API (`POST`, `PUT`, `PATCH`, `DELETE`) : toute autre origine reçoit une `403`. Format : `http(s)://hote[:port]` séparées par des virgules, sans `/` final et sans `*` ; défaut `http://localhost:5173`. Attention : `http://127.0.0.1:5173` n’est pas `http://localhost:5173`, ouvrez le front sur `localhost` ou ajoutez l’autre origine à la liste. `ENVIRONMENT` vaut `development` (défaut) ou `production` ; toute autre valeur empêche l’API de démarrer. En production, le cookie JWT devra être `HttpOnly`, `SameSite=Lax` et `Secure`. `POST /api/authentification/deconnexion` exige un cookie valide, répond `204` et efface le cookie ; le JWT n’est pas révoqué côté serveur et reste valable jusqu’à son expiration.

Les cinq routes budgets utilisent l’utilisateur authentifié par le cookie JWT via `utilisateur_courant`. Chaque lecture et modification est limitée à ses budgets ; un budget appartenant à un autre utilisateur répond `404`. Sans cookie valide, la réponse est `401`. Aucun identifiant utilisateur n’est accepté dans le corps JSON.

## Migrations et catégories

La migration versionnée crée le schéma et les six catégories partagées : Alimentation, Factures, Loisirs, Transport, Santé et Autre. Pour (ré)assurer leur présence sans doublons :

```sh
docker compose exec api python scripts/seed_categories.py
```

Pour appliquer les migrations manuellement : `docker compose run --rm migrate`.

## Tests et contrôles

Les tests backend exigent `TEST_DATABASE_URL`, qui doit viser une base dédiée dont le nom se termine par `_test`. Créez cette base, puis appliquez-y les migrations avant de lancer les tests. Ils vident les données de cette base entre les cas de test (les catégories issues de la migration sont conservées). Avec les identifiants de `.env.example`, depuis la racine du projet :

```sh
docker compose up -d --wait db
docker compose exec -T db sh -c 'psql -U "$POSTGRES_USER" -d postgres -c "CREATE DATABASE cashmire_test;"'
docker compose build api migrate
docker compose run --rm -e DATABASE_URL=postgresql+psycopg://cashmire:local-only-change-me@db:5432/cashmire_test migrate
docker compose run --rm --no-deps -v "$PWD/backend/tests:/app/tests:ro" -e TEST_DATABASE_URL=postgresql+psycopg://cashmire:local-only-change-me@db:5432/cashmire_test api pytest -p no:cacheprovider
```

La création de la base ne se fait qu’une fois ; lors des exécutions suivantes, sautez cette ligne. Si les identifiants PostgreSQL de `.env` diffèrent, adaptez les deux URL. L’image backend ne contient pas les tests : la commande les monte en lecture seule. La fixture de test fixe `JWT_SECRET`, `JWT_EXPIRE_MINUTES`, `ENVIRONMENT` et `ALLOWED_ORIGINS` avant de charger l’application, et la fixture `client` envoie par défaut l’en-tête `Origin: http://localhost:5173`. Un `TestClient(app)` créé à la main doit l’ajouter lui-même, sinon ses écritures reçoivent une `403`.

Pour les contrôles frontend :

```sh
cd frontend
npm ci
npm test
npm run check
npm run build
```

En local hors Docker, démarrez PostgreSQL, réglez `DATABASE_URL` sur `localhost`, lancez `uvicorn app.main:app --reload` depuis `backend` et `npm run dev` depuis `frontend`. Adaptez alors la cible du proxy Vite à `http://localhost:8000`.

## Frontend : navigation, client API et session

- **Client API** (`frontend/src/lib/api/client.ts`) : `requeteApi` appelle `/api` en relatif avec le cookie. Toute réponse non 2xx lève une `ErreurApi` (`lib/api/erreurs.ts`) portant `status`, `code` et `champs` repris du corps `{erreur: {code, message, champs}}`. Une panne réseau lève `status: 0`, `code: 'reseau'`. Un `204` renvoie `undefined`. `surSessionExpiree(rappel)` enregistre un écouteur appelé sur tout `401`, sauf pour `/authentification/connexion`, `/inscription`, `/moi` et `/deconnexion`, où un `401` ne signifie pas qu'une session ouverte a expiré ; elle renvoie la fonction de désinscription. Le client ne redirige jamais.
- **Store de session** (`frontend/src/lib/session.svelte.ts`) : seule source de l'utilisateur connecté (`utilisateur`, `etat`, `message`) avec `charger()`, `connecter()` et `deconnecter()`. Sur une session expirée, il repasse en `deconnecte` avec le message « Votre session a expiré. Reconnectez-vous. ». Un `401` à la déconnexion vaut déconnexion. Le JWT reste dans le cookie `HttpOnly` et n'est jamais lu par le JavaScript.
- **Ajouter une page** : une ligne dans `frontend/src/lib/routes.ts` (`chemin`, `alias`, `libelle`, `privee`, `navigation`, `ecran`), puis la branche qui rend son composant dans `App.svelte`. La navigation (`lib/components/Navigation.svelte`) lit le même tableau ; la navigation se fait par liens `<a href>` avec rechargement complet.


## Arrêt et reset

`docker compose down` arrête les services en conservant les données.

**Destructif :** ceci supprime le volume PostgreSQL et toutes ses données locales :

```sh
docker compose down --volumes
```

## Organisation

- `backend/app/routes/` : routes HTTP de santé, authentification et gestion des budgets.
- `backend/app/models/`, `schemas/`, `services/`, `db/` : modèles, validation, logique et accès DB.
- `backend/migrations/` : schéma versionné Alembic.
- `frontend/src/lib/api/` : appels HTTP centralisés ; `components/` : UI réutilisable ; `lib/types/` accueillera les types partagés au besoin.
- `.github/agents/` : profils Product & Architecture, Full-Stack Development, QA & Security.

Voir [architecture](docs/architecture.md), [modèle de données](docs/data-model.md), [contrat API](docs/api-design.md) et [journal agentique](docs/agentic-log.md). Lire `.github/copilot-instructions.md` avant de modifier le projet.
