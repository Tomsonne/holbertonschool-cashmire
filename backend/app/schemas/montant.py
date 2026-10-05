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

from decimal import Decimal
from typing import Annotated, Any

from pydantic import BeforeValidator, Field, PlainSerializer


def _exiger_chaine(valeur: Any) -> Any:
    """Accepte une chaîne (ou un Decimal construit en Python), refuse les nombres JSON."""
    if isinstance(valeur, bool) or not isinstance(valeur, (str, Decimal)):
        raise ValueError("Le montant doit être une chaîne décimale.")
    return valeur


# NUMERIC(12,2) accepte 10 chiffres avant la virgule : la valeur absolue doit rester sous 10^10.
# On borne la valeur plutôt que de compter les chiffres : Pydantic retire les zéros de fin
# avant de compter, donc "12345678901.00" passerait un contrôle max_digits=12.
LIMITE = Decimal("10000000000")


def _vers_chaine(valeur: Decimal) -> str:
    return f"{valeur:.2f}"


# Montant quelconque (peut être négatif : par exemple le "reste" d'un budget dépassé).
Montant = Annotated[
    Decimal,
    BeforeValidator(_exiger_chaine),
    Field(decimal_places=2, gt=-LIMITE, lt=LIMITE),
    PlainSerializer(_vers_chaine, return_type=str, when_used="json"),
]

# Montant strictement positif : montant d'une dépense, limite d'un budget.
MontantPositif = Annotated[Montant, Field(gt=0)]
