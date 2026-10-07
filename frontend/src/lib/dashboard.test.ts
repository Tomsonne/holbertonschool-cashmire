import { describe, expect, it, vi } from 'vitest';
import { montantDepuisCentimes, repartir, toutesLesDepenses } from './dashboard';
import type { Depense } from './dashboard';

const categorie = { id: 'cat-1', nom: 'Alimentation' };

describe('agrégation du tableau de bord', () => {
  it('parcourt les 101 dépenses et additionne les centimes exactement', async () => {
    const depenses: Depense[] = Array.from({ length: 101 }, (_, index) => ({
      id: String(index), montant: '0.10', libelle: 'Achat',
      date_depense: '2026-10-01', categorie,
    }));
    const chargerPage = vi.fn(async (_mois: string, limite: number, decalage: number) => ({
      elements: depenses.slice(decalage, decalage + limite), total: depenses.length,
    }));
    const toutes = await toutesLesDepenses('2026-10', chargerPage);
    expect(chargerPage).toHaveBeenCalledTimes(2);
    expect(chargerPage).toHaveBeenNthCalledWith(2, '2026-10', 100, 100);
    expect(montantDepuisCentimes(repartir(toutes).total)).toBe('10.10');
  });

  it('refuse une pagination interrompue sans afficher un total partiel', async () => {
    await expect(toutesLesDepenses('2026-10', vi.fn().mockResolvedValue({
      elements: [], total: 2,
    }))).rejects.toThrow('Pagination incomplète');
  });
});
