// Écran rendu par App.svelte pour une route.
export type Ecran = 'budgets' | 'depenses' | 'synthese' | 'technique' | 'connexion' | 'inscription';

export type Route = {
  chemin: string;
  alias: string[];
  libelle: string;
  privee: boolean;
  navigation: boolean;
  ecran: Ecran;
};

// Une ligne par page. L'ordre fixe celui des liens de navigation.
export const routes: Route[] = [
  { chemin: '/synthese', alias: ['/dashboard'], libelle: 'Synthèse', privee: true, navigation: true, ecran: 'synthese' },
  { chemin: '/depenses', alias: [], libelle: 'Dépenses', privee: true, navigation: true, ecran: 'depenses' },
  { chemin: '/budgets', alias: ['/'], libelle: 'Budgets', privee: true, navigation: true, ecran: 'budgets' },
  { chemin: '/etat-technique', alias: [], libelle: 'État technique', privee: false, navigation: false, ecran: 'technique' },
  { chemin: '/connexion', alias: [], libelle: 'Connexion', privee: false, navigation: false, ecran: 'connexion' },
  { chemin: '/inscription', alias: [], libelle: 'Créer un compte', privee: false, navigation: false, ecran: 'inscription' },
];

// Pages publiques d'accès au compte, liées depuis la navigation d'un visiteur.
export const CHEMIN_CONNEXION = '/connexion';
export const CHEMIN_INSCRIPTION = '/inscription';

export function trouverRoute(chemin: string): Route | undefined {
  return routes.find(route => route.chemin === chemin || route.alias.includes(chemin));
}
