import json

import pytest

from api.academic_disciplines import academic_disciplines_for


@pytest.fixture()
def solr_doc():
    doc = {}
    with open("tests/fixtures/academic_disciplines.json") as data:
        doc = json.load(data)
    return doc["facet_counts"]["facet_fields"]


@pytest.fixture()
def subject(solr_doc):
    return academic_disciplines_for(solr_doc)


def test_academic_disciplines_for_has_top_level(subject):
    assert subject[0].name == "Science"
    assert subject[0].count == 23875


def test_academic_disciplines_for_has_subdisciplines(subject):
    subdisciplines = subject[0].disciplines
    eng = subdisciplines[0]
    assert eng.name == "Chemical Engineering"
    assert eng.count == 2715

    chemistry = subdisciplines[1]

    assert chemistry.name == "Chemistry"
    assert chemistry.count == 4279

    org = chemistry.disciplines[0]
    assert org.name == "Organic Chemistry"
    assert org.count == 242

    phys = chemistry.disciplines[1]
    assert phys.name == "Physical Chemistry"
    assert phys.count == 284

    physics = subdisciplines[2]
    assert physics.name == "Physics"
    assert physics.count == 1497
