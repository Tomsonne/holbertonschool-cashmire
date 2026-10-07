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
});
