"""Erreur applicative commune : les routes lèvent ErreurApi pour répondre une erreur 4xx.

Exemple :
    raise ErreurApi(404, "Dépense introuvable.")
    raise ErreurApi(409, "Un budget existe déjà ce mois.", champs={"categorie_id": "Déjà budgétée."})
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
        super().__init__(message)
        self.statut = statut
        self.message = message
        self.champs = champs
        self.code = code or CODES_PAR_STATUT.get(statut, CODE_PAR_DEFAUT)
