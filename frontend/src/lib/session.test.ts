import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { requeteApi } from './api/client';
import { MESSAGE_SESSION_EXPIREE, session } from './session.svelte';

const alice = { id: 'u-1', email: 'alice@example.test', nom_affichage: 'Alice' };
const json = (valeur: unknown, status = 200) => new Response(JSON.stringify(valeur), { status });
const nonAuthentifie = () => json({ erreur: { code: 'non_authentifie', message: 'Authentification requise.' } }, 401);

beforeEach(() => {
  session.utilisateur = null;
  session.etat = 'chargement';
  session.message = '';
});

afterEach(() => {
  vi.restoreAllMocks();
  window.history.replaceState({}, '', '/');
});

async function connecterAlice() {
  vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(json(alice));
  await session.charger();
  vi.restoreAllMocks();
}

describe('Store de session', () => {
  it('charge l’utilisateur connecté', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(json(alice));
    await session.charger();
    expect(fetchMock).toHaveBeenCalledWith('/api/authentification/moi', expect.objectContaining({ credentials: 'include' }));
    expect(session).toMatchObject({ utilisateur: alice, etat: 'pret', message: '' });
  });

  it('passe en déconnecté sans message quand /moi répond 401', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(nonAuthentifie());
    await session.charger();
    expect(session).toMatchObject({ utilisateur: null, etat: 'deconnecte', message: '' });
  });

  it('passe en erreur quand /moi est injoignable', async () => {
    vi.spyOn(globalThis, 'fetch').mockRejectedValueOnce(new TypeError('network error'));
    await session.charger();
    expect(session.etat).toBe('erreur');
    expect(session.message).not.toBe('');
  });

  it('se ferme avec un message quand la session expire en cours d’usage', async () => {
    await connecterAlice();
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(nonAuthentifie());
    await expect(requeteApi('/budgets?mois=2026-10')).rejects.toMatchObject({ status: 401 });
    expect(session).toMatchObject({ utilisateur: null, etat: 'deconnecte', message: MESSAGE_SESSION_EXPIREE });
  });

  it('traite un 401 à la déconnexion comme une déconnexion réussie', async () => {
    await connecterAlice();
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(nonAuthentifie());
    await session.deconnecter();
    expect(session).toMatchObject({ utilisateur: null, etat: 'deconnecte', message: '' });
  });

  it('reste connecté et affiche un message si la déconnexion échoue autrement', async () => {
    await connecterAlice();
    vi.spyOn(globalThis, 'fetch').mockRejectedValueOnce(new TypeError('network error'));
    await session.deconnecter();
    expect(session).toMatchObject({ utilisateur: alice, etat: 'pret', message: 'Impossible de joindre le service. Réessayez.' });
  });

  it('met l’utilisateur à jour après une connexion réussie', async () => {
    session.etat = 'deconnecte';
    session.message = MESSAGE_SESSION_EXPIREE;
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(json(alice));
    await session.connecter('alice@example.test', 'mot-de-passe');
    expect(fetchMock).toHaveBeenCalledWith('/api/authentification/connexion', expect.objectContaining({ method: 'POST' }));
    expect(session).toMatchObject({ utilisateur: alice, etat: 'pret', message: '' });
  });

  it.each([
    [401, 'non_authentifie'],
    [429, 'trop_de_tentatives'],
  ])('laisse remonter une erreur %i de connexion sans changer l’état', async (status, code) => {
    session.etat = 'deconnecte';
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(json({ erreur: { code, message: 'Refusé.' } }, status));
    await expect(session.connecter('alice@example.test', 'faux')).rejects.toMatchObject({ status, code });
    expect(session).toMatchObject({ utilisateur: null, etat: 'deconnecte', message: '' });
  });
});
