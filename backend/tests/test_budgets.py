from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.securite import NOM_COOKIE_JWT
from app.db.session import engine, get_db
from app.main import app
from app.models.budget import Budget
from app.models.categorie import Categorie
from app.models.depense import Depense
from app.models.utilisateur import Utilisateur
from app.services.budgets import presenter_budget


def jeton_pour(utilisateur_id, duree_minutes=30):
    maintenant = datetime.now(timezone.utc)
    return jwt.encode(
        {"sub": str(utilisateur_id), "iat": maintenant, "exp": maintenant + timedelta(minutes=duree_minutes)},
        settings.jwt_secret,
        algorithm="HS256",
    )


@pytest.fixture(autouse=True)
def utilisateur_budget(client, db_session):
    utilisateur = Utilisateur(
        email=f"budget-{uuid4()}@example.invalid",
        mot_de_passe_hache="hash-factice",
        nom_affichage="Budget",
    )
    db_session.add(utilisateur)
    db_session.commit()
    client.cookies.set(NOM_COOKIE_JWT, jeton_pour(utilisateur.id))
    return utilisateur


def test_creer_budget_persiste_et_convertit_le_mois(client, db_session, utilisateur_budget):
    categorie = db_session.scalar(select(Categorie).where(Categorie.nom == "Alimentation"))
    if categorie is None:
        categorie = Categorie(id=uuid4(), nom=f"Test {uuid4()}")
        db_session.add(categorie)
        db_session.flush()

    response = client.post("/api/budgets", json={
        "categorie_id": str(categorie.id), "montant_limite": "125.40", "mois": "2026-10"
    })
    assert response.status_code == 201
    assert response.json()["montant_limite"] == "125.40"
    assert response.json()["depense"] == "0.00"
    assert response.json()["mois"] == "2026-10"
    assert response.json()["seuil_alerte_pct"] == 80

    budget = db_session.get(Budget, response.json()["id"])
    assert budget.utilisateur_id == utilisateur_budget.id
    assert budget.periode_mois.isoformat() == "2026-10-01"
    assert budget.montant_limite == Decimal("125.40")


@pytest.mark.parametrize(("payload", "champ"), [
    ({"montant_limite": "0"}, "montant_limite"),
    ({"montant_limite": "-1"}, "montant_limite"),
    ({"montant_limite": "12.345"}, "montant_limite"),
    ({"montant_limite": 12.5}, "montant_limite"),
    ({"mois": "2026-13"}, "mois"),
    ({"mois": "2026-2"}, "mois"),
    ({"seuil_alerte_pct": 0}, "seuil_alerte_pct"),
    ({"seuil_alerte_pct": 101}, "seuil_alerte_pct"),
    ({"seuil_alerte_pct": 80.5}, "seuil_alerte_pct"),
])
def test_donnees_invalides_repondent_422(client, payload, champ):
    corps = {"categorie_id": "11111111-1111-4111-8111-111111111111", "montant_limite": "10.00", "mois": "2026-10"}
    corps.update(payload)
    response = client.post("/api/budgets", json=corps)
    assert response.status_code == 422
    assert response.json()["erreur"]["code"] == "donnees_invalides"
    assert champ in response.json()["erreur"]["champs"]


def test_doublon_repond_409(client, db_session):
    categorie = Categorie(id=uuid4(), nom=f"Doublon {uuid4()}")
    db_session.add(categorie)
    db_session.flush()
    corps = {"categorie_id": str(categorie.id), "montant_limite": "60.00", "mois": "2026-11"}
    assert client.post("/api/budgets", json=corps).status_code == 201
    response = client.post("/api/budgets", json=corps)
    assert response.status_code == 409
    assert response.json()["erreur"]["code"] == "conflit"


def test_categorie_inconnue_repond_404(client):
    response = client.post("/api/budgets", json={
        "categorie_id": str(uuid4()), "montant_limite": "60.00", "mois": "2026-11"
    })
    assert response.status_code == 404
    assert response.json()["erreur"]["code"] == "introuvable"


def test_requetes_simultanees_ne_creent_qu_un_budget(client, base_propre):
    with Session(engine) as session:
        categorie = session.scalar(select(Categorie).limit(1))
        categorie_id = categorie.id
    mois = "2026-12"

    def session_par_requete():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_db] = session_par_requete
    try:
        jeton = client.cookies.get(NOM_COOKIE_JWT)

        def creer_budget_simultane(_):
            client_concurrent = TestClient(app, headers={"Origin": "http://localhost:5173"})
            client_concurrent.cookies.set(NOM_COOKIE_JWT, jeton)
            return client_concurrent.post("/api/budgets", json={
                "categorie_id": str(categorie_id), "montant_limite": "42.00", "mois": mois
            }).status_code

        with ThreadPoolExecutor(max_workers=2) as pool:
            statuts = list(pool.map(creer_budget_simultane, range(2)))
        assert sorted(statuts) == [201, 409]
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_cookie_valide_autorise_les_budgets_en_production(client, monkeypatch):
    monkeypatch.setattr(settings, "environment", "production")
    assert client.get("/api/budgets").status_code == 200


@pytest.mark.parametrize(("methode", "url", "corps"), [
    ("GET", "/api/budgets", None),
    ("POST", "/api/budgets", {
        "categorie_id": "11111111-1111-4111-8111-111111111111",
        "montant_limite": "10.00", "mois": "2026-10",
    }),
    ("GET", "/api/budgets/11111111-1111-4111-8111-111111111111", None),
    ("PATCH", "/api/budgets/11111111-1111-4111-8111-111111111111", {"montant_limite": "10.00"}),
    ("DELETE", "/api/budgets/11111111-1111-4111-8111-111111111111", None),
])
@pytest.mark.parametrize("cookie", ["absent", "invalide", "expire"])
def test_routes_budgets_exigent_un_cookie_valide(client, utilisateur_budget, methode, url, corps, cookie):
    client.cookies.clear()
    if cookie == "invalide":
        client.cookies.set(NOM_COOKIE_JWT, "jeton-invalide")
    elif cookie == "expire":
        client.cookies.set(NOM_COOKIE_JWT, jeton_pour(utilisateur_budget.id, duree_minutes=-1))
    reponse = client.request(methode, url, json=corps)
    assert reponse.status_code == 401
    assert reponse.json() == {"erreur": {"code": "non_authentifie", "message": "Authentification requise."}}


def test_erreur_bdd_inconnue_est_relancee_apres_rollback(client, db_session, monkeypatch):
    categorie = db_session.scalar(select(Categorie).where(Categorie.nom == "Alimentation"))
    rollback_original = db_session.rollback
    rollbacks = []

    def rollback_verifie():
        rollbacks.append(True)
        rollback_original()

    def commit_invalide():
        raise IntegrityError("INSERT budgets", {}, Exception("contrainte inconnue"))

    monkeypatch.setattr(db_session, "rollback", rollback_verifie)
    monkeypatch.setattr(db_session, "commit", commit_invalide)
    reponse = client.post("/api/budgets", json={
        "categorie_id": str(categorie.id), "montant_limite": "10.00", "mois": "2026-10"
    })
    assert reponse.status_code == 500
    assert reponse.json() == {
        "erreur": {"code": "erreur_interne", "message": "Une erreur interne est survenue."}
    }
    assert rollbacks == [True]
    assert "contrainte inconnue" not in reponse.text


@pytest.mark.parametrize(("montant", "pourcentage", "statut", "reste"), [
    ("799.99", Decimal("80.00"), "ok", "200.01"),
    ("800.00", Decimal("80.00"), "attention", "200.00"),
    ("1000.00", Decimal("100.00"), "attention", "0.00"),
    ("1000.01", Decimal("100.00"), "depasse", "-0.01"),
])
def test_consommation_et_statut_aux_bornes(client, db_session, montant, pourcentage, statut, reste):
    categorie = db_session.scalar(select(Categorie).where(Categorie.nom == "Alimentation"))
    reponse = client.post("/api/budgets", json={
        "categorie_id": str(categorie.id), "montant_limite": "1000.00", "mois": "2026-10"
    })
    assert reponse.status_code == 201
    budget = db_session.get(Budget, reponse.json()["id"])
    assert reponse.json()["depense"] == "0.00"
    assert reponse.json()["reste"] == "1000.00"
    assert isinstance(reponse.json()["pourcentage"], (int, float))
    assert Decimal(str(reponse.json()["pourcentage"])) == 0
    assert reponse.json()["statut"] == "ok"

    db_session.add(Depense(
        utilisateur_id=budget.utilisateur_id, categorie_id=categorie.id,
        montant=Decimal(montant), date_depense=date(2026, 10, 15), libelle="Test",
    ))
    db_session.flush()
    resultat = presenter_budget(db_session, budget, categorie)
    assert resultat.depense == Decimal(montant)
    assert resultat.reste == Decimal(reste)
    assert resultat.pourcentage == pourcentage
    assert resultat.statut == statut


def test_consommation_filtre_utilisateur_categorie_et_mois_et_suit_les_depenses(client, db_session):
    categorie = db_session.scalar(select(Categorie).where(Categorie.nom == "Alimentation"))
    autre_categorie = db_session.scalar(select(Categorie).where(Categorie.nom == "Transport"))
    reponse = client.post("/api/budgets", json={
        "categorie_id": str(categorie.id), "montant_limite": "100.00", "mois": "2026-12"
    })
    assert reponse.status_code == 201
    budget = db_session.get(Budget, reponse.json()["id"])
    autre_utilisateur = Utilisateur(
        email=f"autre-{uuid4()}@example.invalid", mot_de_passe_hache="inutilisable", nom_affichage="Autre"
    )
    db_session.add(autre_utilisateur)
    db_session.flush()
    depense = Depense(
        utilisateur_id=budget.utilisateur_id, categorie_id=categorie.id,
        montant=Decimal("25.00"), date_depense=date(2026, 12, 31), libelle="Incluse",
    )
    db_session.add_all([
        depense,
        Depense(utilisateur_id=budget.utilisateur_id, categorie_id=autre_categorie.id,
                montant=Decimal("12.00"), date_depense=date(2026, 12, 15), libelle="Autre catégorie"),
        Depense(utilisateur_id=budget.utilisateur_id, categorie_id=categorie.id,
                montant=Decimal("13.00"), date_depense=date(2027, 1, 1), libelle="Autre mois"),
        Depense(utilisateur_id=autre_utilisateur.id, categorie_id=categorie.id,
                montant=Decimal("14.00"), date_depense=date(2026, 12, 15), libelle="Autre utilisateur"),
    ])
    db_session.flush()
    assert presenter_budget(db_session, budget, categorie).depense == Decimal("25.00")

    depense.montant = Decimal("30.00")
    db_session.flush()
    assert presenter_budget(db_session, budget, categorie).depense == Decimal("30.00")

    db_session.delete(depense)
    db_session.flush()
    resultat = presenter_budget(db_session, budget, categorie)
    assert resultat.depense == Decimal("0.00")
    assert resultat.pourcentage == Decimal("0.00")


def test_liste_budgets_vide(client):
    reponse = client.get("/api/budgets")
    assert reponse.status_code == 200
    assert reponse.json() == []


def test_liste_filtre_mois_et_detail_avec_consommation_actualisee(client, db_session):
    categorie = db_session.scalar(select(Categorie).where(Categorie.nom == "Alimentation"))
    autre_categorie = db_session.scalar(select(Categorie).where(Categorie.nom == "Transport"))
    octobre = client.post("/api/budgets", json={
        "categorie_id": str(categorie.id), "montant_limite": "100.00", "mois": "2026-10"
    }).json()
    novembre = client.post("/api/budgets", json={
        "categorie_id": str(autre_categorie.id), "montant_limite": "50.00", "mois": "2026-11"
    }).json()
    budget = db_session.get(Budget, octobre["id"])
    depense = Depense(
        utilisateur_id=budget.utilisateur_id, categorie_id=categorie.id,
        montant=Decimal("80.00"), date_depense=date(2026, 10, 12), libelle="Test",
    )
    db_session.add(depense)
    db_session.flush()

    liste = client.get("/api/budgets")
    assert liste.status_code == 200
    assert {element["id"] for element in liste.json()} == {octobre["id"], novembre["id"]}
    filtre = client.get("/api/budgets?mois=2026-10")
    assert filtre.status_code == 200
    assert len(filtre.json()) == 1
    assert filtre.json()[0]["id"] == octobre["id"]
    assert client.get("/api/budgets?mois=2026-09").json() == []

    detail = client.get(f"/api/budgets/{octobre['id']}")
    assert detail.status_code == 200
    assert detail.json() == {
        "id": octobre["id"], "categorie": {"id": str(categorie.id), "nom": categorie.nom},
        "mois": "2026-10", "montant_limite": "100.00", "depense": "80.00",
        "reste": "20.00", "pourcentage": 80.0, "seuil_alerte_pct": 80,
        "statut": "attention",
    }
    assert client.get(f"/api/budgets/{novembre['id']}").json()["depense"] == "0.00"

    depense.montant = Decimal("110.00")
    db_session.flush()
    actualise = client.get(f"/api/budgets/{octobre['id']}").json()
    assert (actualise["depense"], actualise["reste"], actualise["statut"]) == (
        "110.00", "-10.00", "depasse"
    )
    db_session.delete(depense)
    db_session.flush()
    assert client.get(f"/api/budgets/{octobre['id']}").json()["depense"] == "0.00"


def test_consultation_isole_les_budgets_par_utilisateur(client, db_session):
    categorie = db_session.scalar(select(Categorie).where(Categorie.nom == "Alimentation"))
    autre_utilisateur = Utilisateur(
        email=f"etranger-{uuid4()}@example.invalid", mot_de_passe_hache="inutilisable", nom_affichage="Autre"
    )
    db_session.add(autre_utilisateur)
    db_session.flush()
    budget_etranger = Budget(
        utilisateur_id=autre_utilisateur.id, categorie_id=categorie.id,
        montant_limite=Decimal("100.00"), periode_mois=date(2026, 10, 1), seuil_alerte_pct=80,
    )
    db_session.add(budget_etranger)
    db_session.flush()

    assert client.get("/api/budgets").json() == []
    for budget_id in (budget_etranger.id, uuid4()):
        reponse = client.get(f"/api/budgets/{budget_id}")
        assert reponse.status_code == 404
        assert reponse.json()["erreur"]["code"] == "introuvable"


@pytest.mark.parametrize("mois", ["2026-2", "2026-13", "0000-01", "2026-02-01", "xyz"])
def test_filtre_mois_invalide_repond_422(client, mois):
    reponse = client.get("/api/budgets", params={"mois": mois})
    assert reponse.status_code == 422
    assert reponse.json()["erreur"]["code"] == "donnees_invalides"


def test_identifiant_budget_invalide_repond_422(client):
    reponse = client.get("/api/budgets/pas-un-uuid")
    assert reponse.status_code == 422
    assert reponse.json()["erreur"]["code"] == "donnees_invalides"


def test_modifier_budget_revalide_et_recalcule_la_consommation(client, db_session):
    categorie = db_session.scalar(select(Categorie).where(Categorie.nom == "Alimentation"))
    creation = client.post("/api/budgets", json={
        "categorie_id": str(categorie.id), "montant_limite": "100.00", "mois": "2026-10"
    })
    assert creation.status_code == 201
    budget_id = creation.json()["id"]
    budget = db_session.get(Budget, budget_id)
    budget.date_modification = datetime(2020, 1, 1, tzinfo=timezone.utc)
    db_session.add(Depense(
        utilisateur_id=budget.utilisateur_id, categorie_id=categorie.id,
        montant=Decimal("90.00"), date_depense=date(2026, 10, 12), libelle="Test",
    ))
    db_session.flush()

    reponse = client.patch(f"/api/budgets/{budget_id}", json={"montant_limite": "120.00"})
    assert reponse.status_code == 200
    assert reponse.json()["montant_limite"] == "120.00"
    assert reponse.json()["depense"] == "90.00"
    assert reponse.json()["reste"] == "30.00"
    assert reponse.json()["pourcentage"] == 75.0
    assert reponse.json()["seuil_alerte_pct"] == 80
    assert reponse.json()["statut"] == "ok"
    assert db_session.get(Budget, budget_id).date_modification > datetime(2020, 1, 1, tzinfo=timezone.utc)

    reponse = client.patch(f"/api/budgets/{budget_id}", json={"seuil_alerte_pct": 70})
    assert reponse.status_code == 200
    assert reponse.json()["montant_limite"] == "120.00"
    assert reponse.json()["statut"] == "attention"
    assert reponse.json()["seuil_alerte_pct"] == 70

    reponse = client.patch(f"/api/budgets/{budget_id}", json={
        "montant_limite": "80.00", "seuil_alerte_pct": 90,
    })
    assert reponse.status_code == 200
    assert reponse.json()["reste"] == "-10.00"
    assert reponse.json()["statut"] == "depasse"


@pytest.mark.parametrize("corps", [
    {}, {"montant_limite": "0"}, {"montant_limite": "-1"},
    {"montant_limite": "12.345"}, {"montant_limite": 12.5},
    {"montant_limite": "10000000000.00"}, {"montant_limite": None},
    {"seuil_alerte_pct": 0}, {"seuil_alerte_pct": 101},
    {"seuil_alerte_pct": 80.5}, {"seuil_alerte_pct": "80"},
    {"seuil_alerte_pct": None}, {"mois": "2026-11"},
])
def test_modification_invalide_repond_422_sans_changer_le_budget(client, db_session, corps):
    categorie = db_session.scalar(select(Categorie).where(Categorie.nom == "Alimentation"))
    creation = client.post("/api/budgets", json={
        "categorie_id": str(categorie.id), "montant_limite": "100.00", "mois": "2026-10"
    })
    budget_id = creation.json()["id"]
    reponse = client.patch(f"/api/budgets/{budget_id}", json=corps)
    assert reponse.status_code == 422
    assert reponse.json()["erreur"]["code"] == "donnees_invalides"
    db_session.expire_all()
    budget = db_session.get(Budget, budget_id)
    assert budget.montant_limite == Decimal("100.00")
    assert budget.seuil_alerte_pct == 80
    assert budget.periode_mois == date(2026, 10, 1)


def test_supprimer_budget_conserve_les_depenses(client, db_session):
    categorie = db_session.scalar(select(Categorie).where(Categorie.nom == "Alimentation"))
    creation = client.post("/api/budgets", json={
        "categorie_id": str(categorie.id), "montant_limite": "100.00", "mois": "2026-10"
    })
    budget_id = creation.json()["id"]
    budget = db_session.get(Budget, budget_id)
    depense = Depense(
        utilisateur_id=budget.utilisateur_id, categorie_id=categorie.id,
        montant=Decimal("25.00"), date_depense=date(2026, 10, 12), libelle="Conservée",
    )
    db_session.add(depense)
    db_session.flush()
    depense_id = depense.id

    reponse = client.delete(f"/api/budgets/{budget_id}")
    assert reponse.status_code == 204
    assert reponse.content == b""
    assert db_session.get(Budget, budget_id) is None
    assert db_session.get(Depense, depense_id).montant == Decimal("25.00")
    assert client.get(f"/api/budgets/{budget_id}").status_code == 404


def test_modification_et_suppression_isolent_les_utilisateurs(client, db_session):
    categorie = db_session.scalar(select(Categorie).where(Categorie.nom == "Alimentation"))
    autre_utilisateur = Utilisateur(
        email=f"etranger-{uuid4()}@example.invalid", mot_de_passe_hache="inutilisable", nom_affichage="Autre"
    )
    db_session.add(autre_utilisateur)
    db_session.flush()
    budget_etranger = Budget(
        utilisateur_id=autre_utilisateur.id, categorie_id=categorie.id,
        montant_limite=Decimal("100.00"), periode_mois=date(2026, 10, 1), seuil_alerte_pct=80,
    )
    db_session.add(budget_etranger)
    db_session.flush()

    for budget_id in (budget_etranger.id, uuid4()):
        for reponse in (
            client.patch(f"/api/budgets/{budget_id}", json={"montant_limite": "10.00"}),
            client.delete(f"/api/budgets/{budget_id}"),
        ):
            assert reponse.status_code == 404
            assert reponse.json()["erreur"]["code"] == "introuvable"
    assert db_session.get(Budget, budget_etranger.id).montant_limite == Decimal("100.00")


def test_somme_decimale_et_json_apres_changement_de_date_et_categorie(client, db_session):
    alimentation = db_session.scalar(select(Categorie).where(Categorie.nom == "Alimentation"))
    transport = db_session.scalar(select(Categorie).where(Categorie.nom == "Transport"))
    premier = client.post("/api/budgets", json={
        "categorie_id": str(alimentation.id), "montant_limite": "1.00", "mois": "2026-10"
    }).json()
    second = client.post("/api/budgets", json={
        "categorie_id": str(transport.id), "montant_limite": "1.00", "mois": "2026-10"
    }).json()
    budget = db_session.get(Budget, premier["id"])
    depense = Depense(
        utilisateur_id=budget.utilisateur_id, categorie_id=alimentation.id,
        montant=Decimal("0.10"), date_depense=date(2026, 10, 31), libelle="Mobile",
    )
    db_session.add_all([depense, Depense(
        utilisateur_id=budget.utilisateur_id, categorie_id=alimentation.id,
        montant=Decimal("0.20"), date_depense=date(2026, 10, 1), libelle="Autre",
    )])
    db_session.commit()

    def depensee(budget_id):
        reponse = client.get(f"/api/budgets/{budget_id}")
        assert reponse.status_code == 200
        return reponse.json()

    assert (depensee(premier["id"])["depense"], depensee(premier["id"])["reste"]) == ("0.30", "0.70")
    depense.date_depense = date(2026, 11, 1)
    db_session.commit()
    assert depensee(premier["id"])["depense"] == "0.20"
    depense.date_depense = date(2026, 10, 31)
    depense.categorie_id = transport.id
    depense.montant = Decimal("0.35")
    db_session.commit()
    assert depensee(premier["id"])["depense"] == "0.20"
    assert (depensee(second["id"])["depense"], depensee(second["id"])["pourcentage"]) == ("0.35", 35.0)
    db_session.delete(depense)
    db_session.commit()
    assert depensee(second["id"])["depense"] == "0.00"


def test_unicite_budget_portee_par_utilisateur_categorie_et_mois(client, db_session):
    alimentation = db_session.scalar(select(Categorie).where(Categorie.nom == "Alimentation"))
    transport = db_session.scalar(select(Categorie).where(Categorie.nom == "Transport"))
    corps = {"categorie_id": str(alimentation.id), "montant_limite": "10.00", "mois": "2026-10"}
    assert client.post("/api/budgets", json=corps).status_code == 201
    assert client.post("/api/budgets", json=corps).status_code == 409
    assert client.post("/api/budgets", json={**corps, "mois": "2026-11"}).status_code == 201
    assert client.post("/api/budgets", json={**corps, "categorie_id": str(transport.id)}).status_code == 201
    autre = Utilisateur(
        email=f"autre-{uuid4()}@example.invalid", mot_de_passe_hache="inutilisable", nom_affichage="Autre"
    )
    db_session.add(autre)
    db_session.commit()
    db_session.add(Budget(
        utilisateur_id=autre.id, categorie_id=alimentation.id,
        montant_limite=Decimal("10.00"), periode_mois=date(2026, 10, 1), seuil_alerte_pct=80,
    ))
    db_session.commit()


def test_fin_fevrier_bissextile_et_mois_suivant(client, db_session):
    categorie = db_session.scalar(select(Categorie).where(Categorie.nom == "Alimentation"))
    cree = client.post("/api/budgets", json={
        "categorie_id": str(categorie.id), "montant_limite": "100.00", "mois": "2024-02"
    })
    assert cree.status_code == 201
    budget = db_session.get(Budget, cree.json()["id"])
    for jour, montant in [(date(2024, 2, 29), "7.25"), (date(2024, 3, 1), "10.00")]:
        db_session.add(Depense(
            utilisateur_id=budget.utilisateur_id, categorie_id=categorie.id,
            montant=Decimal(montant), date_depense=jour, libelle="Frontière",
        ))
    db_session.commit()
    reponse = client.get(f"/api/budgets/{budget.id}")
    assert reponse.status_code == 200
    assert reponse.json()["depense"] == "7.25"


def test_deux_vrais_cookies_isolent_budgets_et_depenses_et_preservent_les_depenses(
    client, db_session
):
    from fastapi.testclient import TestClient
    from app.main import app

    categorie = db_session.scalar(select(Categorie).where(Categorie.nom == "Alimentation"))
    autre_client = TestClient(app, raise_server_exceptions=False)
    sans_cookie = TestClient(app, raise_server_exceptions=False)
    client.cookies.clear()  # la fixture de ce module pose un JWT factice sur ce client
    mois = date.today().strftime("%Y-%m")
    corps_budget = {
        "categorie_id": str(categorie.id), "montant_limite": "10.00", "mois": mois
    }
    assert sans_cookie.get("/api/budgets").status_code == 401
    assert sans_cookie.post("/api/depenses", json={}).status_code == 401

    for utilisateur_client, email in (
        (client, "alice@example.com"), (autre_client, "bob@example.com"),
    ):
        identifiants = {"email": email, "mot_de_passe": "mot-de-passe-de-test"}
        assert utilisateur_client.post("/api/authentification/inscription", json={
            **identifiants, "nom_affichage": "Test",
        }).status_code == 201
        connexion = utilisateur_client.post("/api/authentification/connexion", json=identifiants)
        assert connexion.status_code == 200
        assert utilisateur_client.cookies.get("access_token")

    budget_alice = client.post("/api/budgets", json=corps_budget)
    budget_bob = autre_client.post("/api/budgets", json=corps_budget)
    assert (budget_alice.status_code, budget_bob.status_code) == (201, 201)
    id_alice, id_bob = budget_alice.json()["id"], budget_bob.json()["id"]
    assert [item["id"] for item in client.get("/api/budgets").json()] == [id_alice]
    assert [item["id"] for item in autre_client.get("/api/budgets").json()] == [id_bob]
    assert client.get(f"/api/budgets/{id_bob}").status_code == 404
    assert autre_client.patch(f"/api/budgets/{id_alice}", json={
        "montant_limite": "1.00"
    }).status_code == 404

    depense_alice = client.post("/api/depenses", json={
        "categorie_id": str(categorie.id), "montant": "3.25", "libelle": "Courses",
        "date_depense": date.today().isoformat(),
    })
    assert depense_alice.status_code == 201
    assert client.get(f"/api/budgets/{id_alice}").json()["depense"] == "3.25"
    assert autre_client.get(f"/api/budgets/{id_bob}").json()["depense"] == "0.00"
    depense_id = depense_alice.json()["id"]
    assert client.delete(f"/api/budgets/{id_alice}").status_code == 204
    assert db_session.get(Depense, depense_id).montant == Decimal("3.25")
