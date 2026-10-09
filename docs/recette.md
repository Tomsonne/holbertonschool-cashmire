# Plan de recette

Ce document décrit comment vérifier que le MVP Cashmire fonctionne de bout en bout, et consigne les résultats de l'exécution. Il complète les tests automatisés : ils prouvent chaque règle isolément, la recette vérifie le **parcours réel dans le navigateur**.

## Environnement

- Démarrage : `docker compose up -d --build` (voir le README), frontend sur `http://localhost:5173`, API sur `http://localhost:8000`.
- Ouvrir le frontend sur **`localhost`** et non sur `127.0.0.1` : seule l'origine `http://localhost:5173` est autorisée pour les écritures.
- Deux comptes sont nécessaires pour les tests d'isolation (le second dans une fenêtre de navigation privée).
- Navigateur : Chrome sur Windows (WSL2 pour Docker). Les autres navigateurs ne sont pas testés.
- Version testée : `main` après la fusion des PR #57 à #62 ; exécution du 9 octobre 2026.

**Exécution :** les scénarios sans constat chiffré ont été joués en démonstration d'équipe, dans le navigateur, avec deux comptes ; les constats chiffrés (montants, pourcentages) viennent de l'exécution du 9 octobre 2026. Les scénarios de la section 7 ont été exécutés avec l'aide d'un agent.
La colonne « Tests automatiques » indique le fichier qui couvre la même règle ; elle ne remplace pas l'exécution manuelle.

## 1. Authentification

| # | Scénario | Résultat attendu | Tests automatiques | Résultat |
|---|---|---|---|---|
| A1 | Créer un compte (email, mot de passe, nom) | Compte créé ; message invitant à se connecter (l'inscription ne connecte pas) | `test_inscription.py`, `Inscription.test.ts` | ✅ |
| A2 | Créer un compte avec un email déjà utilisé | Message clair, sans détail technique | `test_inscription.py` | ✅ |
| A3 | Créer un compte avec un mot de passe trop court | Message par champ, rien n'est créé | `test_inscription.py` (bornes du mot de passe) | ✅ |
| A4 | Se connecter avec les bons identifiants | Nom affiché dans la navigation, accès aux pages privées | `test_connexion.py`, `Connexion.test.ts` | ✅ |
| A5 | Se connecter avec un mauvais mot de passe, puis avec un email inconnu | **Même** message dans les deux cas (pas d'énumération des comptes) | `test_connexion.py` | ✅ |
| A6 | Ouvrir une page privée (`/depenses`) sans être connecté | Formulaire de connexion affiché à la place de la page, sans changer d'URL ; données privées masquées | `test_isolation.py` (401 sur toute route privée), `App.test.ts` | ✅ |
| A7 | Se déconnecter, puis utiliser le bouton « retour » du navigateur | Formulaire de connexion affiché, pages privées inaccessibles (aucune donnée n'est affichée) | `test_deconnexion.py` | ✅ |
| A8 | Recharger la page (F5) en étant connecté | La session est conservée | `session.test.ts` | ✅ |

## 2. Dépenses

| # | Scénario | Résultat attendu | Tests automatiques | Résultat |
|---|---|---|---|---|
| D1 | Créer une dépense (date, montant, libellé, catégorie) | Elle apparaît dans la liste, montant à deux décimales | `test_depenses.py`, `DepenseForm.test.ts` | ✅ |
| D2 | Montant `0`, négatif ou à trois décimales ; libellé vide | Message précis sous le champ, rien n'est créé | `test_depenses.py`, `test_montant.py` | ✅ |
| D3 | Date dans deux jours ou plus (demain est toléré) | Refus avec un message compréhensible | `test_depenses_modification.py` | ✅ |
| D4 | Modifier une dépense | Liste et totaux mis à jour | `test_depenses_modification.py` | ✅ |
| D5 | Supprimer une dépense | Elle disparaît, les totaux sont mis à jour | `test_depenses_modification.py` | ✅ |
| D6 | Parcourir plusieurs pages et filtrer par mois | Pagination et total cohérents | `test_depenses_consultation.py`, `DepensesManager.test.ts` | ✅ |
| D7 | Libellé contenant `<b>test</b>` | Affiché tel quel, jamais interprété (XSS) : Svelte échappe le texte et le code n'utilise aucun `{@html}` | aucun test dédié (contrôle par lecture du code) | ✅ |

## 3. Budgets et alertes

| # | Scénario | Résultat attendu | Tests automatiques | Résultat |
|---|---|---|---|---|
| B1 | Créer un budget mensuel pour une catégorie | Budget affiché avec dépensé, reste et pourcentage | `test_budgets.py`, `BudgetManager.test.ts` | ✅ |
| B2 | Modifier la limite d'un budget | Message « Budget modifié. » et valeurs recalculées | `test_budgets.py` | ✅ |
| B3 | Dépasser la limite d'un budget | Statut « Dépassé », reste négatif exprimé comme « au-dessus de la limite », message clair. Constaté : 20,00 € sur 15,00 €, 133,33 % consommé, 5,00 € dépassés | `test_budgets.py`, `MonthlyDashboard.test.ts` | ✅ |
| B4 | Atteindre le seuil d'alerte (80 % par défaut) | Statut « Attention » et texte expliquant l'alerte | `test_budgets.py` | ✅ |
| B5 | Dépenser exactement la limite (100 %) | « Attention » (limite atteinte, pas franchie), distinct de « Dépassé » | `test_budgets.py` | ✅ |
| B6 | Créer un second budget pour la même catégorie et le même mois | L'interface retire la catégorie de la liste. Si la liste est obsolète (second onglet), message « Un budget existe déjà pour cette catégorie et ce mois. » | `test_budgets.py` (409), `BudgetManager.test.ts` | ✅ |
| B7 | Modifier ou supprimer une dépense liée à un budget | La consommation du budget suit | `test_budgets.py` | ✅ |
| B8 | Supprimer un budget | Il disparaît, les dépenses sont conservées | `test_budgets.py`, `test_budgets_gros_montants.py` | ✅ |
| B9 | Consommation supérieure à 10 chiffres (deux dépenses de `9999999999.99`) | Budget et synthèse s'affichent, sans erreur | `test_budgets_gros_montants.py`, `dashboard.test.ts` | ✅ |

## 4. Synthèse mensuelle et états vides

| # | Scénario | Résultat attendu | Tests automatiques | Résultat |
|---|---|---|---|---|
| S1 | Ouvrir la synthèse d'un compte avec des dépenses et des budgets | Dépensé, plafonds, marge, répartition par catégorie, dernières dépenses cohérents avec les dépenses saisies. Constaté : 107,00 € dépensés, 115,00 € de plafonds | `dashboard.test.ts`, `MonthlyDashboard.test.ts` | ✅ |
| S2 | Ouvrir la synthèse d'un compte vide | « Aucune dépense ni budget pour ce mois. Ajoutez vos premières données depuis les pages dédiées. », zéros affichés sans erreur | `MonthlyDashboard.test.ts` | ✅ |
| S3 | Changer de mois | Les données du mois choisi s'affichent | `MonthlyDashboard.test.ts` | ✅ |

## 5. Sécurité et isolation

| # | Scénario | Résultat attendu | Tests automatiques | Résultat |
|---|---|---|---|---|
| I1 | Se connecter avec un second compte dans une fenêtre privée | Aucune dépense ni aucun budget du premier compte | `test_isolation.py` | ✅ |
| I2 | Accéder à la dépense ou au budget d'un autre compte par son identifiant (API) | `404`, identique à une ressource inexistante, base inchangée | `test_isolation.py` | ✅ |
| I3 | Écriture depuis une origine non autorisée | `403` | `test_origine.py` | ✅ |
| I4 | Cookie falsifié ou expiré | `401` ; formulaire de connexion affiché, données privées masquées | `test_isolation.py` (cookie falsifié), `test_jwt_horloge.py` (jeton expiré), `session.test.ts` | ✅ |
| I5 | Démarrage en production avec le secret d'exemple | L'application refuse de démarrer, message sans recopier le secret | `test_secret_jwt.py` | ✅ (voir section 7) |

## 6. Accessibilité et responsive

| # | Scénario | Résultat attendu | Résultat |
|---|---|---|---|
| X1 | Parcourir les pages au clavier seul (Tab, Maj+Tab, Entrée) | Tous les champs et boutons sont atteignables, le focus est visible | ✅ |
| X2 | Afficher l'application en largeur de smartphone (~375 px, outils de développement) | Pas de défilement horizontal, formulaires utilisables | ✅ |
| X3 | Provoquer une erreur de formulaire | Le message est associé au champ (label, `aria-*`) et annoncé | ✅ |
| X4 | Vérifier le contraste du texte et des badges de statut | Texte lisible sur le fond illustré | ✅ |

## 7. Vérifications complémentaires : démarrage de type production

Exécutées avec l'aide d'un agent, dans un projet Docker isolé (ports et base dédiés, supprimés ensuite), avec `ENVIRONMENT=production` et de vrais secrets aléatoires.

| Vérification | Résultat |
|---|---|
| Démarrage à froid : base, migrations, API, frontend | ✅ tous les services sains |
| `GET /api/health` | ✅ `{"statut":"ok","base_de_donnees":"disponible"}` |
| Cookie en production | ✅ `HttpOnly; Secure; SameSite=lax; Max-Age=1800` |
| Écriture depuis l'origine autorisée / non autorisée | ✅ `201` / `403` |
| Inscription, connexion, dépense, budget par l'API | ✅ `201`, `200`, `201`, `201` |
| Sauvegarde (`pg_dump`) puis restauration dans une base vierge | ✅ 1 utilisateur, 1 dépense, 1 budget, 6 catégories conservés |
| Retour arrière : `alembic downgrade base` puis `upgrade head`, sur une **copie jetable** de la base (le retour à `base` supprime toutes les tables et leurs données ; `upgrade head` recrée le schéma, pas les données) | ✅ |
| Données conservées après arrêt et relance (sans suppression du volume) | ✅ |
| Secret d'exemple avec `ENVIRONMENT=production` | ✅ refus de démarrer |
| Utilisateur du conteneur de l'API | ✅ non root |

## 8. Anomalies et remarques

Aucune anomalie bloquante constatée pendant l'exécution.

- **Remarque (non bloquante) : « Marge restante ».** Sur la synthèse, ce chiffre est la somme du reste de chaque **budget** ; les dépenses sans budget comptent dans « Dépensé » mais pas dans la marge. Plafonds − Dépensé n'est donc pas égal à la marge. À clarifier par un libellé ou une phrase d'aide.
- **Remarque : doublon de budget.** L'interface retire du formulaire les catégories qui ont déjà un budget ce mois-ci ; le serveur refuse quand même le doublon (`409`) si la liste est obsolète. Les deux niveaux sont volontaires.

## 9. Ce qui n'est pas couvert

Lecteur d'écran, navigateurs autres que Chrome, charge, accès simultanés, appareils mobiles réels (la largeur d'écran est simulée). Voir « Limites connues » dans le README.
