import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/svelte';
import { creerErreurApi } from '../api/erreurs';
import Connexion from './Connexion.svelte';

afterEach(() => { cleanup(); vi.restoreAllMocks(); });

function afficher(connecter = vi.fn().mockResolvedValue(undefined), surSucces = vi.fn(), avertissement?: string) {
  render(Connexion, { connecter, surSucces, titre: 'Accéder à mes budgets', avertissement });
  return { connecter, surSucces };
}

async function remplirEtEnvoyer(email = 'alice@example.test', motDePasse = 'mot-de-passe') {
  await fireEvent.input(screen.getByLabelText('Adresse e-mail'), { target: { value: email } });
  await fireEvent.input(screen.getByLabelText('Mot de passe'), { target: { value: motDePasse } });
  await fireEvent.click(screen.getByRole('button', { name: 'Se connecter' }));
}

describe('Formulaire de connexion', () => {
  it('connecte puis appelle surSucces et vide le mot de passe', async () => {
    const { connecter, surSucces } = afficher();
    expect(screen.getByRole('heading', { name: 'Accéder à mes budgets' })).toBeInTheDocument();
    await remplirEtEnvoyer();
    await waitFor(() => expect(surSucces).toHaveBeenCalledTimes(1));
    expect(connecter).toHaveBeenCalledWith('alice@example.test', 'mot-de-passe');
    expect(screen.getByLabelText('Mot de passe')).toHaveValue('');
    expect(screen.getByLabelText('Adresse e-mail')).toHaveValue('alice@example.test');
  });

  it.each([
    [401, 'identifiants_invalides', 'Identifiants invalides.'],
    [429, 'trop_de_tentatives', 'Trop de tentatives, réessayez plus tard.'],
  ])('garde le formulaire et les saisies après un %i', async (status, code, message) => {
    const { surSucces } = afficher(vi.fn().mockRejectedValue(creerErreurApi(message, status, code)));
    await remplirEtEnvoyer();
    expect(await screen.findByRole('alert')).toHaveTextContent(message);
    expect(screen.getByRole('button', { name: 'Se connecter' })).toBeEnabled();
    expect(screen.getByLabelText('Adresse e-mail')).toHaveValue('alice@example.test');
    expect(screen.getByLabelText('Mot de passe')).toHaveValue('mot-de-passe');
    expect(surSucces).not.toHaveBeenCalled();
    // Sans erreur par champ, le focus va au message général.
    await waitFor(() => expect(screen.getByRole('alert')).toHaveFocus());
  });

  it('affiche les erreurs par champ d’un 422 et place le focus sur le premier champ en erreur', async () => {
    const erreur = creerErreurApi('Données invalides.', 422, 'validation', { mot_de_passe: 'Mot de passe trop long.' });
    afficher(vi.fn().mockRejectedValue(erreur));
    await remplirEtEnvoyer();
    expect(await screen.findByRole('alert')).toHaveTextContent('Vérifiez les champs du formulaire.');
    const motDePasse = screen.getByLabelText('Mot de passe');
    expect(motDePasse).toHaveAttribute('aria-invalid', 'true');
    expect(motDePasse).toHaveAccessibleDescription('Mot de passe trop long.');
    expect(screen.getByLabelText('Adresse e-mail')).not.toHaveAttribute('aria-invalid');
    await waitFor(() => expect(motDePasse).toHaveFocus());
    expect(screen.getByRole('button', { name: 'Se connecter' })).toBeInTheDocument();
  });

  it('place le focus sur l’e-mail quand il précède un autre champ en erreur', async () => {
    const erreur = creerErreurApi('Données invalides.', 422, 'validation', { mot_de_passe: 'Trop long.', email: 'Adresse e-mail invalide.' });
    afficher(vi.fn().mockRejectedValue(erreur));
    await remplirEtEnvoyer();
    await waitFor(() => expect(screen.getByLabelText('Adresse e-mail')).toHaveFocus());
    expect(screen.getByLabelText('Adresse e-mail')).toHaveAccessibleDescription('Adresse e-mail invalide.');
  });

  it('désactive le bouton pendant la requête', async () => {
    let terminer!: () => void;
    afficher(vi.fn().mockReturnValue(new Promise<void>(resoudre => { terminer = resoudre; })));
    await remplirEtEnvoyer();
    expect(screen.getByRole('button', { name: 'Connexion…' })).toBeDisabled();
    terminer();
    await waitFor(() => expect(screen.getByRole('button', { name: 'Se connecter' })).toBeEnabled());
  });

  it('ne fixe aucun minimum au mot de passe de connexion', () => {
    afficher();
    const motDePasse = screen.getByLabelText('Mot de passe');
    expect(motDePasse).not.toHaveAttribute('minlength');
    expect(motDePasse).toHaveAttribute('maxlength', '128');
    expect(motDePasse).toHaveAttribute('autocomplete', 'current-password');
    expect(screen.getByLabelText('Adresse e-mail')).toHaveAttribute('autocomplete', 'username');
  });

  it('affiche l’avertissement reçu', () => {
    afficher(undefined, undefined, 'Votre session a expiré. Reconnectez-vous.');
    expect(screen.getByRole('alert')).toHaveTextContent('Votre session a expiré. Reconnectez-vous.');
    expect(screen.getByRole('button', { name: 'Se connecter' })).toBeInTheDocument();
  });
});
