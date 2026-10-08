import type { ChargerPage, Depense, PageDepenses } from '../dashboard';
import type { DepenseFormulaire } from '../depenses';
import { requeteApi } from './client';

export const chargerPageDepenses: ChargerPage = (mois, limite, decalage) => {
  const parametres = new URLSearchParams({ mois, limite: String(limite), decalage: String(decalage) });
  return requeteApi<PageDepenses>(`/depenses?${parametres.toString()}`);
};

export type FiltresDepenses = {
  mois: string;
  categorieId: string;
  limite: number;
  decalage: number;
};

export const depensesApi = {
  lister: ({ mois, categorieId, limite, decalage }: FiltresDepenses) => {
    const parametres = new URLSearchParams({ mois, limite: String(limite), decalage: String(decalage) });
    if (categorieId) parametres.set('categorie_id', categorieId);
    return requeteApi<PageDepenses>(`/depenses?${parametres.toString()}`);
  },
  creer: (donnees: DepenseFormulaire) => requeteApi<Depense>('/depenses', 'POST', donnees),
  modifier: (id: string, donnees: Partial<DepenseFormulaire>) =>
    requeteApi<Depense>(`/depenses/${encodeURIComponent(id)}`, 'PATCH', donnees),
  supprimer: (id: string) => requeteApi<void>(`/depenses/${encodeURIComponent(id)}`, 'DELETE'),
};
