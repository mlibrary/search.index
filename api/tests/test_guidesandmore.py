import json

import pytest

from api.guidesandmore import CSL, decode_id, encode_id


@pytest.fixture()
def solr_bib():
    bib = {}
    with open("tests/fixtures/record/guidesandmore_record.json") as data:
        bib = json.load(data)
    return bib["response"]["docs"][0]


def test_csl_output(solr_bib):
    subject = CSL(solr_doc=solr_bib)
    assert (
        subject.id
        == "https://blogs.lib.umich.edu/eaten-grue/video-game-music-non-music-majors"
    )
    assert (
        subject.url
        == "https://blogs.lib.umich.edu/eaten-grue/video-game-music-non-music-majors"
    )
    assert subject.type == "post-weblog"
    assert subject.title == "Video Game Music for Non-Music Majors"
    assert subject.issued == {"date_parts": [[2016, 3, 22]]}
    assert subject.author == [{"family": "Card", "given": "Emily C."}]


def test_csl_handles_multiple_authors(solr_bib):
    solr_bib["ssfield_author"] = "Emily C. Card, Julian Tutor"
    subject = CSL(solr_doc=solr_bib)
    assert subject.author == [
        {"family": "Card", "given": "Emily C."},
        {"family": "Tutor", "given": "Julian"},
    ]


def test_encode_id_removes_padding():
    subject = encode_id("https://default.invalid/fake-it-%E2%80%98til-a")
    assert subject == "aHR0cHM6Ly9kZWZhdWx0LmludmFsaWQvZmFrZS1pdC0lRTIlODAlOTh0aWwtYQ"


def test_decode_id():
    subject = decode_id(
        "aHR0cHM6Ly9kZWZhdWx0LmludmFsaWQvZmFrZS1pdC0lRTIlODAlOTh0aWwtYQ"
    )
    assert subject == "https://default.invalid/fake-it-%E2%80%98til-a"


def test_decode_id_handle_other_padding():
    assert decode_id("YmxhaGg") == "blahh"
    assert decode_id("Ymxh") == "bla"
