# Cashmire

Socle pédagogique full-stack pour la gestion des dépenses : Svelte/TypeScript, FastAPI, SQLAlchemy et PostgreSQL. À ce stade seule la route `GET /api/health` est implémentée ; l’authentification, les dépenses et les budgets restent à développer.

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

Les paramètres sont listés dans `.env.example`. Les valeurs sont factices et locales. `JWT_SECRET`, `JWT_EXPIRE_MINUTES` (30 minutes provisoires) et `ALLOWED_ORIGINS` préparent le travail d’authentification, mais ne sont pas encore employés. En production, le cookie JWT devra être `HttpOnly`, `SameSite=Lax` et `Secure`. Selon le contrat API, la déconnexion effacera le cookie sans révoquer le JWT côté serveur avant son expiration.

## Migrations et catégories

La migration versionnée crée le schéma et les six catégories partagées : Alimentation, Factures, Loisirs, Transport, Santé et Autre. Pour (ré)assurer leur présence sans doublons :

```sh
docker compose exec api python scripts/seed_categories.py
```

Pour appliquer les migrations manuellement : `docker compose run --rm migrate`.

## Tests et contrôles

```sh
cd backend
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.lock
pytest
cd ../frontend
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

- `backend/app/routes/` : routes HTTP ; seule la santé existe pour cette étape.
- `backend/app/models/`, `schemas/`, `services/`, `db/` : modèles, validation, logique et accès DB.
- `backend/migrations/` : schéma versionné Alembic.
- `frontend/src/lib/api/` : appels HTTP centralisés ; `components/` : UI réutilisable ; `lib/types/` accueillera les types partagés au besoin.
- `.github/agents/` : profils Product & Architecture, Full-Stack Development, QA & Security.

Voir [architecture](docs/architecture.md), [modèle de données](docs/data-model.md), [contrat API](docs/api-design.md) et [journal agentique](docs/agentic-log.md). Lire `.github/copilot-instructions.md` avant de modifier le projet.
