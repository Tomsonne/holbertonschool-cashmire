"""Types Pydantic pour les montants en euros (voir docs/api-design.md).

Règles :
- entrée : une chaîne décimale ("12.50"), 2 décimales au plus, 10 chiffres au plus avant la
  virgule (comme NUMERIC(12,2) en base : au-delà, l'insertion échouerait en erreur 500).
  Les nombres JSON (12.5) sont refusés : un flottant est déjà imprécis avant d'arriver à l'API.
- sortie : toujours une chaîne à deux décimales ("12.50", "300.00", "-44.60"), jamais un nombre.
- en Python, la valeur reste un Decimal : les calculs se font en Decimal, jamais en float.

À utiliser dans les schémas de réponse avec un `response_model`. Sans schéma de réponse,
FastAPI renvoie un nombre JSON (12.5) et la règle n'est plus respectée.
"""

import re
from decimal import Decimal
from typing import Annotated, Any

from pydantic import BeforeValidator, Field, PlainSerializer, WithJsonSchema
from pydantic_core import PydanticCustomError


# Écriture décimale admise : chiffres 0-9, signe « - » facultatif, point et décimales facultatifs.
# Pydantic accepterait bien davantage (« 1e2 », « +5 », « 12. », « .5 », « 1_000 », des espaces,
# des chiffres d'autres alphabets) : ces écritures ne sont pas annoncées par le contrat de l'API.
_ECRITURE = re.compile(r"(-?)([0-9]+)(?:\.([0-9]+))?")


def _controler(valeur: Any, chiffres_max: int | None) -> Any:
    """Accepte une chaîne décimale (ou un Decimal construit en Python), refuse tout le reste.

    `chiffres_max` borne la partie entière d'un montant saisi ; `None` pour un montant calculé.
    """
    if isinstance(valeur, bool) or not isinstance(valeur, (str, Decimal)):
        raise ValueError("Le montant doit être une chaîne décimale.")
    if isinstance(valeur, str):
        trouve = _ECRITURE.fullmatch(valeur)
        if trouve is None:
            raise ValueError("Le montant doit être une chaîne décimale.")
        signe, entier, decimales = trouve.group(1), trouve.group(2), trouve.group(3) or ""
        # Les types d'erreur ci-dessous sont ceux de Pydantic : les gestionnaires leur associent
        # déjà les messages « Deux décimales maximum. » et « Valeur trop grande/petite. ».
        if len(decimales) > 2:
            raise PydanticCustomError("decimal_max_places", "Deux décimales au plus.")
        if chiffres_max is not None and len(entier) > chiffres_max:
            raise PydanticCustomError("greater_than" if signe else "less_than", "Valeur hors limites.")
    return valeur


def _exiger_chaine(valeur: Any) -> Any:
    """Montant saisi : au plus 10 chiffres avant la virgule (limite de NUMERIC(12,2))."""
    return _controler(valeur, 10)


def _exiger_chaine_calculee(valeur: Any) -> Any:
    """Montant calculé (somme, reste) : la même écriture, mais sans borne sur la taille."""
    return _controler(valeur, None)


# NUMERIC(12,2) accepte 10 chiffres avant la virgule : la valeur absolue doit rester sous 10^10.
# On borne la valeur plutôt que de compter les chiffres : Pydantic retire les zéros de fin
# avant de compter, donc "12345678901.00" passerait un contrôle max_digits=12.
LIMITE = Decimal("10000000000")


def _vers_chaine(valeur: Decimal) -> str:
    return f"{valeur:.2f}"


# Description OpenAPI : sans elle, Pydantic annonce « nombre ou chaîne » à l'entrée, ce qui est
# faux (un nombre JSON est refusé). Elle ne change rien au comportement, seulement à /docs.
_DESCRIPTION_ENTREE = (
    "Montant en euros, **chaîne décimale** à 2 décimales au plus et 10 chiffres au plus avant "
    "la virgule. Un nombre JSON (12.5) est refusé."
)
_SCHEMA_ENTREE = {
    "type": "string",
    "pattern": r"^[0-9]{1,10}(\.[0-9]{1,2})?$",
    "examples": ["12.50"],
    "description": _DESCRIPTION_ENTREE,
}
_SCHEMA_ENTREE_POSITIF = {
    **_SCHEMA_ENTREE,
    "description": _DESCRIPTION_ENTREE + " Strictement supérieur à 0.",
}
_SCHEMA_SORTIE = {
    "type": "string",
    "pattern": r"^-?[0-9]{1,10}\.[0-9]{2}$",
    "examples": ["12.50"],
    "description": "Montant en euros, chaîne décimale à exactement 2 décimales (jamais un nombre).",
}

# Montant quelconque (peut être négatif : par exemple le "reste" d'un budget dépassé).
Montant = Annotated[
    Decimal,
    BeforeValidator(_exiger_chaine),
    Field(decimal_places=2, gt=-LIMITE, lt=LIMITE),
    PlainSerializer(_vers_chaine, return_type=str, when_used="json"),
    WithJsonSchema(_SCHEMA_ENTREE, mode="validation"),
    WithJsonSchema(_SCHEMA_SORTIE, mode="serialization"),
]

# Montant strictement positif : montant d'une dépense, limite d'un budget.
MontantPositif = Annotated[Montant, Field(gt=0), WithJsonSchema(_SCHEMA_ENTREE_POSITIF, mode="validation")]

# Montant CALCULÉ par l'API (consommation et reste d'un budget) : c'est une somme de dépenses, qui peut
# dépasser les 10 chiffres d'un montant saisi (NUMERIC(12,2) ne borne que chaque ligne). Même écriture
# (chaîne à 2 décimales), mais sans borne sur la taille : sinon la réponse échouait en 500.
_SCHEMA_CALCULE = {
    "type": "string",
    "pattern": r"^-?[0-9]+\.[0-9]{2}$",
    "examples": ["19999999999.98"],
    "description": "Montant calculé en euros, chaîne décimale à exactement 2 décimales, sans borne de taille.",
}
MontantCalcule = Annotated[
    Decimal,
    BeforeValidator(_exiger_chaine_calculee),
    Field(decimal_places=2),
    PlainSerializer(_vers_chaine, return_type=str, when_used="json"),
    WithJsonSchema(_SCHEMA_CALCULE, mode="validation"),
    WithJsonSchema(_SCHEMA_CALCULE, mode="serialization"),
]
