"""Run with: .venv/Scripts/python -B test_sqlmodel.py

Exercise the configured PostgreSQL database without leaving test rows behind.
"""

from datetime import datetime, timedelta
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from main import app
from src.routers.sqlmodel_example import Hero, Team, get_engine, get_session


def check() -> None:
    prefix = f"check_{uuid4().hex}_"
    engine = get_engine()

    with TestClient(app) as client, engine.connect() as connection:
        transaction = connection.begin()

        def test_session():
            # Endpoint commits release a savepoint, never the outer transaction.
            with Session(
                bind=connection, join_transaction_mode="create_savepoint"
            ) as session:
                yield session

        previous_overrides = app.dependency_overrides.copy()
        app.dependency_overrides[get_session] = test_session

        def request(method: str, path: str, expected: int, **kwargs):
            response = client.request(method, f"/db{path}", **kwargs)
            assert response.status_code == expected, (
                method, path, response.status_code, response.text
            )
            return response

        try:
            assert request("GET", "/health", 200).json()["status"] == "ok"

            team = request(
                "POST", "/teams/", 201,
                json={
                    "name": prefix + "team",
                    "headquarters": "Test headquarters",
                    "heroes": [
                        {"name": prefix + "alpha", "secret_name": "Secret A", "age": 30},
                        {"name": prefix + "beta", "secret_name": "Secret B", "age": 20},
                    ],
                },
            ).json()
            team_id = team["id"]
            heroes = sorted(team["heroes"], key=lambda hero: hero["name"])
            alpha_id, beta_id = [hero["id"] for hero in heroes]
            assert len(heroes) == 2
            for hero in heroes:
                assert hero["team_id"] == team_id
                assert "secret_name" not in hero
                for field in ("created_at", "updated_at"):
                    stamp = datetime.fromisoformat(hero[field])
                    assert stamp.utcoffset() == timedelta(0)

            detail = request("GET", f"/heroes/{alpha_id}", 200).json()
            assert detail["team"]["id"] == team_id
            assert "secret_name" not in detail
            assert len(request("GET", f"/teams/{team_id}", 200).json()["heroes"]) == 2
            request("GET", "/teams/", 200)

            page = request(
                "GET", "/heroes/", 200,
                params={"q": prefix, "team_id": team_id, "sort_by": "age", "limit": 1},
            ).json()
            assert (page["total"], page["offset"], page["limit"]) == (2, 0, 1)
            assert page["items"][0]["id"] == beta_id
            assert "secret_name" not in page["items"][0]
            next_page = request(
                "GET", "/heroes/", 200,
                params={"q": prefix, "team_id": team_id, "sort_by": "age", "offset": 1, "limit": 1},
            ).json()
            assert next_page["items"][0]["id"] == alpha_id
            filtered = request(
                "GET", "/heroes/", 200,
                params={"q": prefix, "min_age": 25, "sort_by": "name", "descending": True},
            ).json()
            assert filtered["total"] == 1 and filtered["items"][0]["id"] == alpha_id
            descending = request(
                "GET", "/heroes/", 200,
                params={"q": prefix, "sort_by": "age", "descending": True},
            ).json()
            assert [hero["id"] for hero in descending["items"]] == [alpha_id, beta_id]

            for params in ({"offset": -1}, {"limit": 0}, {"limit": 101}, {"sort_by": "invalid"}):
                request("GET", "/heroes/", 422, params=params)
            request("POST", "/heroes/", 422, json={"name": prefix + "invalid", "secret_name": "X", "age": -1})
            request("POST", "/heroes/", 422, json={"name": "", "secret_name": "X"})
            request("POST", "/heroes/", 409, json={"name": heroes[0]["name"], "secret_name": "Duplicate"})
            request("POST", "/teams/", 409, json={"name": team["name"], "headquarters": "Duplicate"})

            # A failed second member must roll back both the first member and team.
            failed_team_name = prefix + "rolled_back_team"
            failed_hero_name = prefix + "rolled_back_hero"
            request(
                "POST", "/teams/", 409,
                json={
                    "name": failed_team_name,
                    "headquarters": "Must not persist",
                    "heroes": [
                        {"name": failed_hero_name, "secret_name": "New"},
                        {"name": heroes[0]["name"], "secret_name": "Duplicate"},
                    ],
                },
            )
            with Session(bind=connection, join_transaction_mode="create_savepoint") as session:
                assert session.exec(select(Team).where(Team.name == failed_team_name)).first() is None
                assert session.exec(select(Hero).where(Hero.name == failed_hero_name)).first() is None

            unchanged = request("PATCH", f"/heroes/{alpha_id}", 200, json={}).json()
            assert unchanged["name"] == heroes[0]["name"] and unchanged["age"] == 30
            request("PATCH", f"/heroes/{alpha_id}", 422, json={"name": None})
            request("PATCH", f"/heroes/{alpha_id}", 422, json={"secret_name": None})
            request("PATCH", f"/heroes/{alpha_id}", 409, json={"name": heroes[1]["name"]})
            updated = request(
                "PATCH", f"/heroes/{alpha_id}", 200,
                json={"age": None, "team_id": None, "secret_name": "Changed secret"},
            ).json()
            assert updated["age"] is None and updated["team_id"] is None
            assert "secret_name" not in updated
            assert datetime.fromisoformat(updated["updated_at"]) >= datetime.fromisoformat(heroes[0]["updated_at"])
            with Session(bind=connection, join_transaction_mode="create_savepoint") as session:
                assert session.get(Hero, alpha_id).secret_name == "Changed secret"
            request("PATCH", f"/heroes/{alpha_id}", 200, json={"team_id": team_id})

            renamed = request(
                "PATCH", f"/teams/{team_id}", 200,
                json={"name": prefix + "renamed_team", "headquarters": "New headquarters"},
            ).json()
            assert renamed["name"] == prefix + "renamed_team"
            assert renamed["headquarters"] == "New headquarters"
            request("PATCH", f"/teams/{team_id}", 422, json={"name": None})
            request("DELETE", f"/teams/{team_id}", 409)
            assert request("GET", f"/heroes/{beta_id}", 200).json()["team_id"] == team_id

            empty_team = request(
                "POST", "/teams/", 201,
                json={"name": prefix + "empty_team", "headquarters": "Temporary"},
            ).json()
            empty_team_id = empty_team["id"]
            assert request("DELETE", f"/teams/{empty_team_id}", 204).content == b""
            request("GET", f"/teams/{empty_team_id}", 404)
            request("PATCH", f"/teams/{empty_team_id}", 404, json={"headquarters": "Gone"})
            request("DELETE", f"/teams/{empty_team_id}", 404)
            request("POST", "/heroes/", 404, json={"name": prefix + "bad_team", "secret_name": "X", "team_id": empty_team_id})
            request("PATCH", f"/heroes/{alpha_id}", 404, json={"team_id": empty_team_id})

            solo = request(
                "POST", "/heroes/", 201,
                json={"name": prefix + "solo", "secret_name": "Solo secret"},
            ).json()
            assert solo["team_id"] is None and solo["age"] is None
            # Leave solo present so the final query also verifies outer rollback.
            for hero_id in (alpha_id, beta_id):
                assert request("DELETE", f"/heroes/{hero_id}", 204).content == b""
            request("GET", f"/heroes/{alpha_id}", 404)
            request("PATCH", f"/heroes/{alpha_id}", 404, json={"age": 20})
            request("DELETE", f"/heroes/{alpha_id}", 404)
            request("DELETE", f"/teams/{team_id}", 204)
        finally:
            app.dependency_overrides.clear()
            app.dependency_overrides.update(previous_overrides)
            transaction.rollback()

    with Session(engine) as session:
        assert session.exec(select(Team).where(Team.name.startswith(prefix))).first() is None
        assert session.exec(select(Hero).where(Hero.name.startswith(prefix))).first() is None
    print("SQLModel PostgreSQL checks passed; test rows rolled back.")


if __name__ == "__main__":
    check()
