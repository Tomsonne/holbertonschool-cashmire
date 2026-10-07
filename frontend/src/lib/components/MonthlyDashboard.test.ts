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
