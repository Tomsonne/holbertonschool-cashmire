# Journal agentique

## Initialisation du socle — 2026-10-05

- **Demande :** construire le premier socle Cashmire, DB/migration, route santé, page Svelte, documentation et tests, sans livrer authentification, dépenses ni budgets.
- **Proposition appliquée :** monolithe FastAPI + SQLAlchemy/Alembic + PostgreSQL 16, Svelte/Vite/TypeScript, Compose avec service explicite de migration. La migration crée les quatre tables et six catégories existantes dans `docs/data-model.md`; le seed séparé est idempotent.
- **Vérifications exécutées :** dépôt initialement vide et aucun changement préexistant ; documents existants restaurés et lus depuis `origin/main` ; branche `chore/initial-architecture` créée. `docker compose config -q` et `git diff --check` passent. Stack construite et démarrée sur le nouveau volume dédié `holbertonschool-cashmire_postgres_data`; PostgreSQL et API rapportent `healthy`, le frontend démarre sainement. La migration initiale a été appliquée sur ce volume vierge et `docker compose run --rm migrate` a ensuite été rejoué sans erreur. Le seed a été exécuté deux fois et `SELECT count(*) FROM categories` retourne 6. Le proxy du frontend répond `{"statut":"ok","base_de_donnees":"disponible"}`. Une requête de santé via TestClient avec PostgreSQL répond 200 avec le contrat attendu ; en remplaçant le moteur par une cible inaccessible, elle répond 503 avec le JSON dégradé exact. `backend/.venv/bin/pytest`: 2 tests réussis. `npm test`: 1 test réussi (échec réseau puis bouton de réessai), `npm run check` : 0 diagnostic, `npm run build` réussi, `npm audit` : 0 vulnérabilité. Le SQL Alembic a aussi été généré hors ligne. Les appels host-loopback `curl localhost:8000/5173` étaient bloqués par le sandbox ; le chemin applicatif navigateur→proxy→API a été vérifié depuis les conteneurs.
- **Limites :** JWT seulement préparé en configuration ; 30 minutes provisoires. La frontière à 100 % doit être confirmée. Aucun retour des étudiants n’a été recueilli.
- **Revue humaine :** en attente.

---

## Catégories : partagées, par utilisateur ou mixtes ? — décision de cadrage

- **Problème :** l'énoncé demande de définir une stratégie de catégories ; elle conditionne le modèle de données, l'isolation entre utilisateurs et les tests.
- **Rôle utilisé :** Product & Architecture.
- **Délégué :** comparer les options (catégories partagées, personnelles, mixtes) au regard du périmètre du MVP.
- **Proposition de l'agent :** un modèle « mixte » (catégories prédéfinies et catégories créées par chaque utilisateur).
- **Vérification :** relue par l'équipe contre le parcours du MVP (dépense → budget → alerte) et contre le coût réel : propriété des catégories, unicité par utilisateur, routes d'écriture à protéger, tests d'isolation supplémentaires.
- **Rejeté / accepté :** le modèle mixte est **rejeté pour le MVP**. Accepté : six catégories prédéfinies (Alimentation, Factures, Loisirs, Transport, Santé, Autre), partagées, en **lecture seule**, avec des identifiants fixes et un seed rejouable sans doublon.
- **Décision finale et pourquoi :** un nouvel utilisateur peut saisir une dépense immédiatement, sans configuration ; aucune route d'écriture sur les catégories, donc moins de surface d'attaque ; l'extension aux catégories personnelles reste possible par une migration. Les catégories personnelles sont listées comme amélioration, pas comme oubli.

## Un montant que Pydantic accepte et que PostgreSQL refuse — issue #6, PR #31

- **Problème :** valider les montants sans jamais utiliser de `float`, avec une limite compatible avec `NUMERIC(12,2)`.
- **Rôle utilisé :** Full-Stack Development.
- **Délégué :** écrire les types de montants (entrée en chaîne, deux décimales, sortie en chaîne).
- **Proposition de l'agent :** limiter la taille avec `max_digits=12` de Pydantic.
- **Vérification :** un test avec `"12345678901.00"` : Pydantic l'accepte (il retire les zéros de fin avant de compter les chiffres), puis PostgreSQL le refuse (`numeric field overflow`) et l'API répond **500**.
- **Modifié :** remplacement par une **borne explicite** (valeur absolue inférieure à 10¹⁰), accompagnée de tests aux limites (`9999999999.99` accepté, `10000000000` refusé).
- **Décision finale et pourquoi :** la validation doit refuser avant la base ; une 500 sur une saisie utilisateur est un défaut de contrat. C'est un test, et non la lecture du code, qui a révélé le défaut.

## Une erreur 500 qui aurait exposé un détail de base — relecture de la PR #31

- **Problème :** le format d'erreur unique devait renvoyer des messages utiles sans détail technique.
- **Rôle utilisé :** Full-Stack Development ; relecture humaine par Thomas.
- **Proposition de l'agent :** une classe `ErreurApi` utilisable avec n'importe quel statut, y compris 500, avec un message transmis tel quel au client.
- **Vérification :** Thomas a relevé qu'un `ErreurApi(500, détail SQL)` ferait fuiter le détail. Sept tests passent au rouge lorsque la correction est retirée.
- **Accepté :** `ErreurApi` est **réservée aux erreurs 4xx** ; toute 500 passe par le gestionnaire générique, qui répond un message fixe, sans trace ni SQL.
- **Décision finale et pourquoi :** le message d'une erreur 4xx est écrit par nous ; celui d'une 500 ne doit jamais venir du serveur. Exemple d'une proposition de l'agent corrigée par la relecture d'un autre membre.

## Test instable : mesurer avant de corriger — issue #53, PR #54

- **Problème :** environ 1 passage sur 40, une 401 immédiatement après une connexion réussie.
- **Rôle utilisé :** Full-Stack Development (investigation) et QA & Security.
- **Délégué :** trouver la cause d'un échec intermittent sans relancer jusqu'à ce que ça passe.
- **Démarche :** sonde de 150 puis 120 connexions, capture de l'exception exacte (`ImmatureSignatureError`), mesure de l'horloge du conteneur, puis hypothèse écartée en vérifiant qu'un `encode` suivi d'un `decode` répété 20 000 fois ne produit aucun échec.
- **Cause trouvée :** l'horloge du conteneur (WSL2 / Docker) **recule d'environ 1,3 s** ; l'`iat` du jeton paraît alors dans le futur et un jeton valide est refusé.
- **Accepté :** une marge `leeway=10` secondes à la vérification du JWT. 0 échec sur 360 connexions, 10 tests, dont des cas de sécurité (un jeton à 40 s d'avance ou expiré reste refusé).
- **Décision finale et pourquoi :** la marge est le compromis standard de PyJWT, bornée par des tests, négligeable devant une durée de 30 minutes. Correctif séparé, car il touche le fichier d'un autre membre.

## Revue QA & Security de la PR #57 — corrections issues de la revue (Task 4)

- **Problème :** la PR #57 finalisait la documentation OpenAPI et les documents `docs/`. Il fallait savoir si elle disait vrai et si le code avait des défauts de sécurité ou de fiabilité.
- **Rôle utilisé :** les agents **QA & Security** de deux autres membres de l'équipe (Thomas et Benjamin), avec un prompt commun : lecture seule, aucune commande destructive, pas de modification de la base de développement, **preuve exigée pour chaque constat**.
- **Propositions des agents :** deux rapports de sept constats chacun (validation des montants, secret JWT d'exemple, erreur 500 sur les gros budgets, limiteur de connexion, exemples d'erreur de l'OpenAPI, 422 oubliée, durée du JWT, prérequis).
- **Vérification :** chaque constat a été **reproduit par exécution** avant décision (montants `1e2`, `+5`, `1_000` acceptés ; jeton forgé avec le secret public accepté ; liste des budgets en 500 permanente ; blocage du limiteur simulé).

  | Constat | Décision |
  |---|---|
  | Le motif des montants publié n'est pas celui de la validation | **Modifié** : la validation est resserrée au contrat (au lieu d'élargir la documentation). La gravité « bloquant » est jugée **exagérée** : aucune valeur stockée n'était fausse |
  | `JWT_SECRET` d'exemple accepté en production | **Accepté** : documentation corrigée dans la PR, garde-fou dans le code en issue séparée **#58** (PR #60) |
  | 500 quand la consommation d'un budget dépasse 9 999 999 999,99 | **Accepté** : défaut antérieur à la PR, corrigé en issue **#59** (PR #61) |
  | Blocage du limiteur « de quelques minutes » | **Accepté** : simulé (prolongeable en espaçant les essais), limites documentées |
  | Exemples d'erreur faux dans l'OpenAPI | **Accepté** : corrigés ; un test provoque 27 vraies erreurs et compare message, code et champs |

- **Corrigé par l'équipe :** une hypothèse écrite dans l'issue #59 (« le tableau de bord tient ces montants ») était **fausse** : `centimes()` côté front n'acceptait que 10 chiffres. Un test de composant l'a démontré ; l'issue a été rectifiée et le correctif front est inclus dans la PR #61.
- **Résultat :** 489 tests à la fin de la PR #57, puis 535 tests back et 92 tests front avec #58 et #59 ; chaque correction a un test qui échoue sans elle (mutations vérifiées).
- **Décision finale et pourquoi :** une réponse d'agent n'est pas une preuve. Les agents ont trouvé de vrais défauts (dont un que l'auteur n'avait pas vu), mais chaque constat a été reproduit, sa gravité ajustée, et chaque correction transformée en test pour ne pas revenir.
