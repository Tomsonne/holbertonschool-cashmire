import type { Budget, Categorie } from '../budgets';
import { requeteApi } from './client';

export type Utilisateur = { id: string; email: string; nom_affichage: string };

export const sessionApi = {
  moi: () => requeteApi<Utilisateur>('/authentification/moi'),
  connecter: (email: string, mot_de_passe: string) => requeteApi<Utilisateur>('/authentification/connexion', 'POST', { email, mot_de_passe }),
  deconnecter: () => requeteApi<void>('/authentification/deconnexion', 'POST'),
};

export const budgetsApi = {
  categories: () => requeteApi<Categorie[]>('/categories'),
  lister: (mois: string) => requeteApi<Budget[]>(`/budgets?mois=${encodeURIComponent(mois)}`),
  creer: (donnees: { categorie_id: string; montant_limite: string; mois: string; seuil_alerte_pct: number }) => requeteApi<Budget>('/budgets', 'POST', donnees),
  modifier: (id: string, donnees: { montant_limite: string; seuil_alerte_pct: number }) => requeteApi<Budget>(`/budgets/${encodeURIComponent(id)}`, 'PATCH', donnees),
  supprimer: (id: string) => requeteApi<void>(`/budgets/${encodeURIComponent(id)}`, 'DELETE'),
};
