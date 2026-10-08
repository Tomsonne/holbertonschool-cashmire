import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/svelte';
import DepenseForm from './DepenseForm.svelte';
import { dateIso } from '../depenses';

afterEach(() => { cleanup(); vi.restoreAllMocks(); });

const categories = [{ id: 'cat-1', nom: 'Alimentation' }];

async function remplir(libelle: string, montant: string) {
  await fireEvent.input(screen.getByLabelText('Libellé'), { target: { value: libelle } });
  await fireEvent.input(screen.getByLabelText('Montant (€)'), { target: { value: montant } });
  await fireEvent.change(screen.getByLabelText('Catégorie'), { target: { value: 'cat-1' } });
}

describe('Formulaire de dépense', () => {
  it('refuse une saisie invalide sans appeler l’API', async () => {
    const enregistrer = vi.fn();
    render(DepenseForm, { categories, enregistrer });
    await fireEvent.click(screen.getByRole('button', { name: 'Ajouter la dépense' }));
    expect(enregistrer).not.toHaveBeenCalled();
    expect(screen.getByText('Choisissez une catégorie.')).toBeInTheDocument();
    expect(screen.getByLabelText('Montant (€)')).toHaveAttribute('aria-invalid', 'true');
  });

  it('envoie le montant normalisé et le libellé nettoyé', async () => {
    const enregistrer = vi.fn().mockResolvedValue(undefined);
    render(DepenseForm, { categories, enregistrer });
    await remplir('  Courses  ', '12,5');
    await fireEvent.click(screen.getByRole('button', { name: 'Ajouter la dépense' }));
    await waitFor(() => expect(enregistrer).toHaveBeenCalledWith({
      montant: '12.50', libelle: 'Courses', date_depense: dateIso(new Date()), categorie_id: 'cat-1',
    }));
  });

  it('affiche l’erreur de l’API et conserve la saisie', async () => {
    const enregistrer = vi.fn().mockRejectedValue({ status: 401 });
    render(DepenseForm, { categories, enregistrer });
    await remplir('Courses', '12,50');
    await fireEvent.click(screen.getByRole('button', { name: 'Ajouter la dépense' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Votre session a expiré');
    expect(screen.getByLabelText('Libellé')).toHaveValue('Courses');
  });
});
