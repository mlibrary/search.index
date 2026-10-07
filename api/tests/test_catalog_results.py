import pytest
import json
from api.catalog_results import Filter, FilterQuery, Results


@pytest.fixture()
def solr_results():
    with open("tests/fixtures/results/page1.json") as data:
        bib = json.load(data)
    return bib


@pytest.fixture()
def no_search_only():
    return {"ht_search_only": False, "filters": []}


@pytest.fixture
def search_only(no_search_only):
    no_search_only["ht_search_only"] = True
    return no_search_only


class TestResults:
    def test_availability_filter_full_text(self, solr_results, no_search_only):
        results = {}
        filters = Results(data=solr_results, query_params=no_search_only).filters
        availability_filters = next(f for f in filters if f.field == "availability")
        for f in availability_filters.values:
            results[f.text] = f.count
        assert len(availability_filters.values) == 3
        assert results["Hathi Trust"] == 8
        assert results["Available Online"] == 6
        assert results["Physical"] == 10

    def test_availability_filter_search_only(self, solr_results, search_only):
        results = {}
        filters = Results(data=solr_results, query_params=search_only).filters
        availability_filters = next(f for f in filters if f.field == "availability")
        for f in availability_filters.values:
            results[f.text] = f.count
        assert len(availability_filters.values) == 3
        assert results["Hathi Trust"] == 9
        assert results["Available Online"] == 7
        assert results["Physical"] == 10


class TestFilter:
    def test_filter_has_values(self):
        subject = Filter(field="format", values=["Value1", 1, "Value2", 25]).values

        assert subject[0].text == "Value1"
        assert subject[0].count == 1
        assert subject[1].text == "Value2"
        assert subject[1].count == 25


class TestFilterQuery:
    def test_query_handles_format_facet(self, no_search_only):
        expected = "format:(Book)"
        no_search_only["filters"].append("format:Book")
        subject = FilterQuery(no_search_only)
        assert expected in subject.query()

    def test_query_escape_the_value_and_use_solr_name(self, no_search_only):
        expected = "topicStr:(Engineering\\ \\&\\ Applied\\ Sciences)"

        no_search_only["filters"].append("subject:Engineering & Applied Sciences")
        subject = FilterQuery(no_search_only)

        assert expected in subject.query()

    def test_query_ands_together_facets_with_same_facet_field(self, no_search_only):
        expected = "topicStr:(Technology\\ \\-\\ General AND Engineering\\ \\&\\ Applied\\ Sciences)"

        no_search_only["filters"].append("subject:Technology - General")
        no_search_only["filters"].append("subject:Engineering & Applied Sciences")
        subject = FilterQuery(no_search_only)

        assert expected in subject.query()

    def test_query_excludes_unknown_facet(self, no_search_only):
        no_search_only["filters"].append("facet_field_does_not_exist:some_value")
        subject = FilterQuery(no_search_only)
        assert len(subject.query()) == 1

    def test_availability_for_exclude_search_only(self, no_search_only):
        expected = "(availability:physical OR availability:hathi_trust_full_text_or_electronic_holding)"
        subject = FilterQuery(no_search_only)
        assert expected in subject.query()

    def test_availability_for_exclude_search_only_and_nonsense_availability_value(
        search, no_search_only
    ):
        expected = "(availability:physical OR availability:hathi_trust_full_text_or_electronic_holding)"
        no_search_only["filters"].append("availability:non a real availability value")
        subject = FilterQuery(no_search_only)
        assert expected in subject.query()

    def test_availability_for_exclude_search_only_and_valid_and_nonsense_nonsense_availability_value(
        search, no_search_only
    ):
        expected = "(availability:(hathi_trust_full_text))"
        no_search_only["filters"].append("availability:non a real availability value")
        no_search_only["filters"].append("availability:Hathi Trust")
        subject = FilterQuery(no_search_only)
        assert expected in subject.query()

    def test_availability_for_exclude_search_only_with_physical_filter(
        self, no_search_only
    ):
        expected = "(availability:(physical))"

        no_search_only["filters"].append("availability:Physical")
        subject = FilterQuery(no_search_only)
        assert expected in subject.query()

    def test_availability_for_exclude_search_only_with_physical_and_ht_filter(
        self, no_search_only
    ):
        expected = "(availability:(physical AND hathi_trust_full_text))"

        no_search_only["filters"].append("availability:Physical")
        no_search_only["filters"].append("availability:Hathi Trust")
        subject = FilterQuery(no_search_only)
        assert expected in subject.query()
        assert len(subject.query()) == 1

    def test_availability_for_include_search_only(self, search_only):
        expected = (
            "(availability:physical OR availability:hathi_trust_or_electronic_holding)"
        )
        subject = FilterQuery(search_only)
        assert expected in subject.query()

    def test_availability_for_include_search_only_with_physical_and_ht_filter_and_available_online_filter(
        self, search_only
    ):
        expected = "(availability:(physical AND hathi_trust AND hathi_trust_or_electronic_holding))"

        search_only["filters"].append("availability:Physical")
        search_only["filters"].append("availability:Hathi Trust")
        search_only["filters"].append("availability:Available Online")
        subject = FilterQuery(search_only)
        assert expected in subject.query()
        assert len(subject.query()) == 1

    def test_library_handles_aa(self, no_search_only):
        expected = "institution:(UM\\ Ann\\ Arbor\\ Libraries)"
        no_search_only["filters"].append("library:aa")
        subject = FilterQuery(no_search_only)

        assert expected in subject.query()
        assert len(subject.query()) == 2

    def test_library_returns_no_instition_when_all_included(self, no_search_only):
        no_search_only["filters"].append("library:aa")
        no_search_only["filters"].append("library:all")
        subject = FilterQuery(no_search_only)

        assert len(subject.query()) == 1

    def test_library_returns_no_institution_when_given_nonsense_library(
        self, no_search_only
    ):
        no_search_only["filters"].append("library:nonsense")
        subject = FilterQuery(no_search_only)
        assert len(subject.query()) == 1

    def test_library_returns_only_valid_institution_when_given(self, no_search_only):
        expected = "institution:(UM\\ Ann\\ Arbor\\ Libraries)"
        no_search_only["filters"].append("library:aa")
        no_search_only["filters"].append("library:nonsense")
        subject = FilterQuery(no_search_only)

        assert expected in subject.query()
        assert len(subject.query()) == 2
