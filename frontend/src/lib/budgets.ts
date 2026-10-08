import type { ErreurApi } from './api/erreurs';

export type Categorie = { id: string; nom: string };

export type Budget = {
  id: string;
  categorie: Categorie;
  mois: string;
  montant_limite: string;
  depense: string;
  reste: string;
  pourcentage: number;
  seuil_alerte_pct: number;
  statut: 'ok' | 'attention' | 'depasse';
};

export type { ErreurApi };

export function messageErreur(error: unknown): string {
  const apiError = error as ErreurApi;
  if (apiError?.status === 401) return 'Votre session a expiré. Reconnectez-vous.';
  if (apiError?.status === 409) return 'Un budget existe déjà pour cette catégorie et ce mois.';
  if (apiError?.status === 422) return 'Vérifiez les données du formulaire.';
  return 'Impossible de joindre le service. Réessayez.';
}

export function montantLisible(value: string): string {
  return `${value.replace('.', ',')} €`;
}

export function iconeCategorie(nom: string): string | null {
  const cle = nom.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
  if (['alimentation', 'factures', 'loisirs', 'transport'].includes(cle)) {
    return `/assets/cashmire/icon-${cle}.png`;
  }
  return null;
}
