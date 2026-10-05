"""Erreur applicative commune : les routes lèvent ErreurApi pour répondre une erreur 4xx.

Exemple :
    raise ErreurApi(404, "Dépense introuvable.")
    raise ErreurApi(409, "Un budget existe déjà ce mois.", champs={"categorie_id": "Déjà budgétée."})

ErreurApi est réservée aux statuts 4xx : le message est renvoyé tel quel au client. Les erreurs
500 ne se lèvent jamais à la main ; elles sont gérées par le gestionnaire générique, qui renvoie
un message fixe (aucun détail SQL ni trace).
"""

# Statut HTTP -> code du contrat (voir docs/api-design.md).
CODES_PAR_STATUT: dict[int, str] = {
    400: "requete_invalide",
    401: "non_authentifie",
    404: "introuvable",
    409: "conflit",
    422: "donnees_invalides",
    429: "trop_de_tentatives",
    500: "erreur_interne",
}
CODE_PAR_DEFAUT = "requete_invalide"


class ErreurApi(Exception):
    def __init__(
        self,
        statut: int,
        message: str,
        champs: dict[str, str] | None = None,
        code: str | None = None,
    ) -> None:
        # Vérification avant tout : un statut hors 4xx est une erreur de programmation. On lève
        # ValueError (sans reprendre le message, qui pourrait contenir un détail interne) ;
        # le gestionnaire générique répond alors une 500 au message fixe.
        if not 400 <= statut < 500:
            raise ValueError("ErreurApi est réservée aux statuts 4xx.")
        super().__init__(message)
        self.statut = statut
        self.message = message
        self.champs = champs
        self.code = code or CODES_PAR_STATUT.get(statut, CODE_PAR_DEFAUT)
