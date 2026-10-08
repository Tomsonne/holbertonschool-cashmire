import { afterEach, expect, it, vi } from 'vitest';
import { cleanup, render, screen } from '@testing-library/svelte';
import MonthlyDashboard from './MonthlyDashboard.svelte';

afterEach(() => { cleanup(); vi.restoreAllMocks(); });

it('affiche les montants et une alerte explicite renvoyée par l’API', async () => {
  render(MonthlyDashboard, {
    loadBudgets: vi.fn().mockResolvedValue([{
      id: 'budget-1', categorie: { id: 'cat-1', nom: 'Alimentation' },
      mois: '2026-10', montant_limite: '10.00', depense: '12.30',
      reste: '-2.30', pourcentage: 123, seuil_alerte_pct: 80, statut: 'depasse',
    }]),
    loadExpensePage: vi.fn().mockResolvedValue({
      elements: [{ id: 'dep-1', montant: '12.30', libelle: 'Courses',
        date_depense: '2026-10-01', categorie: { id: 'cat-1', nom: 'Alimentation' } }],
      total: 1,
    }),
  });
  expect(await screen.findByText('La limite est dépassée.')).toBeInTheDocument();
  expect(screen.getByText(/2,30 € au-dessus de la limite/)).toBeInTheDocument();
  expect(screen.getByText('Répartition des dépenses')).toBeInTheDocument();
});

it('affiche une consommation de plus de dix chiffres sans planter', async () => {
  render(MonthlyDashboard, {
    loadBudgets: vi.fn().mockResolvedValue([{
      id: 'budget-1', categorie: { id: 'cat-1', nom: 'Alimentation' },
      mois: '2026-10', montant_limite: '100.00', depense: '19999999999.98',
      reste: '-19999999899.98', pourcentage: 19999999999.98, seuil_alerte_pct: 80, statut: 'depasse',
    }]),
    loadExpensePage: vi.fn().mockResolvedValue({
      elements: [
        { id: 'dep-1', montant: '9999999999.99', libelle: 'Gros achat',
          date_depense: '2026-10-01', categorie: { id: 'cat-1', nom: 'Alimentation' } },
        { id: 'dep-2', montant: '9999999999.99', libelle: 'Gros achat',
          date_depense: '2026-10-02', categorie: { id: 'cat-1', nom: 'Alimentation' } },
      ],
      total: 2,
    }),
  });
  expect(await screen.findByText('La limite est dépassée.')).toBeInTheDocument();
  expect(screen.getByText(/19999999899,98 € au-dessus de la limite/)).toBeInTheDocument();
});
