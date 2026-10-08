import { creerErreurApi } from './erreurs';

type ErreurReponse = { erreur?: { code?: string; message?: string; champs?: Record<string, string> } };

// Un 401 sur ces chemins ne signifie pas qu'une session ouverte a expiré
// (mauvais mot de passe, visiteur jamais connecté, déconnexion déjà effective).
const CHEMINS_SANS_EXPIRATION = [
  '/authentification/connexion',
  '/authentification/inscription',
  '/authentification/moi',
  '/authentification/deconnexion',
];

const ecouteursExpiration = new Set<() => void>();

// Enregistre un écouteur appelé à chaque 401 d'une route privée. Renvoie la fonction de désinscription.
export function surSessionExpiree(rappel: () => void): () => void {
  ecouteursExpiration.add(rappel);
  return () => { ecouteursExpiration.delete(rappel); };
}

function signalerExpiration(chemin: string) {
  if (CHEMINS_SANS_EXPIRATION.includes(chemin.split('?')[0])) return;
  for (const rappel of [...ecouteursExpiration]) rappel();
}

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
    throw creerErreurApi('Impossible de joindre le service. Réessayez.', 0, 'reseau');
  }

  if (!reponse.ok) {
    let corps: ErreurReponse = {};
    try { corps = await reponse.json() as ErreurReponse; } catch { /* réponse sans JSON */ }
    const erreur = creerErreurApi(
      corps.erreur?.message ?? `Erreur HTTP ${reponse.status}`,
      reponse.status,
      corps.erreur?.code ?? 'inconnu',
      corps.erreur?.champs,
    );
    if (reponse.status === 401) signalerExpiration(chemin);
    throw erreur;
  }
  if (reponse.status === 204) return undefined as T;
  return reponse.json() as Promise<T>;
}
