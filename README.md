# Cashmire

Socle pédagogique full-stack pour la gestion des dépenses : Svelte/TypeScript, FastAPI, SQLAlchemy et PostgreSQL. L’API du MVP est complète : santé, inscription, connexion, déconnexion, utilisateur connecté, catégories (lecture seule), dépenses (création, liste, détail, modification, suppression) et budgets mensuels avec leur consommation. Le frontend propose les pages Budgets, Dépenses et Synthèse, ainsi que les écrans d’inscription et de connexion.

## Prérequis

- Docker Desktop avec Docker Compose v2
- Git
- Node 22 et npm, seulement pour lancer les contrôles frontend hors Docker (la CI et l’image utilisent Node 22)
- Python 3.12, seulement pour lancer le backend hors Docker

## Démarrage

```sh
cp .env.example .env
docker compose up --build
```

Ouvrir http://localhost:5173 : la gestion des budgets est également accessible sur http://localhost:5173/budgets, et la synthèse mensuelle sur http://localhost:5173/synthese. Un formulaire de connexion utilise le cookie JWT de l'API ; il faut disposer d'un compte : créez-le sur http://localhost:5173/inscription (ou avec `curl`, voir « Documentation de l'API » ci-dessous). L'ancien écran de santé reste accessible sur http://localhost:5173/etat-technique. L’API est accessible sur http://localhost:8000/api/health et sa documentation sur http://localhost:8000/docs. Le frontend appelle `/api` en chemin relatif. Vite relaie ces requêtes vers le service `api` sur le réseau Compose ; le navigateur ne connaît pas le nom Docker `api`.

La synthèse lit les budgets et toutes les pages de `GET /api/depenses` pour calculer ses totaux sur le mois choisi.

Compose attend PostgreSQL, exécute `alembic upgrade head` dans le service `migrate`, puis démarre l’API après la réussite des migrations. Les données persistent dans `postgres_data`.

## Documentation de l'API

La documentation interactive (OpenAPI) est servie par l'API sur http://localhost:8000/docs ; le contrat brut est sur http://localhost:8000/openapi.json. Elle décrit toutes les routes, les schémas, le cookie d'authentification, les montants (chaînes décimales) et les erreurs réelles (format unique `{"erreur": {...}}`, sauf `GET /api/health`, qui renvoie son propre format quand la base est injoignable). Le contrat rédigé à la main est dans [docs/api-design.md](docs/api-design.md) ; des tests vérifient que les deux décrivent exactement les routes du code.

**Créer un compte de test.** Toute écriture doit venir d'une origine autorisée (voir `ALLOWED_ORIGINS` ci-dessous) : sans origine autorisée (en-tête `Origin`, ou à défaut `Referer`), la réponse est `403`. Avec `curl` :

```sh
curl -X POST http://localhost:8000/api/authentification/inscription \
  -H "Content-Type: application/json" -H "Origin: http://localhost:5173" \
  -d '{"email":"ada@example.com","mot_de_passe":"un-mot-de-passe-long","nom_affichage":"Ada"}'
```

Aucun compte de démonstration n'est fourni pour l'instant : créez le vôtre (page d'inscription du frontend ou `curl`).

**Essayer l'API depuis `/docs`.** Cette page est servie par l'API (origine `http://localhost:8000`), qui n'est pas autorisée par défaut : ses essais d'écriture reçoivent `403`. Dans `.env`, mettez `ALLOWED_ORIGINS=http://localhost:5173,http://localhost:8000`, puis `docker compose up -d --force-recreate api`. Appelez d'abord `/api/authentification/connexion` : le navigateur garde le cookie et le renvoie aux appels suivants (le bouton « Authorize » ne peut pas fixer un cookie).

## Configuration

Les paramètres sont listés dans `.env.example`. Les valeurs sont factices et locales. `JWT_SECRET` est obligatoire et doit contenir au moins 32 caractères, y compris en développement et lors des migrations. Avec `ENVIRONMENT=production`, les secrets d’exemple publics (celui de `.env.example`, les clés des tests et de la CI) sont refusés au démarrage. `JWT_EXPIRE_MINUTES` doit être positif ; sa valeur par défaut est de 30 minutes. `ALLOWED_ORIGINS` liste les origines autorisées à écrire dans l’API (`POST`, `PUT`, `PATCH`, `DELETE`) : toute autre origine reçoit une `403`. Format : `http(s)://hote[:port]` séparées par des virgules, sans `/` final et sans `*` ; défaut `http://localhost:5173`. Attention : `http://127.0.0.1:5173` n’est pas `http://localhost:5173`, ouvrez le front sur `localhost` ou ajoutez l’autre origine à la liste. `ENVIRONMENT` vaut `development` (défaut) ou `production` ; toute autre valeur empêche l’API de démarrer. En production, le cookie JWT devra être `HttpOnly`, `SameSite=Lax` et `Secure`. `POST /api/authentification/deconnexion` exige un cookie valide, répond `204` et efface le cookie ; le JWT n’est pas révoqué côté serveur et reste valable jusqu’à son expiration.

Toutes les routes privées (utilisateur connecté, catégories, dépenses, budgets) identifient l’utilisateur par le cookie JWT via `utilisateur_courant`. Chaque lecture, modification et suppression est limitée à ses propres données : la ressource d’un autre utilisateur répond `404`, comme une ressource inexistante. Sans cookie valide, la réponse est `401`. Aucun identifiant utilisateur n’est accepté dans le corps JSON. `backend/tests/test_isolation.py` le vérifie, y compris que chaque route privée exige une connexion.

## Avant un déploiement

Les valeurs de `.env.example` sont **publiques** (elles sont dans le dépôt) : ne les réutilisez jamais hors de votre machine. Avant tout déploiement :
- générez un `JWT_SECRET` aléatoire (`openssl rand -hex 32`, puis collez le **résultat** dans `.env`) ;
- choisissez un `POSTGRES_PASSWORD` fort et reportez-le dans `DATABASE_URL` ;
- mettez `ENVIRONMENT=production` (le cookie devient `Secure`) ;
- remplacez `ALLOWED_ORIGINS` par l'origine HTTPS réelle du frontend.

Ces valeurs sont publiques : avec le `JWT_SECRET` d'exemple, n'importe qui pourrait fabriquer un jeton valide et se faire passer pour un utilisateur. Avec `ENVIRONMENT=production`, l'application **refuse de démarrer** avec ce secret d'exemple (et avec les clés des tests et de la CI). Elle ne juge pas la qualité d'un autre secret : générez-le toujours avec `openssl rand -hex 32`.

## Migrations et catégories

La migration versionnée crée le schéma et les six catégories partagées : Alimentation, Factures, Loisirs, Transport, Santé et Autre. Elles sont **en lecture seule** : `GET /api/categories` les liste, aucune route ne permet d’en créer, modifier ou supprimer. Pour (ré)assurer leur présence sans doublons :

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
docker compose run --rm --no-deps -v "$PWD/backend/tests:/app/tests:ro" -v "$PWD/docs:/docs:ro" -v "$PWD/.env.example:/.env.example:ro" -e TEST_DATABASE_URL=postgresql+psycopg://cashmire:local-only-change-me@db:5432/cashmire_test api pytest -p no:cacheprovider
```

La création de la base ne se fait qu’une fois ; lors des exécutions suivantes, sautez cette ligne. Si les identifiants PostgreSQL de `.env` diffèrent, adaptez les deux URL. L’image backend ne contient pas les tests : la commande les monte en lecture seule, avec `docs/` et `.env.example` que lisent les tests de cohérence entre les documents, la configuration et le code (sans ces montages, ils sont ignorés ; la CI les exécute toujours). La CI GitHub Actions (`.github/workflows/ci.yml`) lance les tests backend et frontend, la vérification des types et le build sur chaque pull request vers `main`. La fixture de test fixe `JWT_SECRET`, `JWT_EXPIRE_MINUTES`, `ENVIRONMENT` et `ALLOWED_ORIGINS` avant de charger l’application, et la fixture `client` envoie par défaut l’en-tête `Origin: http://localhost:5173`. Un `TestClient(app)` créé à la main doit l’ajouter lui-même, sinon ses écritures reçoivent une `403`.

Pour les contrôles frontend :

```sh
cd frontend
npm ci
npm test
npm run check
npm run build
```

En local hors Docker (Python 3.12 et Node 22), démarrez PostgreSQL et réglez `DATABASE_URL` sur `localhost`. Depuis `backend` : `python -m pip install -r requirements.lock`, `alembic upgrade head`, puis `uvicorn app.main:app --reload`. Depuis `frontend` : `npm ci`, puis `npm run dev`. Adaptez alors la cible du proxy Vite (`server.proxy` dans `frontend/vite.config.ts`, `http://api:8000` par défaut) à `http://localhost:8000`.

## Frontend : navigation, client API et session

- **Client API** (`frontend/src/lib/api/client.ts`) : `requeteApi` appelle `/api` en relatif avec le cookie. Toute réponse non 2xx lève une `ErreurApi` (`lib/api/erreurs.ts`) portant `status`, `code` et `champs` repris du corps `{erreur: {code, message, champs}}`. Une panne réseau lève `status: 0`, `code: 'reseau'`. Un `204` renvoie `undefined`. `surSessionExpiree(rappel)` enregistre un écouteur appelé sur tout `401`, sauf pour `/authentification/connexion`, `/inscription`, `/moi` et `/deconnexion`, où un `401` ne signifie pas qu'une session ouverte a expiré ; elle renvoie la fonction de désinscription. Le client ne redirige jamais.
- **Store de session** (`frontend/src/lib/session.svelte.ts`) : seule source de l'utilisateur connecté (`utilisateur`, `etat`, `message`) avec `charger()`, `connecter()` et `deconnecter()`. Sur une session expirée, il repasse en `deconnecte` avec le message « Votre session a expiré. Reconnectez-vous. ». Un `401` à la déconnexion vaut déconnexion. Le JWT reste dans le cookie `HttpOnly` et n'est jamais lu par le JavaScript.
- **Connexion et inscription** : deux pages publiques, `/connexion` et `/inscription` (composants `lib/components/Connexion.svelte` et `Inscription.svelte`), qui n'appellent jamais `/moi`. Après une connexion réussie sur `/connexion`, l'application redirige vers `/budgets` (`aller` de `lib/navigation.ts`). Les pages privées gardent leur propre formulaire de connexion en place, sans redirection, et chargent les catégories après le succès. La navigation d'un visiteur propose « Connexion » et « Créer un compte ».
- **Erreurs des formulaires d'accès** : une erreur de soumission ne masque jamais le formulaire et les saisies sont conservées. Les messages viennent de `messageErreurAuth` (`lib/authentification.ts`) : message de l'API pour `401`, `403` et `429` ; « Un compte existe déjà avec cette adresse e-mail. » pour un `409` à l'inscription ; « Vérifiez les champs du formulaire. » pour un `422`, avec l'erreur de chaque champ affichée sous celui-ci (`aria-invalid`, `aria-describedby`) ; « Impossible de joindre le service. Réessayez. » sinon. « Service indisponible » est réservé à l'échec du chargement initial de la session ou des catégories.
- **Mot de passe** : de 10 à 128 caractères à l'inscription (`minlength`/`maxlength`) ; à la connexion, seul le maximum de 128 est appliqué, sans minimum, comme le contrat API. **L'inscription ne connecte pas** : après le `201`, un message invite à se connecter avec un lien vers `/connexion`.
- **Ajouter une page** : une ligne dans `frontend/src/lib/routes.ts` (`chemin`, `alias`, `libelle`, `privee`, `navigation`, `ecran`), puis la branche qui rend son composant dans `App.svelte`. La navigation (`lib/components/Navigation.svelte`) lit le même tableau ; la navigation se fait par liens `<a href>` avec rechargement complet.


## Limites connues

- **JWT non révocable :** la déconnexion efface le cookie, mais le jeton reste valable jusqu’à son expiration (30 minutes par défaut).
- **Limiteur de connexion en mémoire :** 5 échecs en 15 minutes par email, compteur propre à chaque processus et perdu au redémarrage ; un tiers qui connaît un email peut en bloquer la connexion **jusqu’à 15 minutes**, et prolonger le blocage en espaçant ses essais (un échec dès qu’une place se libère).
- **Origine des écritures :** le comportement derrière un reverse proxy qui réécrit `Origin` ou `Referer` n’est pas traité ; `/docs` demande d’ajouter son origine à `ALLOWED_ORIGINS` (voir plus haut).
- **Illustrations du frontend :** environ 12 Mo de PNG (`frontend/public/assets/cashmire`) ; une conversion en WebP et un redimensionnement sont prévus (éco-conception).
- **Secrets faibles :** seuls les secrets d’exemple publics connus sont refusés en production ; un secret court en apparence aléatoire ou faible, mais inconnu, n’est pas détecté (voir « Avant un déploiement »). Le mot de passe PostgreSQL d’exemple n’est pas contrôlé non plus.
- **Énumération des comptes :** l’inscription répond `409` « Un compte existe déjà avec cet email. » : elle révèle qu’un email est inscrit, contrairement à la connexion, qui répond le même `401` dans les deux cas. Compromis assumé du MVP (le masquer demanderait une vérification par email).
- **Consommation de budget très élevée :** si la somme des dépenses d’un budget dépasse 9 999 999 999,99 €, la réponse échoue en `500` (la limite de 10 chiffres s’applique aussi aux sommes calculées) ; le budget est quand même créé, puis la liste des budgets de ce mois répond `500`. Bug connu, à corriger.
- **Catégories :** six catégories prédéfinies, communes et en lecture seule ; les catégories personnelles sont une extension possible après le MVP.
- **Synthèse mensuelle :** calculée dans le navigateur à partir de toutes les pages de dépenses du mois ; une route d’agrégats côté API serait plus adaptée à de gros volumes.

## Arrêt et reset

`docker compose down` arrête les services en conservant les données.

**Destructif :** ceci supprime le volume PostgreSQL et toutes ses données locales :

```sh
docker compose down --volumes
```

## Organisation

- `backend/app/routes/` : routes HTTP (santé, authentification, catégories, dépenses, budgets) ; `backend/app/core/` : configuration, sécurité (JWT, Argon2), erreurs, vérification d’origine et documentation OpenAPI.
- `backend/app/models/`, `schemas/`, `services/`, `db/` : modèles, validation, logique et accès DB.
- `backend/migrations/` : schéma versionné Alembic.
- `frontend/src/lib/api/` : appels HTTP centralisés ; `components/` : UI réutilisable ; `lib/types/` accueillera les types partagés au besoin.
- `.github/agents/` : profils Product & Architecture, Full-Stack Development, QA & Security.

Voir [architecture](docs/architecture.md), [modèle de données](docs/data-model.md), [contrat API](docs/api-design.md) et [journal agentique](docs/agentic-log.md). Lire `.github/copilot-instructions.md` avant de modifier le projet.
