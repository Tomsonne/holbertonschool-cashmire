// Écran rendu par App.svelte pour une route.
export type Ecran = 'budgets' | 'synthese' | 'technique';

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
  { chemin: '/budgets', alias: ['/'], libelle: 'Budgets', privee: true, navigation: true, ecran: 'budgets' },
  { chemin: '/etat-technique', alias: [], libelle: 'État technique', privee: false, navigation: false, ecran: 'technique' },
];

// Page qui affiche le formulaire de connexion tant que l'écran dédié (#21) n'existe pas.
export const CHEMIN_CONNEXION = '/budgets';

export function trouverRoute(chemin: string): Route | undefined {
  return routes.find(route => route.chemin === chemin || route.alias.includes(chemin));
}
