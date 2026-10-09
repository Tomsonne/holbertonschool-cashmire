# Accessibilité, responsive et éco-conception

Ce document dit ce qui est en place dans le MVP, comment cela a été vérifié et ce qui reste à faire. Il ne prétend pas à une conformité WCAG complète : aucune validation par un outil d'audit ni par un lecteur d'écran n'a été faite.

## Accessibilité

### Ce qui est en place dans le code
| Pratique | Constat |
|---|---|
| **Langue de la page** | `<html lang="fr">` |
| **Structure** | Une navigation `<nav aria-label="Pages disponibles">` et des titres hiérarchisés. Les écrans d'accès (connexion, inscription), l'aperçu technique et la page introuvable ont un `<main>` ; **les pages privées connectées (Budgets, Dépenses, Synthèse) n'en ont pas** (voir les limites) |
| **Formulaires** | Chaque champ a un `<label>` ; types adaptés (`email`, `password`, `month`) ; limites de longueur du mot de passe exprimées par `minlength` et `maxlength` |
| **Messages d'erreur et d'état** | Erreurs affichées près du champ, avec des attributs `aria-*` (`aria-invalid`, rôles `status` ou `alert` pour les retours) ; la saisie est conservée après une erreur |
| **Focus visible** | Contour de 3 px sur `:focus-visible` pour les boutons et champs, défini dans la navigation, l'écran d'accès et la synthèse |
| **Images décoratives** | Les illustrations et icônes de catégories ont un `alt` vide : le sens passe par le texte (nom de la catégorie, statut) |
| **Information non portée par la seule couleur** | Le statut d'un budget est écrit (« Dans le budget », « Attention », « Dépassé »), en plus de la couleur et de la barre de progression |
| **États vides et zéros** | Messages explicatifs (« Aucun budget pour ce mois. », « Aucune dépense ni budget pour ce mois. Ajoutez vos premières données depuis les pages dédiées. ») ; un budget dépassé est expliqué (« 5,00 € au-dessus de la limite »), il n'est pas présenté comme une erreur technique |
| **Retours après action** | Messages de succès (« Budget modifié. »), de chargement et d'échec |

### Responsive
- Balise `viewport` présente ; mise en page adaptée par seuils de largeur (1100 px et 767 px), avec passage en colonne sur smartphone.
- Interface pensée mobile-first.

### Vérifications effectuées
Voir `docs/recette.md`, section 6 : navigation au clavier, largeur de smartphone simulée (~375 px) dans les outils de développement, message d'erreur associé au champ, lisibilité du texte et des badges.

### Ce qui reste à faire (limites assumées)
- **Repère `<main>` des pages privées :** Budgets, Dépenses et Synthèse sont composées de sections sans élément `<main>` englobant ; un utilisateur de lecteur d'écran n'a donc pas de repère « contenu principal » sur ces pages. Correction prévue dans une PR de code séparée.
- **Contrastes** : lus à l'œil, **non mesurés** avec un outil ; le texte est posé sur un fond illustré, ce qui mérite un contrôle chiffré (rapport de contraste WCAG AA).
- **Lecteur d'écran** : non testé (ni NVDA, ni VoiceOver).
- **Mouvement réduit** : aucune règle `prefers-reduced-motion`.
- **Appareils réels** : la vérification mobile est simulée.
- **Audit automatisé** (Lighthouse, axe) non exécuté.

## Éco-conception

### Ce qui est en place
| Pratique | Constat |
|---|---|
| **Peu de code côté navigateur** | Svelte compile les composants : la construction du frontend donne environ **107 Ko de JavaScript (36 Ko compressés) et 25 Ko de CSS** |
| **Aucune bibliothèque d'interface ni de graphiques tierce** | Les dépendances du frontend se limitent à Svelte, Vite et au plugin Svelte |
| **Icônes de catégories légères** | Six icônes en **WebP**, de 15 à 25 Ko chacune (environ 110 Ko au total), remplaçant d'anciens PNG de plusieurs mégaoctets |
| **Pagination** | Les dépenses sont servies par pages de 10 : l'API ne renvoie pas toute la liste |
| **Calcul du consommé à la demande** | Pas de donnée dérivée stockée ni de tâche de fond |
| **Pas de suivi** | Aucun traceur, aucune mesure d'audience, aucun service tiers de données |

### Ce qui reste à faire (limites assumées)
| Point | Constat | Amélioration prévue |
|---|---|---|
| **Illustrations lourdes** | Trois images PNG restent à environ 2 Mo chacune (`hero-village.png`, `logo-emblem.png`, `woodland-frame.png`) : le dossier d'images pèse **environ 6,6 Mo** | Conversion en WebP et redimensionnement |
| **Polices externes** | Trois familles chargées depuis Google Fonts : requêtes tierces, poids supplémentaire, transmission de l'adresse IP | Héberger une ou deux polices en local, et limiter les graisses |
| **Frontend servi par Vite** | La livraison locale utilise le serveur de développement | Pour un déploiement : `npm run build` puis un serveur statique avec compression et cache |
| **Métadonnées** | `index.html` contient le titre, la langue, la couleur de thème et le viewport ; **pas de description** ni de balises de partage | Ajouter une `meta description` et un titre par écran |
| **Synthèse calculée dans le navigateur** | Elle lit toutes les pages de dépenses du mois | Une route d'agrégats côté API pour de gros volumes |

## Pourquoi ces limites sont connues et acceptées
Elles ont été documentées avant l'évaluation plutôt que corrigées à la dernière minute : le MVP fonctionnel est vérifié par des tests (back et front), et les changements d'images, de polices et de métadonnées touchent le code livré. Ils sont listés comme améliorations dans le README.
