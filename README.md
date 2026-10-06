# Cashmire

Socle pédagogique full-stack pour la gestion des dépenses : Svelte/TypeScript, FastAPI, SQLAlchemy et PostgreSQL. L’API de santé, l’inscription, la connexion et les routes de création, consultation, modification et suppression des budgets mensuels sont implémentées. Les autres routes métier restent à développer.

## Prérequis

- Docker Desktop avec Docker Compose v2
- Git

## Démarrage

```sh
cp .env.example .env
docker compose up --build
```

Ouvrir http://localhost:5173. L’API est accessible sur http://localhost:8000/api/health et sa documentation sur http://localhost:8000/docs. Le frontend appelle `/api/health` en chemin relatif. Vite relaie cette requête vers le service `api` sur le réseau Compose ; le navigateur ne connaît pas le nom Docker `api`.

Compose attend PostgreSQL, exécute `alembic upgrade head` dans le service `migrate`, puis démarre l’API après la réussite des migrations. Les données persistent dans `postgres_data`.

## Configuration

Les paramètres sont listés dans `.env.example`. Les valeurs sont factices et locales. `JWT_SECRET` est obligatoire et doit contenir au moins 32 caractères, y compris en développement et lors des migrations. `JWT_EXPIRE_MINUTES` doit être positif ; sa valeur par défaut est de 30 minutes. `ALLOWED_ORIGINS` reste à raccorder à la protection par origine. En production, le cookie JWT devra être `HttpOnly`, `SameSite=Lax` et `Secure`. Selon le contrat API, la déconnexion effacera le cookie sans révoquer le JWT côté serveur avant son expiration.

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

La création de la base ne se fait qu’une fois ; lors des exécutions suivantes, sautez cette ligne. Si les identifiants PostgreSQL de `.env` diffèrent, adaptez les deux URL. L’image backend ne contient pas les tests : la commande les monte en lecture seule. La fixture de test fixe `JWT_SECRET` et `ENVIRONMENT` avant de charger l’application.

Pour les contrôles frontend :

```sh
cd frontend
npm ci
npm test
npm run check
npm run build
```

En local hors Docker, démarrez PostgreSQL, réglez `DATABASE_URL` sur `localhost`, lancez `uvicorn app.main:app --reload` depuis `backend` et `npm run dev` depuis `frontend`. Adaptez alors la cible du proxy Vite à `http://localhost:8000`.

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
