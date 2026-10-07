import type { ErreurApi } from '../budgets';

type ErreurReponse = { erreur?: { message?: string; champs?: Record<string, string> } };

export async function requeteApi<T>(chemin: string, methode = 'GET', donnees?: object): Promise<T> {
  let reponse: Response;
  try {
    reponse = await fetch(`/api${chemin}`, {
      method: methode,
      credentials: 'include',
      headers: donnees ? { Accept: 'application/json', 'Content-Type': 'application/json' } : { Accept: 'application/json' },
      body: donnees ? JSON.stringify(donnees) : undefined,
    });
  } catch {
    throw new Error('Impossible de joindre le service. Réessayez.');
  }

  if (!reponse.ok) {
    let corps: ErreurReponse = {};
    try { corps = await reponse.json() as ErreurReponse; } catch { /* réponse sans JSON */ }
    const erreur = new Error(corps.erreur?.message ?? `Erreur HTTP ${reponse.status}`) as ErreurApi;
    erreur.status = reponse.status;
    erreur.champs = corps.erreur?.champs;
    throw erreur;
  }
  if (reponse.status === 204) return undefined as T;
  return reponse.json() as Promise<T>;
}
