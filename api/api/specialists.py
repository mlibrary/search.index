import requests
from api.services import S
from api.results import solr_escape
from api.catalog_results import CatalogFilterQuery
from api.onlinejournals_results import OnlinejournalsFilterQuery


def get_catalog_specialists(query_params: dict):
    response = fetch_catalog_academic_disciplines(query_params)
    return calculate_specialists(response, query_params)


def get_onlinejournals_specialists(query_params: dict):
    response = fetch_onlinejournals_academic_disciplines(query_params)
    return calculate_specialists(response, query_params)


def fetch_catalog_academic_disciplines(query_params: dict):
    fq = CatalogFilterQuery(query_params)
    parser_params = {
        "query": query_params["query"],
        "fq[]": fq.query(),
    }
    response = requests.Session().get(
        f"{S.parser_url}/catalog/academic_disciplines", params=parser_params
    )
    return response.json()


def fetch_onlinejournals_academic_disciplines(query_params: dict):
    fq = OnlinejournalsFilterQuery(query_params)
    parser_params = {
        "query": query_params["query"],
        "fq[]": fq.query(),
    }
    response = requests.Session().get(
        f"{S.parser_url}/onlinejournals/academic_disciplines", params=parser_params
    )
    return response.json()


def calculate_specialists(response, query_params: dict):
    top_academic_disciplines = get_top_academic_disciplines(response)

    website_response = fetch_website_solr_specialists(
        website_solr_query_params(top_academic_disciplines, query_params)
    )
    specialists = specialist_response(website_response)
    return {
        "specialists": specialists,
        "academic_disciplines": top_academic_disciplines,
    }


def get_top_academic_disciplines(data: dict):
    term_threshold = 25
    term_counts = {}
    for doc in data["response"]["docs"]:
        if "hlb3Str" in doc:
            for term in doc["hlb3Str"]:
                if term in term_counts:
                    term_counts[term] += 1
                else:
                    term_counts[term] = 1

    result = []
    for term in term_counts:
        if term_counts[term] >= term_threshold:
            result.append({"discipline": solr_escape(term), "count": term_counts[term]})
    return result


def fetch_website_solr_specialists(params):
    resp = requests.Session().get(
        f"{S.website_solr_url}/solr/www.lib/select", params=params
    )
    return resp.json()


def website_solr_query_params(top_academic_disciplines, query_params):
    fq_academic_disciplines = []
    for f in query_params.get("filters", []):
        term, value = f.split(":")
        if term == "academic_discipline":
            fq_academic_disciplines.append(solr_escape(value))

    fq = "+source:drupal-users +status:true"
    if fq_academic_disciplines:
        ad_str = " AND ".join(fq_academic_disciplines)
        fq += f" +(taxonomy_name:({ad_str}))"

    query = " OR ".join([tad["discipline"] for tad in top_academic_disciplines])

    bq = [
        f"taxonomy_name:({tad['discipline']})^{tad['count']}"
        for tad in top_academic_disciplines
    ]

    return {
        "mm": 1,
        "qf": "taxonomy_name",
        "pf": "taxonomy_name",
        "q": query,
        "fq": fq,
        "bq": bq,
        "rows": 10,
        "defType": "edismax",
        "fl": "*",
        "wt": "json",
    }


def specialist_response(data):
    specialists = []
    for person in data["response"]["docs"]:
        specialists.append(
            {
                "name": person["title"],
                "uniqname": person["ssfield_uniqname"],
                "title": person.get("job_title", None),
                "email": person["email"][0],
                "phone": person.get("ssfield_phone", None),
                "academic_disciplines": person["taxonomy_name"],
            }
        )
    return specialists
