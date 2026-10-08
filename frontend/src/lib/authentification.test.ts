import { describe, expect, it } from 'vitest';
import { creerErreurApi } from './api/erreurs';
import { champsErreurAuth, messageErreurAuth } from './authentification';

// Reproduit le message que pose le client quand le corps de la réponse n'en contient pas.
const sansMessage = (status: number) => creerErreurApi(`Erreur HTTP ${status}`, status, 'inconnu');

describe('Messages d’erreur de connexion et d’inscription', () => {
  it.each([
    [401, 'identifiants_invalides', 'Identifiants invalides.'],
    [403, 'origine_refusee', 'Origine de la requête refusée.'],
    [429, 'trop_de_tentatives', 'Trop de tentatives, réessayez plus tard.'],
  ])('reprend le message de l’API pour un %i', (status, code, message) => {
    expect(messageErreurAuth(creerErreurApi(message, status, code), 'connexion')).toBe(message);
  });

  it.each([
    [401, 'Adresse e-mail ou mot de passe incorrect.'],
    [403, 'Requête refusée. Rechargez la page puis réessayez.'],
    [429, 'Trop de tentatives. Réessayez plus tard.'],
  ])('donne un texte par défaut pour un %i sans message', (status, attendu) => {
    expect(messageErreurAuth(sansMessage(status), 'connexion')).toBe(attendu);
  });

  it('explique un 409 à l’inscription', () => {
    const erreur = creerErreurApi('Email déjà utilisé.', 409, 'conflit');
    expect(messageErreurAuth(erreur, 'inscription')).toBe('Un compte existe déjà avec cette adresse e-mail.');
  });

  it('ne traite pas un 409 inattendu à la connexion comme un email déjà pris', () => {
    const erreur = creerErreurApi('Conflit.', 409, 'conflit');
    expect(messageErreurAuth(erreur, 'connexion')).toBe('Impossible de joindre le service. Réessayez.');
  });

  it.each(['connexion', 'inscription'] as const)('renvoie vers les champs pour un 422 (%s)', (contexte) => {
    const erreur = creerErreurApi('Données invalides.', 422, 'validation', { email: 'Adresse e-mail invalide.' });
    expect(messageErreurAuth(erreur, contexte)).toBe('Vérifiez les champs du formulaire.');
  });

  it.each([
    ['un 500', sansMessage(500)],
    ['une panne réseau', creerErreurApi('Impossible de joindre le service. Réessayez.', 0, 'reseau')],
    ['une erreur inconnue', new Error('boum')],
    ['une cause absente', undefined],
  ])('annonce un service injoignable pour %s', (_cas, cause) => {
    expect(messageErreurAuth(cause, 'connexion')).toBe('Impossible de joindre le service. Réessayez.');
    expect(messageErreurAuth(cause, 'inscription')).toBe('Impossible de joindre le service. Réessayez.');
  });
});

describe('Erreurs par champ', () => {
  it('reprend les champs d’un 422', () => {
    const champs = { mot_de_passe: 'Au moins 10 caractères.' };
    expect(champsErreurAuth(creerErreurApi('Données invalides.', 422, 'validation', champs))).toEqual(champs);
  });

  it('ignore les champs hors 422 et un 422 sans champs', () => {
    expect(champsErreurAuth(creerErreurApi('Conflit.', 409, 'conflit', { email: 'Pris.' }))).toEqual({});
    expect(champsErreurAuth(creerErreurApi('Données invalides.', 422, 'validation'))).toEqual({});
    expect(champsErreurAuth(undefined)).toEqual({});
  });
});
