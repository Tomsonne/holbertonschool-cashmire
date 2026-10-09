# Confidentialité et informations légales

Cashmire est une application **fictive**, réalisée dans un cadre pédagogique. Ce document décrit les données personnelles qu'elle traite, pourquoi, où elles sont stockées et comment elles sont protégées. Ce n'est pas une analyse juridique : il documente les choix du MVP et ses limites, de façon à pouvoir être relu et corrigé avant un usage réel.

## Qui est responsable

L'équipe de développement du projet (voir le dépôt). Aucune donnée n'est vendue, partagée ni utilisée pour de la publicité ou du suivi : l'application n'embarque ni outil de mesure d'audience, ni traceur, ni service tiers de données.

## Quelles données sont stockées et pourquoi

| Donnée | Table | Pourquoi elle est nécessaire |
|---|---|---|
| **Adresse e-mail** | `utilisateurs` | Identifiant de connexion ; unique, sans distinction de casse |
| **Nom d'affichage** (100 caractères au plus) | `utilisateurs` | Saluer l'utilisateur dans la navigation |
| **Mot de passe haché** (Argon2id) | `utilisateurs` | Vérifier l'identité à la connexion ; le mot de passe n'est **jamais** stocké en clair |
| **Date de création du compte** | `utilisateurs` | Information technique du compte |
| **Dépenses** : montant, date, libellé (200 caractères au plus), catégorie, dates de création et de modification | `depenses` | Fonction principale : suivre ses dépenses |
| **Budgets** : catégorie, mois, limite, seuil d'alerte, dates de création et de modification | `budgets` | Calculer la consommation et les alertes |

Les **catégories** (six, communes à tous) ne sont pas des données personnelles. Il n'y a ni numéro de compte bancaire, ni coordonnées de paiement, ni adresse postale, ni date de naissance : les montants sont saisis à la main par l'utilisateur. Les libellés de dépenses étant libres, un utilisateur peut y écrire ce qu'il veut ; ils sont considérés comme sensibles, car ils décrivent son quotidien.

## Où les données sont stockées

- Dans **PostgreSQL**, dans un volume Docker local (`postgres_data`). Le MVP n'est pas déployé : les **données applicatives** (comptes, dépenses, budgets) restent sur la machine qui lance `docker compose up`. Seule exception : le chargement des polices provoque des requêtes du navigateur vers Google (voir « Limites connues »).
- **En mémoire du serveur** : le limiteur de connexion garde, pendant 15 minutes, les **adresses e-mail des tentatives de connexion échouées**, **y compris celles de personnes sans compte**. Ces données ne sont pas écrites en base et sont perdues au redémarrage.
- Dans le navigateur, un seul élément est conservé : le **cookie de session** `access_token`. Le frontend n'utilise ni `localStorage`, ni `sessionStorage`.

## Le cookie de session

Un jeton signé (JWT), valable 30 minutes, transmis dans un cookie `access_token` :
- `HttpOnly` : le JavaScript de la page ne peut pas le lire ;
- `SameSite=Lax` : le cookie n'est **pas envoyé lors des requêtes d'écriture** (`POST`, `PUT`, `PATCH`, `DELETE`) venues d'un autre site ; il l'est lors d'un simple clic sur un lien venant d'un autre site ;
- `Secure` en production : envoyé uniquement en HTTPS ;
- il contient l'identifiant de l'utilisateur (`sub`), la date d'émission (`iat`) et la date d'expiration (`exp`), **pas** son e-mail ni son nom. Un JWT est signé mais pas chiffré : il est lisible, donc il ne porte aucune donnée sensible.

C'est un cookie **strictement nécessaire** au fonctionnement de la connexion : il ne sert à aucun suivi.

## Comment les données sont protégées

| Risque | Mesure |
|---|---|
| Fuite de mots de passe | Argon2id (lent et gourmand en mémoire) ; jamais en clair ; jamais recopiés dans une erreur (`input` jamais renvoyé) |
| Accès aux données d'un autre utilisateur | Chaque lecture, modification et suppression filtre par l'identifiant du propriétaire, pris dans le jeton ; une ressource d'autrui répond `404`, comme une ressource inexistante ; vérifié par `backend/tests/test_isolation.py` |
| Vol de session par script (XSS) | Cookie `HttpOnly` ; Svelte échappe les textes affichés ; aucun `{@html}` sur des données utilisateur |
| Requête forgée depuis un autre site (CSRF) | `SameSite=Lax` et vérification de l'origine (`Origin`, à défaut `Referer`) sur toute écriture |
| Injection SQL | Requêtes paramétrées par SQLAlchemy ; aucune requête construite par concaténation |
| Force brute sur la connexion | Limiteur : 5 échecs en 15 minutes par e-mail |
| Fuite par les messages d'erreur | Format d'erreur unique ; une erreur interne répond un message fixe, sans trace, sans SQL, sans configuration |
| Secrets | Aucun secret dans le dépôt (`.env` ignoré) ; en production, les secrets d'exemple publics sont refusés au démarrage |
| Intégrité des montants | `NUMERIC(12,2)` en base, `Decimal` en Python, jamais de `float` |

## Vos droits et leur état dans le MVP

| Droit | État |
|---|---|
| **Accès** à ses données | ✅ L'utilisateur voit ses dépenses et ses budgets dans l'application |
| **Rectification** | ✅ Modification des dépenses et des budgets ; ❌ pas de modification de l'e-mail, du nom ou du mot de passe dans l'interface (hors périmètre du MVP) |
| **Suppression** | ✅ Suppression des dépenses et des budgets, une à une ; ❌ **pas de suppression de compte** dans l'application. La base est conçue pour la permettre (la suppression d'un utilisateur supprime ses dépenses et ses budgets en cascade), mais aucune route ne l'expose |
| **Portabilité** | ❌ pas d'export des données |

## Limites connues

- **Journaux d'accès :** Uvicorn enregistre par défaut l'**adresse IP** de chaque requête dans ses journaux d'accès : c'est une donnée personnelle, à protéger comme les autres journaux (et à anonymiser ou à désactiver pour une mise en production).
- **Journaux d'erreurs :** en cas d'erreur interne, la trace complète est écrite dans les journaux du serveur. Elle peut contenir, selon l'erreur de la base de données, une valeur saisie (par exemple un e-mail). Les journaux ne sont jamais renvoyés au client ; en contrepartie, ils doivent être protégés comme les données. Une réduction de ce contenu est prévue.
- **Polices Google :** la feuille de style charge les polices depuis `fonts.googleapis.com`. Le navigateur de l'utilisateur contacte donc ce service tiers à chaque chargement, ce qui lui transmet son adresse IP. Une vraie mise en production devra héberger les polices elles-mêmes (voir `docs/accessibilite-eco-conception.md`).
- **Durée de conservation :** aucune suppression automatique n'est prévue ; les données restent tant que le volume existe.
- **Sauvegardes :** pas de procédure automatisée ; la procédure manuelle décrite dans le README produit des sauvegardes **non chiffrées**.
- **Session :** la déconnexion **efface le cookie du navigateur mais n'invalide pas le jeton** : un jeton volé reste valable jusqu'à son expiration (30 minutes), car il n'est pas révocable côté serveur.
- **Limiteur de connexion :** il est en mémoire, donc **propre à chaque processus** : avec plusieurs workers, la limite de 5 échecs est multipliée par le nombre de processus (le MVP en lance un seul).
- **Aucun consentement n'est demandé**, car il n'y a ni traceur ni cookie facultatif. Si une mesure d'audience était ajoutée, il faudrait un bandeau et un choix.

## Informations légales (MVP fictif)

Cashmire est un projet pédagogique : il ne fournit aucun conseil financier, ne se connecte à aucune banque et ne traite aucun paiement. Les montants sont saisis par l'utilisateur ; l'application n'est responsable ni de leur exactitude ni des décisions prises à partir d'eux. Il n'y a pas d'éditeur commercial ni d'hébergeur à nommer : l'application n'est pas publiée.

Les illustrations de l'interface sont celles fournies à l'équipe pour le projet.
