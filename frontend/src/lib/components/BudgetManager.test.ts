import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/svelte';
import BudgetManager from './BudgetManager.svelte';
import type { Budget } from '../budgets';

afterEach(() => { cleanup(); vi.restoreAllMocks(); });

const categorie = { id: 'cat-1', nom: 'Alimentation' };
const budget: Budget = {
  id: 'budget-1', categorie, mois: '2026-10', montant_limite: '100.00',
  depense: '105.25', reste: '-5.25', pourcentage: 105.25,
  seuil_alerte_pct: 80, statut: 'depasse',
};

describe('Gestion des budgets', () => {
  it('annonce la consommation renvoyée par l’API et confirme avant suppression', async () => {
    const loadBudgets = vi.fn().mockResolvedValue([budget]);
    const deleteBudget = vi.fn().mockResolvedValue(undefined);
    render(BudgetManager, {
      categories: [categorie], loadBudgets, deleteBudget,
      createBudget: vi.fn(), updateBudget: vi.fn(),
    });
    expect(await screen.findByText('105,25 €')).toBeInTheDocument();
    expect(screen.getByText('Dépassé')).toBeInTheDocument();
    expect(screen.getByText(/5,25 € dépassés/)).toBeInTheDocument();
    await fireEvent.click(screen.getByRole('button', { name: 'Supprimer' }));
    expect(deleteBudget).not.toHaveBeenCalled();
    await fireEvent.click(screen.getByRole('button', { name: 'Confirmer la suppression' }));
    await waitFor(() => expect(deleteBudget).toHaveBeenCalledWith('budget-1'));
  });

  it('normalise la virgule et explique un doublon 409', async () => {
    const createBudget = vi.fn().mockRejectedValue({ status: 409 });
    render(BudgetManager, {
      categories: [categorie], loadBudgets: vi.fn().mockResolvedValue([]),
      createBudget, updateBudget: vi.fn(), deleteBudget: vi.fn(),
    });
    await screen.findByText(/Aucun budget pour ce mois/);
    await fireEvent.change(screen.getByLabelText('Catégorie'), { target: { value: categorie.id } });
    await fireEvent.input(screen.getByLabelText('Limite mensuelle (€)'), { target: { value: '12,50' } });
    await fireEvent.click(screen.getByRole('button', { name: 'Créer le budget' }));
    await waitFor(() => expect(createBudget).toHaveBeenCalledWith(expect.objectContaining({
      categorie_id: categorie.id, montant_limite: '12.50', seuil_alerte_pct: 80,
    })));
    expect(await screen.findByRole('alert')).toHaveTextContent('Un budget existe déjà');
  });
});
