# Instructions de travail pour Cashmire

## Contexte et contrat
Cashmire est une application de gestion de budget : API FastAPI, interface Svelte, base PostgreSQL.
Lire `docs/api-design.md`, `docs/data-model.md` et `docs/architecture.md` avant d'intervenir.
Le contrat API fait autorité : chemins sous `/api`, JSON en français, erreurs sous `erreur`,
montants en chaînes décimales, JWT en cookie HttpOnly. Ne pas inventer de route ni modifier le
contrat sans décision documentée.

## Conventions
- Python 3.12, FastAPI, SQLAlchemy 2, psycopg 3, Alembic ; Svelte 5, Vite, TypeScript.
- Langue : base de données, champs de l'API et messages utilisateur en français (sans accents dans les identifiants techniques) ; identifiants Python en anglais.
- Argent : `Decimal` et `NUMERIC(12,2)`, jamais `float`. Dans les schémas Pydantic, utiliser `Montant` ou `MontantPositif` (`app/schemas/montant.py`) et toujours déclarer un `response_model` : sans schéma de réponse, FastAPI renvoie un nombre JSON (`12.5`) au lieu de la chaîne `"12.50"`.
- Erreurs : lever `ErreurApi` (`app/core/erreurs.py`) pour les statuts 4xx uniquement, ne jamais construire une réponse d'erreur à la main ; les gestionnaires garantissent le format `{erreur: {code, message, champs?}}`. Les erreurs 500 ne se lèvent jamais à la main : le gestionnaire générique renvoie un message fixe, sans détail SQL ni trace.
- Toute évolution de la base passe par une migration Alembic. Ni `create_all()` ni réinitialisation du schéma au démarrage.
- Pas de secret réel dans Git, pas de mot de passe en clair, pas de fausse réussite ni de route hors contrat.
- Garder l'architecture simple et les dépendances au minimum.

## Responsabilité des couches
- Route : reçoit la requête, valide l'entrée, appelle un service, renvoie la réponse.
- Service : règles métier et accès à la base ; filtre toujours par l'utilisateur connecté.
- Utilisateur connecté : fourni par une dépendance FastAPI unique, jamais lu depuis le corps de la requête.
- Erreurs : converties au format unique par les gestionnaires globaux (`app/core/gestionnaires.py`), pas route par route.
- Conversion `Decimal` ↔ chaîne : à la frontière des schémas (`Montant`).

## Règles de sécurité du code
- Requêtes SQL paramétrées ; jamais de SQL construit par concaténation.
- Pas de `{@html}` Svelte sur des données utilisateur.
- Ne jamais écrire de mot de passe, de jeton ou de secret dans les logs ni dans les réponses.
- Ne jamais committer `.env` ; seul `.env.example` est versionné, sans secret réel.
- Refuser de démarrer si `JWT_SECRET` est vide ou trop court, y compris en développement.
- Le JWT ne peut pas être révoqué côté serveur avant expiration dans le MVP.
- En production : cookies `HttpOnly`, `SameSite=Lax`, `Secure`, protection CSRF par origine, secrets injectés à l'exécution.

## Accessibilité et interface
- Mobile-first, labels associés aux champs, navigation au clavier, contraste lisible.
- Le navigateur appelle `/api` en relatif ; la cible proxy est résolue côté réseau Compose.
- États de chargement, de succès, d'erreur et de liste vide affichés clairement.

## Workflow
- Cycle : Understand → Plan → Delegate → Verify → Review.
- Une branche par issue, une PR par branche, commits en Conventional Commits (`feat:`, `fix:`, `docs:`, `chore:`).
- Aucun merge de code généré par un agent sans vérification et relecture humaines par un autre membre.
- Seul l'agent QA & Security exécute des commandes, dans les limites fixées par son profil. Full-Stack Development et Product & Architecture n'en exécutent pas : ils listent celles que l'humain doit lancer.
- Le résultat d'une commande lancée par un agent n'est pas une preuve : un humain relance les tests avant la PR.

## Décisions ouvertes : ne pas trancher, les signaler
Statut d'un budget à exactement 100 %, code d'erreur pour une catégorie inconnue,
déconnexion sans authentification requise.

## Décisions tranchées (voir `docs/api-design.md`)
- Durée de vie du JWT : 30 minutes, sans refresh token (issue #8).
- Limitation des tentatives de connexion (429) : 5 échecs sur 15 minutes par email, compteur en mémoire (issue #8).

## Commandes
- Démarrer : `cp .env.example .env && docker compose up --build`
- Arrêter sans effacer : `docker compose down`
- **Reset destructif des données locales** : `docker compose down --volumes`. Ne jamais le lancer sans accord explicite d'un humain.
- Migrations : `docker compose run --rm migrate`
- Seed idempotent : `docker compose exec api python scripts/seed_categories.py`
- Backend : `cd backend && pytest`
- Frontend : `cd frontend && npm ci && npm test && npm run check && npm run build`

## Définition de « terminé »
Tests ajoutés (nominal et erreurs), documentation mise à jour, commandes de vérification listées,
PR relue par un autre membre.