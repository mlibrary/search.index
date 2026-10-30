import pytest
import json
from api.services import S
from api.specialists import (
    fetchers,
    get_specialists,
)


@pytest.fixture()
def academic_discipline_data():
    with open("tests/fixtures/specialists/academic_discipline_response.json") as data:
        body = json.load(data)
    return body


def test_top_academic_disciplines(academic_discipline_data):
    subject = fetchers["catalog"].get_top_academic_disciplines(academic_discipline_data)

    assert subject == [
        {"discipline": "Science", "count": 40},
        {"discipline": "Biology", "count": 39},
        {"discipline": "Zoology", "count": 39},
        {"discipline": "Ecology\\ and\\ Evolutionary\\ Biology", "count": 39},
        {"discipline": "Humanities", "count": 31},
    ]


@pytest.fixture()
def specialist_data():
    with open("tests/fixtures/specialists/person.json") as data:
        body = json.load(data)
    return body


@pytest.fixture()
def specialist_response_data():
    with open("tests/fixtures/specialists/specialists_response.json") as data:
        body = json.load(data)
    return body


@pytest.mark.asyncio
async def test_get_specialists_for_catalog(
    academic_discipline_data, specialist_data, specialist_response_data, respx_mock
):
    respx_mock.get(f"{S.parser_url}/catalog/academic_disciplines").respond(
        200, json=academic_discipline_data
    )
    respx_mock.get(f"{S.website_solr_url}/solr/www.lib/select").respond(
        200, json=specialist_data
    )
    assert (
        await get_specialists(
            datastore="catalog",
            query_params={"query": "", "filters": [], "ht_search_only": False},
        )
        == specialist_response_data
    )


@pytest.mark.asyncio
async def test_get_specialists_for_onlinejournals(
    academic_discipline_data, specialist_data, specialist_response_data, respx_mock
):
    respx_mock.get(f"{S.parser_url}/onlinejournals/academic_disciplines").respond(
        200, json=academic_discipline_data
    )
    respx_mock.get(f"{S.website_solr_url}/solr/www.lib/select").respond(
        200, json=specialist_data
    )
    assert (
        await get_specialists(
            datastore="onlinejournals",
            query_params={"query": "", "filters": []},
        )
        == specialist_response_data
    )


def test_specialist_response(specialist_data):

    subject = fetchers["catalog"].specialist_response(specialist_data)

    assert subject == [
        {
            "name": "So And So",
            "uniqname": "soandso",
            "title": "Biological Sciences Librarian",
            "email": "soandso@umich.edu",
            "phone": "999-999-9999",
            "academic_disciplines": [
                "Genetics",
                "Molecular, Cellular and Developmental Biology",
                "Zoology",
                "Ecology and Evolutionary Biology",
                "Botany",
                "Biology",
            ],
        }
    ]


def test_specialist_response_where_keys_are_missing(specialist_data):
    specialist_data["response"]["docs"][0].pop("ssfield_phone")
    subject = fetchers["catalog"].specialist_response(specialist_data)

    assert subject[0]["phone"] is None


def test_website_solr_query_params():
    tads = [
        {"discipline": "Science", "count": 40},
        {"discipline": "Ecology\\ and\\ Evolutionary\\ Biology", "count": 39},
    ]

    query_params = {}

    subject = fetchers["catalog"].website_solr_query_params(
        top_academic_disciplines=tads, query_params=query_params
    )

    assert subject["q"] == "Science OR Ecology\\ and\\ Evolutionary\\ Biology"
    assert subject["fq"] == "+source:drupal-users +status:true"
    assert subject["bq"] == [
        "taxonomy_name:(Science)^40",
        "taxonomy_name:(Ecology\\ and\\ Evolutionary\\ Biology)^39",
    ]


def test_website_solr_query_params_handles_academic_discipline_fq():
    tads = [
        {"discipline": "Science", "count": 40},
    ]
    query_params = {
        "filters": [
            "academic_discipline:Ecology and Evolutionary Biology",
            "academic_discipline:Biology",
        ]
    }

    subject = fetchers["catalog"].website_solr_query_params(
        top_academic_disciplines=tads, query_params=query_params
    )

    assert (
        subject["fq"]
        == "+source:drupal-users +status:true +(taxonomy_name:(Ecology\\ and\\ Evolutionary\\ Biology AND Biology))"
    )
