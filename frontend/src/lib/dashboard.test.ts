import { describe, expect, it, vi } from 'vitest';
import { centimes, montantDepuisCentimes, repartir, toutesLesDepenses } from './dashboard';
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

describe('sommes à plus de dix chiffres', () => {
  it('lit et reformate les montants calculés par l’API sans les borner', () => {
    expect(centimes('19999999999.98')).toBe(1999999999998n);
    expect(centimes('-19999999899.98')).toBe(-1999999989998n);
    expect(montantDepuisCentimes(centimes('19999999999.98'))).toBe('19999999999.98');
    expect(montantDepuisCentimes(centimes('-19999999899.98'))).toBe('-19999999899.98');
  });

  it('additionne deux dépenses de 9 999 999 999,99 sans perdre un centime', () => {
    const gros = (id: string): Depense => ({
      id, montant: '9999999999.99', libelle: 'Gros achat', date_depense: '2026-10-01', categorie,
    });
    expect(montantDepuisCentimes(repartir([gros('1'), gros('2')]).total)).toBe('19999999999.98');
  });

  it('refuse toujours une chaîne qui n’est pas un montant à deux décimales', () => {
    for (const invalide of ['1e2', '12.5', '12', '+5', '1_000.00', '']) {
      expect(() => centimes(invalide)).toThrow('Montant invalide');
    }
  });
});
