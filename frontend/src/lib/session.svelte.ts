import { sessionApi, type Utilisateur } from './api/budgets';
import { surSessionExpiree } from './api/client';
import type { ErreurApi } from './api/erreurs';

export type EtatSession = 'chargement' | 'deconnecte' | 'pret' | 'erreur';

export const MESSAGE_SESSION_EXPIREE = 'Votre session a expiré. Reconnectez-vous.';

// État de session partagé par toute l'interface. Le JWT reste dans le cookie HttpOnly :
// ce store ne connaît que l'utilisateur renvoyé par l'API.
class Session {
  utilisateur = $state<Utilisateur | null>(null);
  etat = $state<EtatSession>('chargement');
  message = $state('');

  charger = async () => {
    this.etat = 'chargement';
    this.message = '';
    try {
      this.utilisateur = await sessionApi.moi();
      this.etat = 'pret';
    } catch (cause) {
      this.utilisateur = null;
      if ((cause as ErreurApi)?.status === 401) this.etat = 'deconnecte';
      else {
        this.etat = 'erreur';
        this.message = 'Impossible de charger votre session. Réessayez.';
      }
    }
  };

  // Laisse remonter l'erreur : c'est l'écran de connexion qui décide quoi afficher.
  connecter = async (email: string, motDePasse: string) => {
    this.message = '';
    this.utilisateur = await sessionApi.connecter(email, motDePasse);
    this.etat = 'pret';
  };

  // Un 401 signifie que la session était déjà terminée : on la considère fermée.
  deconnecter = async () => {
    try { await sessionApi.deconnecter(); }
    catch (cause) {
      if ((cause as ErreurApi)?.status !== 401) {
        this.message = (cause as Error)?.message || 'Déconnexion impossible.';
        return;
      }
    }
    this.fermer('');
  };

  fermer(message: string) {
    this.utilisateur = null;
    this.etat = 'deconnecte';
    this.message = message;
  }
}

export const session = new Session();

surSessionExpiree(() => session.fermer(MESSAGE_SESSION_EXPIREE));
