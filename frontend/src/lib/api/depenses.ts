import type { ChargerPage, PageDepenses } from '../dashboard';
import { requeteApi } from './client';

export const chargerPageDepenses: ChargerPage = (mois, limite, decalage) => {
  const parametres = new URLSearchParams({ mois, limite: String(limite), decalage: String(decalage) });
  return requeteApi<PageDepenses>(`/depenses?${parametres.toString()}`);
};
