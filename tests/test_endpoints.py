from pathlib import Path
from typing import Generator
from unittest.mock import patch
from uuid import uuid4
from fastapi import status
import alembic.command
import alembic.config
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlmodel import select

from app.core.db import get_database_session
from app.main import app
from app.models.organisation import Organisation
from app.models.location import Location, CreateLocation

_ALEMBIC_INI_PATH = Path(__file__).parent.parent / "alembic.ini"

@pytest.fixture()
def test_client() -> TestClient:
    return TestClient(app)

@pytest.fixture(autouse=True)
def apply_alembic_migrations() -> Generator[None, None, None]:
    # Creates test database per test function
    test_db_file_name = f"test_{uuid4()}.db"
    database_path = Path(test_db_file_name)
    try:
        test_db_url = f"sqlite:///{test_db_file_name}"
        alembic_cfg = alembic.config.Config(_ALEMBIC_INI_PATH)
        alembic_cfg.attributes["sqlalchemy_url"] = test_db_url
        alembic.command.upgrade(alembic_cfg, "head")
        test_engine = create_engine(test_db_url, echo=True)
        with patch("app.core.db.get_engine") as mock_engine:
            mock_engine.return_value = test_engine
            yield
    finally:
        database_path.unlink(missing_ok=True)


def test_organisation_endpoints(test_client: TestClient) -> None:
    list_of_organisation_names_to_create = ["organisation_a", "organisation_b", "organisation_c"]

    # Validate that organisations do not exist in database
    with get_database_session() as database_session:
        query = select(Organisation)
        organisations_before = database_session.exec(query).all()
        database_session.expunge_all()
    assert len(organisations_before) == 0

    # Create organisations
    for organisation_name in list_of_organisation_names_to_create:
        response = test_client.post("/api/organisations/create", json={"name": organisation_name})
        assert response.status_code == status.HTTP_200_OK

    # Validate that organisations exist in database
    with get_database_session() as database_session:
        query = select(Organisation)
        organisations_after = database_session.exec(query).all()
        database_session.expunge_all()
    created_organisation_names = set(organisation.name for organisation in organisations_after)
    assert created_organisation_names == set(list_of_organisation_names_to_create)

    # Validate that created organisations can be retried via API
    response = test_client.get("/api/organisations")
    organisations = set(organisation["name"] for organisation in response.json())
    assert  set(organisations) == created_organisation_names
    
    
    
def test_location_endpoints(test_client: TestClient) -> None:

    # Create org
    org_response = test_client.post("/api/organisations/create", json={"name": "Test Organisation"})
    assert org_response.status_code == status.HTTP_200_OK
    organisation_id = org_response.json()["id"]


    # Test 1: No locs for org
    with get_database_session() as db_session:
        locations_before = db_session.exec(select(Location).where(Location.organisation_id == organisation_id)).all()
        db_session.expunge_all()
    assert len(locations_before) == 0


    
    # Arrange locs
    locations_to_create = [
        {"organisation_id": organisation_id, "location_name": "test 1", "longitude": 123.456, "latitude": 78.910},
        {"organisation_id": organisation_id, "location_name": "test 2", "longitude": 223.456, "latitude": 88.910}
    ]

    # Test 2: Validate create locs
    for location_data in locations_to_create:
        response = test_client.post("/api/locations/create", json=location_data)
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["location_name"] == location_data["location_name"]
        

        
    # Test 3: Validate 404 for no org while creating loc
    response = test_client.post("/api/locations/create", json={
        "organisation_id": 5,
        "location_name": "does not exists",
        "longitude": 0,
        "latitude": 0
    })
    assert response.status_code == status.HTTP_404_NOT_FOUND

    
    # Test 4: Validate locations exist in the database
    with get_database_session() as db_session:
        locs = db_session.exec(select(Location).where(Location.organisation_id == organisation_id)).all()
        db_session.expunge_all()
    created_location_names = set(loc.location_name for loc in locs)
    assert created_location_names == set(loc["location_name"] for loc in locations_to_create)


    # Test 5: Validate length of the retrieved locs for org
    response = test_client.get(f"/api/locations/{organisation_id}")
    assert response.status_code == status.HTTP_200_OK
    retrieved_locations = response.json()
    assert len(retrieved_locations) == len(locations_to_create)


    retrieved_location_names = set(location["location_name"] for location in retrieved_locations)
    assert retrieved_location_names == created_location_names

    # Test 6: Non existent org
    response = test_client.get("/api/locations/9999")
    assert response.status_code == status.HTTP_404_NOT_FOUND

    

    # Test 7: Retrieve with bounding box
    bounding_box = {
        'bounding_box': [
            78.900, 
            123.450,
            78.920, 
            123.460 
        ]
    }
    response = test_client.get(f"/api/locations/{organisation_id}", params=bounding_box)
    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()) == 1



    