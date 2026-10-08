export type DepenseFormulaire = {
  montant: string;
  libelle: string;
  date_depense: string;
  categorie_id: string;
};

export type ErreursFormulaire = Partial<Record<keyof DepenseFormulaire, string>>;

// Transforme "12,5" en "12.50". Renvoie null si la saisie est invalide ou nulle.
export function normaliserMontant(saisie: string): string | null {
  const nettoye = saisie.trim().replace(',', '.');
  if (!/^\d{1,10}(\.\d{1,2})?$/.test(nettoye)) return null;
  const [entier, decimales = ''] = nettoye.split('.');
  const montant = `${entier}.${decimales.padEnd(2, '0')}`;
  return /^0+\.00$/.test(montant) ? null : montant;
}

// Date locale au format AAAA-MM-JJ (celui de <input type="date">).
export function dateIso(date: Date): string {
  const mois = String(date.getMonth() + 1).padStart(2, '0');
  const jour = String(date.getDate()).padStart(2, '0');
  return `${date.getFullYear()}-${mois}-${jour}`;
}

export function validerFormulaire(formulaire: DepenseFormulaire): ErreursFormulaire {
  const erreurs: ErreursFormulaire = {};
  if (normaliserMontant(formulaire.montant) === null) {
    erreurs.montant = 'Saisissez un montant supérieur à 0, avec 2 décimales au plus.';
  }
  const libelle = formulaire.libelle.trim();
  if (libelle.length === 0 || libelle.length > 200) {
    erreurs.libelle = 'Le libellé doit contenir entre 1 et 200 caractères.';
  }
  const demain = new Date();
  demain.setDate(demain.getDate() + 1);
  if (!formulaire.date_depense) {
    erreurs.date_depense = 'Choisissez une date.';
  } else if (formulaire.date_depense < '2000-01-01' || formulaire.date_depense > dateIso(demain)) {
    erreurs.date_depense = 'La date doit être comprise entre le 01/01/2000 et demain.';
  }
  if (!formulaire.categorie_id) erreurs.categorie_id = 'Choisissez une catégorie.';
  return erreurs;
}

export function messageErreurDepense(erreur: unknown): string {
  const status = (erreur as { status?: number } | null)?.status;
  if (status === 401) return 'Votre session a expiré. Reconnectez-vous.';
  if (status === 404) return 'Cette dépense n’existe plus. Actualisez la liste.';
  if (status === 422) return 'Vérifiez les données du formulaire.';
  return 'Impossible de joindre le service. Réessayez.';
}

export function dateLisible(date: string): string {
  const [annee, mois, jour] = date.split('-');
  return `${jour}/${mois}/${annee}`;
}
