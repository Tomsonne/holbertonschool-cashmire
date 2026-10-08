import type { Categorie } from './budgets';

export type Depense = {
  id: string;
  montant: string;
  libelle: string;
  date_depense: string;
  categorie: Categorie;
};

export type PageDepenses = { elements: Depense[]; total: number };
export type ChargerPage = (mois: string, limite: number, decalage: number) => Promise<PageDepenses>;

export async function toutesLesDepenses(mois: string, chargerPage: ChargerPage): Promise<Depense[]> {
  const depenses: Depense[] = [];
  while (true) {
    const page = await chargerPage(mois, 100, depenses.length);
    if (!Number.isSafeInteger(page.total) || page.total < 0) throw new Error('Pagination invalide');
    if (page.elements.length === 0 && depenses.length < page.total) throw new Error('Pagination incomplète');
    depenses.push(...page.elements);
    if (depenses.length >= page.total) return depenses;
  }
}

export function centimes(montant: string): bigint {
  // Pas de borne sur la taille : une somme calculée par l'API (consommation d'un budget) peut dépasser
  // les 10 chiffres d'un montant saisi.
  const match = /^(-?)(\d+)\.(\d{2})$/.exec(montant);
  if (!match) throw new Error('Montant invalide');
  return (match[1] === '-' ? -1n : 1n) * (BigInt(match[2]) * 100n + BigInt(match[3]));
}

export function montantDepuisCentimes(value: bigint): string {
  const signe = value < 0n ? '-' : '';
  const absolu = value < 0n ? -value : value;
  return `${signe}${absolu / 100n}.${String(absolu % 100n).padStart(2, '0')}`;
}

export function repartir(depenses: Depense[]) {
  const repartition = new Map<string, { categorie: Categorie; total: bigint }>();
  let total = 0n;
  for (const depense of depenses) {
    const valeur = centimes(depense.montant);
    total += valeur;
    const precedente = repartition.get(depense.categorie.id);
    repartition.set(depense.categorie.id, {
      categorie: depense.categorie,
      total: (precedente?.total ?? 0n) + valeur,
    });
  }
  return { total, categories: [...repartition.values()].sort((a, b) => a.categorie.nom.localeCompare(b.categorie.nom, 'fr')) };
}

export function partPourMille(valeur: bigint, total: bigint): number {
  return total === 0n ? 0 : Number(valeur * 1000n / total);
}
