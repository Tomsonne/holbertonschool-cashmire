// Erreur levée par le client API : `status` vaut 0 et `code` vaut `reseau` si le service est injoignable.
export type ErreurApi = Error & {
  status: number;
  code: string;
  champs?: Record<string, string>;
};

export function creerErreurApi(message: string, status: number, code: string, champs?: Record<string, string>): ErreurApi {
  const erreur = new Error(message) as ErreurApi;
  erreur.status = status;
  erreur.code = code;
  erreur.champs = champs;
  return erreur;
}
