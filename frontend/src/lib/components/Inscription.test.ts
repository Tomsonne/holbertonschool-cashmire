import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/svelte';
import { creerErreurApi } from '../api/erreurs';
import Inscription from './Inscription.svelte';

afterEach(() => { cleanup(); vi.restoreAllMocks(); });

const NOM = 'Nom d’affichage';

async function remplirEtEnvoyer() {
  await fireEvent.input(screen.getByLabelText('Adresse e-mail'), { target: { value: 'alice@example.test' } });
  await fireEvent.input(screen.getByLabelText('Mot de passe'), { target: { value: 'mot-de-passe-solide' } });
  await fireEvent.input(screen.getByLabelText(NOM), { target: { value: 'Alice' } });
  await fireEvent.click(screen.getByRole('button', { name: 'Créer mon compte' }));
}

describe('Formulaire d’inscription', () => {
  it('annonce la création du compte et renvoie vers la connexion sans se connecter', async () => {
    const inscrire = vi.fn().mockResolvedValue({ id: 'u-1', email: 'alice@example.test', nom_affichage: 'Alice' });
    render(Inscription, { inscrire });
    await remplirEtEnvoyer();
    const statut = await screen.findByRole('status');
    expect(statut).toHaveTextContent('Compte créé. Vous pouvez maintenant vous connecter.');
    expect(screen.getByRole('link', { name: 'Se connecter' })).toHaveAttribute('href', '/connexion');
    expect(screen.queryByRole('button', { name: 'Créer mon compte' })).not.toBeInTheDocument();
    expect(inscrire).toHaveBeenCalledTimes(1);
    expect(inscrire).toHaveBeenCalledWith('alice@example.test', 'mot-de-passe-solide', 'Alice');
    await waitFor(() => expect(statut).toHaveFocus());
  });

  it('garde le formulaire et les saisies quand l’adresse est déjà prise (409)', async () => {
    render(Inscription, { inscrire: vi.fn().mockRejectedValue(creerErreurApi('Email déjà utilisé.', 409, 'conflit')) });
    await remplirEtEnvoyer();
    expect(await screen.findByRole('alert')).toHaveTextContent('Un compte existe déjà avec cette adresse e-mail.');
    expect(screen.getByLabelText('Adresse e-mail')).toHaveValue('alice@example.test');
    expect(screen.getByLabelText('Mot de passe')).toHaveValue('mot-de-passe-solide');
    expect(screen.getByLabelText(NOM)).toHaveValue('Alice');
    expect(screen.getByRole('button', { name: 'Créer mon compte' })).toBeEnabled();
    await waitFor(() => expect(screen.getByRole('alert')).toHaveFocus());
  });

  it('relie les erreurs d’un 422 à leurs champs et place le focus sur le premier', async () => {
    const erreur = creerErreurApi('Données invalides.', 422, 'validation', {
      nom_affichage: 'Le nom d’affichage est requis.',
      mot_de_passe: 'Le mot de passe doit contenir au moins 10 caractères.',
    });
    render(Inscription, { inscrire: vi.fn().mockRejectedValue(erreur) });
    await remplirEtEnvoyer();
    expect(await screen.findByRole('alert')).toHaveTextContent('Vérifiez les champs du formulaire.');

    const motDePasse = screen.getByLabelText('Mot de passe');
    expect(motDePasse).toHaveAttribute('aria-invalid', 'true');
    expect(motDePasse.getAttribute('aria-describedby')?.split(' ')).toContain('inscription-mot-de-passe-erreur');
    expect(motDePasse).toHaveAccessibleDescription(/au moins 10 caractères/);

    const nom = screen.getByLabelText(NOM);
    expect(nom).toHaveAttribute('aria-invalid', 'true');
    expect(nom).toHaveAttribute('aria-describedby', 'inscription-nom-erreur');
    expect(nom).toHaveAccessibleDescription('Le nom d’affichage est requis.');

    const email = screen.getByLabelText('Adresse e-mail');
    expect(email).not.toHaveAttribute('aria-invalid');
    expect(email).not.toHaveAttribute('aria-describedby');
    await waitFor(() => expect(motDePasse).toHaveFocus());
  });

  it('relie l’erreur d’e-mail à son champ et place le focus dessus', async () => {
    const erreur = creerErreurApi('Données invalides.', 422, 'donnees_invalides', {
      email: 'Adresse e-mail invalide.',
    });
    render(Inscription, { inscrire: vi.fn().mockRejectedValue(erreur) });
    await remplirEtEnvoyer();
    expect(await screen.findByRole('alert')).toHaveTextContent('Vérifiez les champs du formulaire.');

    const email = screen.getByLabelText('Adresse e-mail');
    expect(email).toHaveAttribute('aria-invalid', 'true');
    expect(email.getAttribute('aria-describedby')?.split(' ')).toContain('inscription-email-erreur');
    expect(email).toHaveAccessibleDescription('Adresse e-mail invalide.');
    expect(screen.getByLabelText('Mot de passe')).not.toHaveAttribute('aria-invalid');
    expect(screen.getByLabelText(NOM)).not.toHaveAttribute('aria-invalid');
    await waitFor(() => expect(email).toHaveFocus());
  });

  it('désactive le bouton pendant la requête', async () => {
    let terminer!: () => void;
    render(Inscription, { inscrire: vi.fn().mockReturnValue(new Promise<void>(resoudre => { terminer = resoudre; })) });
    await remplirEtEnvoyer();
    expect(screen.getByRole('button', { name: 'Création du compte…' })).toBeDisabled();
    terminer();
    expect(await screen.findByRole('status')).toHaveTextContent('Compte créé.');
  });

  it('applique les contraintes de l’API aux champs', () => {
    render(Inscription, { inscrire: vi.fn() });
    const email = screen.getByLabelText('Adresse e-mail');
    expect(email).toHaveAttribute('type', 'email');
    expect(email).toHaveAttribute('autocomplete', 'username');
    expect(email).toBeRequired();
    const motDePasse = screen.getByLabelText('Mot de passe');
    expect(motDePasse).toHaveAttribute('minlength', '10');
    expect(motDePasse).toHaveAttribute('maxlength', '128');
    expect(motDePasse).toHaveAttribute('autocomplete', 'new-password');
    expect(motDePasse).toBeRequired();
    expect(motDePasse).toHaveAccessibleDescription('Entre 10 et 128 caractères.');
    const nom = screen.getByLabelText(NOM);
    expect(nom).toHaveAttribute('maxlength', '100');
    expect(nom).toHaveAttribute('autocomplete', 'name');
    expect(nom).toBeRequired();
  });
});