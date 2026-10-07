Tu travailles sur le frontend de Cashmire. Applique la direction artistique validée : **« Les Trois Petits Cochons »**, en suivant la maquette fournie.

L’objectif visuel est une application de finances personnelles chaleureuse, lisible et illustrée comme un livre de contes. Les personnages donnent une identité au produit ; les montants, actions et graphiques restent les éléments les plus faciles à lire.

**Palette commune à tous les écrans**

| Usage | Couleur |
|---|---|
| Fond principal crème | `#FFF8EC` |
| Fond des cartes ivoire | `#FFFCF5` |
| Texte principal et bouton vert | `#2C4939` |
| Vert sauge | `#8FAF79` |
| Jaune paille | `#F1CA72` |
| Rouge brique / corail | `#DF7059` |
| Bleu ciel | `#74BDE8` |
| Bordures brun doux | `#B99B72` |

Centraliser ces couleurs dans des variables de thème communes.

Pour la répartition des dépenses : alimentation en sauge, factures en jaune paille, loisirs en corail et transport en bleu ciel. Les états des budgets utilisent leurs propres badges : vert pour « Dans le budget », ambre pour « Attention », rouge pour « Dépassé ».

**Typographie et composants**

- Titres : police ronde, légèrement manuscrite, avec une apparence de conte illustré. Réserver cette police aux titres et à la marque.
- Textes, boutons, formulaires et tableaux : police sans-serif très lisible.
- Montants : chiffres alignés, suffisamment grands et contrastés.
- Tailles indicatives : texte courant 14–16 px ; titres 28–36 px sur ordinateur et 22–28 px sur mobile.
- Cartes arrondies, rayon de 12–16 px, bordure fine et ombre discrète.
- Espacements communs basés sur 8, 16, 24 et 32 px.
- Bouton principal bien visible ; boutons secondaires ivoire avec bordure.
- Icônes simples, légèrement illustrées, cohérentes entre toutes les pages.

**Illustrations**

Créer ou utiliser des illustrations originales montrant exactement trois cochons sympathiques et leurs maisons : paille, bois et briques. Associer chaque cochon à son matériau : chapeau de paille, tenue de charpentier, tenue de maçon.

L’univers comprend des arbres, feuilles, fleurs, outils et matériaux. Concentrer les grandes illustrations dans la bannière d’accueil. Sur les cartes, privilégier de petites icônes et quelques détails végétaux.

Prévoir des fichiers séparés : bannière sans texte, petit emblème Cashmire, icônes des catégories et éventuels personnages isolés. Construire les textes, boutons, cartes et graphiques avec les composants de l’application.

**Disposition du tableau de bord**

1. En-tête horizontal : logo Cashmire, navigation, sélection du mois et actions principales.
2. Bannière illustrée : titre « Des budgets bien construits. », sous-titre « Chaque dépense trouve sa place. », trois indicateurs et scène des trois maisons.
3. Deux panneaux : courbe des dépenses cumulées à gauche, environ 60 % de la largeur ; camembert avec légende à droite, environ 40 %.
4. Quatre cartes de budgets alignées : catégorie, montant consommé/plafond, pourcentage, progression et badge.
5. Tableau des dernières dépenses sous les budgets.

Les graphiques ont un fond clair, des axes discrets et des légendes lisibles. Utiliser les illustrations autour des panneaux, en laissant les données dégagées.

**Adaptation mobile**

Passer à une colonne : bannière compacte, indicateurs, graphique, budgets puis dépenses. Simplifier la scène illustrée tout en conservant les trois maisons. Adapter les lignes de dépenses en blocs lisibles. Prévoir une navigation inférieure et une action « Ajouter une dépense » facile à atteindre. Les boutons doivent offrir une zone tactile d’au moins 44 px.

**États visuels et cohérence**

Afficher chaque état de budget avec une couleur, une icône et un libellé explicite. Un dépassement conserve son véritable pourcentage et affiche le montant dépassé.

Les formulaires reprennent les mêmes fonds, bordures, arrondis et boutons. Prévoir un focus visible, des erreurs proches des champs, des confirmations discrètes et des états vides avec une petite illustration accompagnée d’une action claire.

Réutiliser les composants et styles communs entre les contributions des différents agents. Toutes les pages doivent donner l’impression d’appartenir à la même application, avec les mêmes couleurs, typographies, espacements et illustrations.