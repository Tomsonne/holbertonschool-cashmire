import { afterEach, describe, expect, it, vi } from 'vitest';
import { requeteApi, surSessionExpiree } from './client';
import type { ErreurApi } from './erreurs';

const desinscriptions: (() => void)[] = [];

afterEach(() => {
  desinscriptions.splice(0).forEach(desinscrire => desinscrire());
  vi.restoreAllMocks();
  window.history.replaceState({}, '', '/');
});

function ecouter() {
  const rappel = vi.fn();
  desinscriptions.push(surSessionExpiree(rappel));
  return rappel;
}

function repondre(status: number, corps?: unknown) {
  return vi.spyOn(globalThis, 'fetch').mockResolvedValue(
    new Response(corps === undefined ? null : JSON.stringify(corps), { status }),
  );
}

async function erreurDe(promesse: Promise<unknown>): Promise<ErreurApi> {
  try { await promesse; } catch (cause) { return cause as ErreurApi; }
  throw new Error('La requête aurait dû échouer.');
}

describe('Client API', () => {
  it('renseigne status, code, message et champs depuis le corps d’erreur', async () => {
    repondre(422, { erreur: { code: 'validation', message: 'Données invalides.', champs: { montant_limite: 'Montant requis.' } } });
    const erreur = await erreurDe(requeteApi('/budgets', 'POST', {}));
    expect(erreur).toBeInstanceOf(Error);
    expect(erreur).toMatchObject({ status: 422, code: 'validation', message: 'Données invalides.', champs: { montant_limite: 'Montant requis.' } });
  });

  it('renvoie undefined sur une réponse 204', async () => {
    repondre(204);
    await expect(requeteApi('/budgets/b-1', 'DELETE')).resolves.toBeUndefined();
  });

  it('signale une panne réseau avec status 0 et code reseau', async () => {
    vi.spyOn(globalThis, 'fetch').mockRejectedValue(new TypeError('network error'));
    const erreur = await erreurDe(requeteApi('/categories'));
    expect(erreur).toMatchObject({ status: 0, code: 'reseau', message: 'Impossible de joindre le service. Réessayez.' });
  });

  it('prévient l’écouteur sur un 401 d’une route privée', async () => {
    const rappel = ecouter();
    repondre(401, { erreur: { code: 'non_authentifie', message: 'Authentification requise.' } });
    const erreur = await erreurDe(requeteApi('/budgets?mois=2026-10'));
    expect(erreur.status).toBe(401);
    expect(rappel).toHaveBeenCalledTimes(1);
  });

  it.each([
    '/authentification/connexion',
    '/authentification/inscription',
    '/authentification/moi',
    '/authentification/deconnexion',
  ])('ne prévient pas l’écouteur sur un 401 de %s', async (chemin) => {
    const rappel = ecouter();
    repondre(401, { erreur: { code: 'non_authentifie', message: 'Authentification requise.' } });
    await erreurDe(requeteApi(chemin, 'POST', {}));
    expect(rappel).not.toHaveBeenCalled();
  });

  it.each([403, 429])('ne prévient pas l’écouteur sur un %i', async (status) => {
    const rappel = ecouter();
    repondre(status, { erreur: { code: 'refuse', message: 'Refusé.' } });
    await erreurDe(requeteApi('/budgets', 'POST', {}));
    expect(rappel).not.toHaveBeenCalled();
  });

  it('ne prévient plus l’écouteur après désinscription', async () => {
    const rappel = vi.fn();
    const desinscrire = surSessionExpiree(rappel);
    desinscrire();
    repondre(401, { erreur: { code: 'non_authentifie', message: 'Authentification requise.' } });
    await erreurDe(requeteApi('/categories'));
    expect(rappel).not.toHaveBeenCalled();
  });
});
