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

export type ErreurApi = Error & {
  status?: number;
  champs?: Record<string, string>;
};

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
