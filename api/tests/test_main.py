import responses
import pytest
import json
from fastapi.testclient import TestClient
from httpx import Response
from api.main import app
from api.services import S


@pytest.fixture()
def solr_bib():
    bib = {}
    with open("tests/fixtures/land_birds_solr.json") as data:
        bib = json.load(data)
    return bib


@pytest.fixture()
def onlinejournals_solr_bib():
    bib = {}
    with open("tests/fixtures/onlinejournal_solr.json") as data:
        bib = json.load(data)
    return bib


@pytest.fixture()
def articles_doc():
    bib = {}
    with open("tests/fixtures/primo/article.json") as data:
        bib = json.load(data)
    return bib


@pytest.fixture()
def onlinejournals_results():
    bib = {}
    with open("tests/fixtures/results/page1.json") as data:
        bib = json.load(data)
    return bib


@pytest.fixture()
def client():
    yield TestClient(app)


@pytest.fixture()
def valid_mms_id():
    return "990008019700106381"


@pytest.fixture
def loan_data():
    return json.loads('{"total_record_count": 0}')


def test_get_catalog_record(client, valid_mms_id, solr_bib, loan_data, respx_mock):
    respx_mock.get(f"{S.alma_api_url}/bibs/{valid_mms_id}/loans").mock(
        Response(200, json=loan_data)
    )
    respx_mock.get(f"{S.solr_url}/solr/biblio/select").mock(
        Response(200, json=solr_bib)
    )
    with open("tests/fixtures/land_birds.json") as data:
        expected = json.load(data)

    response = client.get(f"/catalog/records/{valid_mms_id}")
    assert response.status_code == 200
    subject = response.json()
    for field in expected:
        assert subject[field] == expected[field]


def test_get_onlinejournals_record(
    client, valid_mms_id, onlinejournals_solr_bib, loan_data, respx_mock
):
    respx_mock.get(f"{S.solr_url}/solr/biblio/select").mock(
        Response(200, json=onlinejournals_solr_bib)
    )
    with open("tests/fixtures/onlinejournal.json") as data:
        expected = json.load(data)

    response = client.get(f"/onlinejournals/records/{valid_mms_id}")
    assert response.status_code == 200
    subject = response.json()

    for field in expected:
        assert subject[field] == expected[field]


def test_get_onlinejournals_results(
    client, valid_mms_id, onlinejournals_results, respx_mock
):
    respx_mock.get(f"{S.parser_url}/onlinejournals/search").mock(
        Response(
            200,
            json=onlinejournals_results,
        )
    )

    response = client.get("/onlinejournals/search", params={"query": "music"})
    assert response.status_code == 200
    subject = response.json()

    assert subject["records"][0] is not None


@responses.activate
def test_get_articles_record(client, articles_doc):
    responses.get(f"{S.primo_api_url}/search", json=articles_doc, status=200)

    response = client.get("/articles/records/some_id")
    assert response.status_code == 200
    subject = response.json()
    assert subject["id"] == "cdi_projectmuse_ebooks_9781400840458"
    assert subject["title"] == [
        {"text": "Banding Together: How Communities Create Genres in Popular Music"}
    ]
