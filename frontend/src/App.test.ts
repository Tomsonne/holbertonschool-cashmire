import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/svelte';
import App from './App.svelte';

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
});
