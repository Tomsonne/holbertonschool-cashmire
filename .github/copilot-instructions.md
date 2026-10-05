# Instructions de travail pour Cashmire

## Contexte et contrat

Lire `docs/api-design.md`, `docs/data-model.md` et `docs/architecture.md` avant d’intervenir. Le contrat API fait autorité : chemins sous `/api`, JSON en français, erreurs structurées sous `erreur`, montants transmis en chaînes décimales, JWT futur en cookie HttpOnly. Ne pas inventer une route ni modifier le contrat sans décision documentée.

## Conventions

- Python 3.12, FastAPI, SQLAlchemy 2, psycopg 3, Alembic ; Svelte 5, Vite, TypeScript.
- Tables et champs API en français ; noms techniques sans accents.
- Argent : `Decimal` et `NUMERIC(12,2)`, jamais `float`. Dans les schémas Pydantic, utiliser `Montant` ou `MontantPositif` (`app/schemas/montant.py`) et toujours déclarer un `response_model` : sans schéma de réponse, FastAPI renvoie un nombre JSON (`12.5`) au lieu de la chaîne `"12.50"`.
- Erreurs : lever `ErreurApi` (`app/core/erreurs.py`), ne jamais construire une réponse d'erreur à la main ; les gestionnaires garantissent le format `{erreur: {code, message, champs?}}`.
- Toute évolution DB utilise une migration Alembic. Ni `create_all()` ni réinitialisation de schéma au démarrage.
- Pas de secret réel dans Git, pas de mot de passe en clair, pas de fausse réussite ni de route hors contrat.
- Toute donnée privée est filtrée par l’utilisateur authentifié. Le JWT ne peut pas être révoqué côté serveur avant expiration dans le MVP défini.
- Le navigateur appelle `/api` en relatif ; la cible proxy est résolue côté réseau Compose.
- Garder l’architecture pédagogique et les dépendances nécessaires seulement.

## Commandes

- Démarrer : `cp .env.example .env && docker compose up --build`
- Arrêter sans effacer : `docker compose down`
- **Reset destructif des données locales :** `docker compose down --volumes`
- Migrations : `docker compose run --rm migrate`
- Seed idempotent : `docker compose exec api python scripts/seed_categories.py`
- Backend : `cd backend && pytest`
- Frontend : `cd frontend && npm ci && npm test && npm run check && npm run build`

## Sécurité et revue

Ne jamais committer `.env`. En production, cookies `HttpOnly`, `SameSite=Lax`, `Secure`, protections CSRF/origine, secrets injectés à l’exécution et erreurs sans détail SQL/trace interne. Documenter les hypothèses et les commandes réellement exécutées. Ne pas prétendre à une validation de l’équipe ; la revue humaine reste nécessaire.
