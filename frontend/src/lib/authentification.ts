import type { ErreurApi } from './api/erreurs';

export type ContexteAuth = 'connexion' | 'inscription';

export const MESSAGE_SERVICE_INJOIGNABLE = 'Impossible de joindre le service. Réessayez.';
export const MESSAGE_CHAMPS_INVALIDES = 'Vérifiez les champs du formulaire.';
export const MESSAGE_EMAIL_DEJA_PRIS = 'Un compte existe déjà avec cette adresse e-mail.';

// Textes utilisés quand l'API ne fournit pas de message.
const MESSAGES_PAR_DEFAUT: Record<number, string> = {
  401: 'Adresse e-mail ou mot de passe incorrect.',
  403: 'Requête refusée. Rechargez la page puis réessayez.',
  429: 'Trop de tentatives. Réessayez plus tard.',
};

// Le client remplace un message absent par « Erreur HTTP <statut> » : ce texte technique n'est pas affiché.
function messageApi(erreur: ErreurApi): string | undefined {
  const message = erreur.message?.trim();
  return message && message !== `Erreur HTTP ${erreur.status}` ? message : undefined;
}

// Message général d'une erreur de soumission des formulaires de connexion et d'inscription.
export function messageErreurAuth(cause: unknown, contexte: ContexteAuth): string {
  const erreur = cause as ErreurApi | undefined;
  const status = erreur?.status;
  if (erreur && (status === 401 || status === 403 || status === 429)) return messageApi(erreur) ?? MESSAGES_PAR_DEFAUT[status];
  if (status === 409 && contexte === 'inscription') return MESSAGE_EMAIL_DEJA_PRIS;
  if (status === 422) return MESSAGE_CHAMPS_INVALIDES;
  return MESSAGE_SERVICE_INJOIGNABLE;
}

// Erreurs par champ d'un 422 (clés de l'API : `email`, `mot_de_passe`, `nom_affichage`).
export function champsErreurAuth(cause: unknown): Record<string, string> {
  const erreur = cause as ErreurApi | undefined;
  return erreur?.status === 422 ? { ...erreur.champs } : {};
}
