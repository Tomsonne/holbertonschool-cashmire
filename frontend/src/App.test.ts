import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/svelte';
import App from './App.svelte';
import { aller } from './lib/navigation';
import { session } from './lib/session.svelte';

// jsdom n'implémente pas la navigation : la redirection est observée sur ce mock.
vi.mock('./lib/navigation', () => ({ aller: vi.fn() }));

afterEach(() => { cleanup(); vi.restoreAllMocks(); window.history.replaceState({}, '', '/'); });

describe('Cashmire health screen', () => {
  it('announces an API failure and retries on request', async () => {
    window.history.replaceState({}, '', '/etat-technique');
    const fetchMock = vi.spyOn(globalThis, 'fetch')
      .mockRejectedValueOnce(new TypeError('network error'))
      .mockResolvedValueOnce(new Response(JSON.stringify({ statut: 'ok', base_de_donnees: 'disponible' }), { status: 200 }));
    render(App);
    expect(await screen.findByText('Service momentanément indisponible')).toBeInTheDocument();
    await fireEvent.click(screen.getByRole('button', { name: 'Réessayer' }));
    await waitFor(() => expect(screen.getByText('Tout fonctionne')).toBeInTheDocument());
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it('ouvre les budgets à la racine et demande une connexion sans cookie JWT', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(new Response(JSON.stringify({ erreur: { code: 'non_authentifie', message: 'Authentification requise.' } }), { status: 401 }));
    render(App);
    expect(await screen.findByRole('heading', { name: 'Accéder à mes budgets' })).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith('/api/authentification/moi', expect.objectContaining({ credentials: 'include' }));
  });

  it('charge les catégories et les budgets après une connexion', async () => {
    const json = (valeur: unknown) => new Response(JSON.stringify(valeur), { status: 200 });
    const fetchMock = vi.spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce(new Response(JSON.stringify({ erreur: { message: 'Authentification requise.' } }), { status: 401 }))
      .mockResolvedValueOnce(json({ id: 'u-1', email: 'alice@example.test', nom_affichage: 'Alice' }))
      .mockResolvedValueOnce(json([{ id: 'c-1', nom: 'Alimentation' }]))
      .mockResolvedValueOnce(json([]));
    render(App);
    await screen.findByRole('heading', { name: 'Accéder à mes budgets' });
    await fireEvent.input(screen.getByLabelText('Adresse e-mail'), { target: { value: 'alice@example.test' } });
    await fireEvent.input(screen.getByLabelText('Mot de passe'), { target: { value: 'mot-de-passe' } });
    await fireEvent.click(screen.getByRole('button', { name: 'Se connecter' }));
    expect(await screen.findByText(/Aucun budget pour ce mois/)).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith('/api/authentification/connexion', expect.objectContaining({ method: 'POST', credentials: 'include' }));
    expect(fetchMock).toHaveBeenCalledWith('/api/categories', expect.objectContaining({ credentials: 'include' }));
    expect(fetchMock).toHaveBeenCalledWith(expect.stringMatching(/^\/api\/budgets\?mois=/), expect.objectContaining({ credentials: 'include' }));
  });

  it('ouvre la synthèse avec les dépenses de l’API', async () => {
    window.history.replaceState({}, '', '/synthese');
    const json = (valeur: unknown, status = 200) => new Response(JSON.stringify(valeur), { status });
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      const url = String(input);
      if (url.endsWith('/authentification/moi')) return json({ id: 'u-1', nom_affichage: 'Alice', email: 'alice@example.test' });
      if (url.endsWith('/categories')) return json([]);
      if (url.startsWith('/api/budgets?')) return json([]);
      if (url.startsWith('/api/depenses?')) return json({ elements: [{ id: 'd-1', libelle: 'Courses', montant: '12.30', date_depense: '2026-10-01', categorie: { id: 'c-1', nom: 'Alimentation' } }], total: 1 });
      throw new Error(`Requête inattendue : ${url}`);
    });
    render(App);
    expect(await screen.findByText('Courses')).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith(expect.stringMatching(/^\/api\/depenses\?mois=.*limite=100&decalage=0/), expect.objectContaining({ credentials: 'include' }));
  });

  it('ouvre la page des dépenses avec la liste paginée de l’API', async () => {
    window.history.replaceState({}, '', '/depenses');
    const json = (valeur: unknown, status = 200) => new Response(JSON.stringify(valeur), { status });
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      const url = String(input);
      if (url.endsWith('/authentification/moi')) return json({ id: 'u-1', nom_affichage: 'Alice', email: 'alice@example.test' });
      if (url.endsWith('/categories')) return json([{ id: 'c-1', nom: 'Alimentation' }]);
      if (url.startsWith('/api/depenses?')) return json({ elements: [{ id: 'd-1', libelle: 'Courses', montant: '12.30', date_depense: '2026-10-01', categorie: { id: 'c-1', nom: 'Alimentation' } }], total: 1 });
      throw new Error(`Requête inattendue : ${url}`);
    });
    render(App);
    expect(await screen.findByText('Courses')).toBeInTheDocument();
    expect(screen.getByText('12,30 €')).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith(expect.stringMatching(/^\/api\/depenses\?mois=.*limite=10&decalage=0/), expect.objectContaining({ credentials: 'include' }));
  });

  it('ramène au formulaire de connexion quand la session expire sur les budgets', async () => {
    window.history.replaceState({}, '', '/budgets');
    const json = (valeur: unknown, status = 200) => new Response(JSON.stringify(valeur), { status });
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      const url = String(input);
      if (url.endsWith('/authentification/moi')) return json({ id: 'u-1', nom_affichage: 'Alice', email: 'alice@example.test' });
      if (url.endsWith('/categories')) return json([]);
      if (url.startsWith('/api/budgets?')) return json({ erreur: { code: 'non_authentifie', message: 'Authentification requise.' } }, 401);
      throw new Error(`Requête inattendue : ${url}`);
    });
    render(App);
    expect(await screen.findByRole('heading', { name: 'Accéder à mes budgets' })).toBeInTheDocument();
    expect(screen.getByRole('alert')).toHaveTextContent('Votre session a expiré. Reconnectez-vous.');
    expect(screen.queryByText('Bonjour, Alice')).not.toBeInTheDocument();
  });

  it('affiche le chargement de la session tant que /moi n’a pas répondu', async () => {
    window.history.replaceState({}, '', '/budgets');
    vi.spyOn(globalThis, 'fetch').mockReturnValue(new Promise(() => {}));
    render(App);
    expect(screen.getByRole('status')).toHaveTextContent('Chargement de votre session…');
  });
});

describe('Pages de connexion et d’inscription', () => {
  const json = (valeur: unknown, status = 200) => new Response(JSON.stringify(valeur), { status });
  const alice = { id: 'u-1', email: 'alice@example.test', nom_affichage: 'Alice' };

  // Le store de session est partagé par tout le fichier : chaque test repart d'un visiteur.
  beforeEach(() => {
    vi.mocked(aller).mockClear();
    session.utilisateur = null;
    session.etat = 'chargement';
    session.message = '';
  });

  async function remplirConnexion() {
    await fireEvent.input(screen.getByLabelText('Adresse e-mail'), { target: { value: 'alice@example.test' } });
    await fireEvent.input(screen.getByLabelText('Mot de passe'), { target: { value: 'mot-de-passe' } });
    await fireEvent.click(screen.getByRole('button', { name: 'Se connecter' }));
  }

  it('connecte sur /connexion sans appeler /moi puis redirige vers les budgets', async () => {
    window.history.replaceState({}, '', '/connexion');
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(json(alice));
    render(App);
    expect(screen.getByRole('heading', { name: 'Connexion' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Créer un compte' })).toHaveAttribute('href', '/inscription');
    expect(fetchMock).not.toHaveBeenCalled();
    await remplirConnexion();
    await waitFor(() => expect(aller).toHaveBeenCalledWith('/budgets'));
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock).toHaveBeenCalledWith('/api/authentification/connexion', expect.objectContaining({ method: 'POST', credentials: 'include' }));
  });

  it('garde le formulaire de /connexion après un 401 sans rediriger', async () => {
    window.history.replaceState({}, '', '/connexion');
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(json({ erreur: { code: 'identifiants_invalides', message: 'Identifiants invalides.' } }, 401));
    render(App);
    await remplirConnexion();
    expect(await screen.findByRole('alert')).toHaveTextContent('Identifiants invalides.');
    expect(screen.getByRole('heading', { name: 'Connexion' })).toBeInTheDocument();
    expect(aller).not.toHaveBeenCalled();
  });

  it('affiche l’inscription sans appeler /moi et annonce la création du compte', async () => {
    window.history.replaceState({}, '', '/inscription');
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(json({ ...alice, date_creation: '2026-10-08T10:00:00Z' }, 201));
    render(App);
    expect(screen.getByRole('heading', { name: 'Créer un compte' })).toBeInTheDocument();
    expect(fetchMock).not.toHaveBeenCalled();
    await fireEvent.input(screen.getByLabelText('Adresse e-mail'), { target: { value: 'alice@example.test' } });
    await fireEvent.input(screen.getByLabelText('Mot de passe'), { target: { value: 'mot-de-passe-solide' } });
    await fireEvent.input(screen.getByLabelText('Nom d’affichage'), { target: { value: 'Alice' } });
    await fireEvent.click(screen.getByRole('button', { name: 'Créer mon compte' }));
    expect(await screen.findByRole('status')).toHaveTextContent('Compte créé. Vous pouvez maintenant vous connecter.');
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock).toHaveBeenCalledWith('/api/authentification/inscription', expect.objectContaining({ method: 'POST' }));
    expect(aller).not.toHaveBeenCalled();
  });

  it.each([
    [429, { code: 'trop_de_tentatives', message: 'Trop de tentatives, réessayez plus tard.' }, 'Trop de tentatives, réessayez plus tard.'],
    [500, { code: 'erreur_interne', message: 'Erreur interne du serveur.' }, 'Impossible de joindre le service. Réessayez.'],
  ])('garde le formulaire d’une page privée après un %i à la connexion', async (status, erreur, attendu) => {
    window.history.replaceState({}, '', '/budgets');
    const fetchMock = vi.spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce(json({ erreur: { code: 'non_authentifie', message: 'Authentification requise.' } }, 401))
      .mockResolvedValueOnce(json({ erreur }, status));
    render(App);
    await screen.findByRole('heading', { name: 'Accéder à mes budgets' });
    await remplirConnexion();
    expect(await screen.findByRole('alert')).toHaveTextContent(attendu);
    expect(screen.queryByRole('heading', { name: 'Service indisponible' })).not.toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Accéder à mes budgets' })).toBeInTheDocument();
    expect(screen.getByLabelText('Adresse e-mail')).toHaveValue('alice@example.test');
    expect(screen.getByRole('button', { name: 'Se connecter' })).toBeEnabled();
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });
});
