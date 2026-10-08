import { afterEach, describe, expect, it, vi } from 'vitest';
import type { ComponentProps } from 'svelte';
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/svelte';
import DepensesManager from './DepensesManager.svelte';

afterEach(() => { cleanup(); vi.restoreAllMocks(); });

const categories = [{ id: 'cat-1', nom: 'Alimentation' }];
const depense = {
  id: 'dep-1', montant: '12.50', libelle: 'Courses', date_depense: '2026-10-08', categorie: categories[0],
};

function monter(surcharges: Partial<ComponentProps<typeof DepensesManager>> = {}) {
  const props = {
    categories,
    loadDepenses: vi.fn().mockResolvedValue({ elements: [depense], total: 1 }),
    createDepense: vi.fn().mockResolvedValue(depense),
    updateDepense: vi.fn().mockResolvedValue(depense),
    deleteDepense: vi.fn().mockResolvedValue(undefined),
    ...surcharges,
  };
  render(DepensesManager, props);
  return props;
}

describe('Gestion des dépenses', () => {
  it('affiche la liste avec montant et date lisibles', async () => {
    const { loadDepenses } = monter();
    expect(await screen.findByText('Courses')).toBeInTheDocument();
    expect(screen.getByText('12,50 €')).toBeInTheDocument();
    expect(screen.getByText('Alimentation · 08/10/2026')).toBeInTheDocument();
    expect(loadDepenses).toHaveBeenCalledWith(expect.objectContaining({ categorieId: '', limite: 10, decalage: 0 }));
  });

  it('explique quoi faire quand il n’y a aucune dépense', async () => {
    monter({ loadDepenses: vi.fn().mockResolvedValue({ elements: [], total: 0 }) });
    expect(await screen.findByText(/Aucune dépense pour ces critères/)).toBeInTheDocument();
  });

  it('affiche une erreur de chargement sans prétendre que la liste est vide', async () => {
    monter({ loadDepenses: vi.fn().mockRejectedValue({ status: 401 }) });
    expect(await screen.findByRole('alert')).toHaveTextContent('Votre session a expiré');
    expect(screen.queryByText(/Aucune dépense/)).toBeNull();
  });

  it('demande confirmation avant de supprimer puis recharge la liste', async () => {
    const { deleteDepense, loadDepenses } = monter();
    await fireEvent.click(await screen.findByRole('button', { name: 'Supprimer Courses' }));
    expect(deleteDepense).not.toHaveBeenCalled();
    await fireEvent.click(screen.getByRole('button', { name: 'Confirmer la suppression' }));
    await waitFor(() => expect(deleteDepense).toHaveBeenCalledWith('dep-1'));
    expect(await screen.findByText('Dépense supprimée.')).toBeInTheDocument();
    expect(loadDepenses).toHaveBeenCalledTimes(2);
  });

  it('crée une dépense avec un montant normalisé et actualise la liste', async () => {
    const { createDepense, loadDepenses } = monter();
    await screen.findByText('Courses');
    const ajout = within(screen.getByRole('region', { name: 'Ajouter une dépense' }));
    await fireEvent.input(ajout.getByLabelText('Libellé'), { target: { value: 'Cinéma' } });
    await fireEvent.input(ajout.getByLabelText('Montant (€)'), { target: { value: '8,5' } });
    await fireEvent.change(ajout.getByLabelText('Catégorie'), { target: { value: 'cat-1' } });
    await fireEvent.click(ajout.getByRole('button', { name: 'Ajouter la dépense' }));
    await waitFor(() => expect(createDepense).toHaveBeenCalledWith(expect.objectContaining({
      montant: '8.50', libelle: 'Cinéma', categorie_id: 'cat-1',
    })));
    expect(await screen.findByText('Dépense ajoutée.')).toBeInTheDocument();
    expect(loadDepenses).toHaveBeenCalledTimes(2);
  });

  it('pagine et filtre par catégorie en repartant de la première page', async () => {
    const { loadDepenses } = monter({ loadDepenses: vi.fn().mockResolvedValue({ elements: [depense], total: 25 }) });
    expect(await screen.findByText('Page 1 sur 3')).toBeInTheDocument();
    await fireEvent.click(screen.getByRole('button', { name: 'Suivant' }));
    await waitFor(() => expect(loadDepenses).toHaveBeenLastCalledWith(expect.objectContaining({ decalage: 10 })));
    expect(await screen.findByText('Page 2 sur 3')).toBeInTheDocument();
    await fireEvent.change(screen.getByDisplayValue('Toutes'), { target: { value: 'cat-1' } });
    await waitFor(() => expect(loadDepenses).toHaveBeenLastCalledWith(
      expect.objectContaining({ categorieId: 'cat-1', decalage: 0 }),
    ));
  });
});
