import httpx
from api.services import S
from api.results import solr_escape
from api.catalog_results import FilterQuery as CatalogFilterQuery
from api.onlinejournals_results import FilterQuery as OnlinejournalsFilterQuery


async def get_specialists(datastore: str, query_params: dict):
    fq = get_filter_query(datastore, query_params)
    parser_params = {
        "query": query_params["query"],
        "fq[]": fq.query(),
    }
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{S.parser_url}/{datastore}/academic_disciplines", params=parser_params
        )
    return await calculate_specialists(response.json(), query_params)


def get_filter_query(datastore: str, query_params: dict):
    match datastore:
        case "catalog":
            return CatalogFilterQuery(query_params)
        case "onlinejournals":
            return OnlinejournalsFilterQuery(query_params)


async def calculate_specialists(
    response, query_params: dict, ad_field: str = "hlb3Str"
):
    top_academic_disciplines = get_top_academic_disciplines(response, ad_field)

    website_response = await fetch_website_solr_specialists(
        website_solr_query_params(top_academic_disciplines, query_params)
    )
    specialists = specialist_response(website_response)
    return {
        "specialists": specialists,
        "academic_disciplines": top_academic_disciplines,
    }


def get_top_academic_disciplines(data: dict, ad_field: str = "hlb3Str"):
    term_threshold = 25
    term_counts = {}
    for doc in data["response"]["docs"]:
        if ad_field in doc:
            for term in doc[ad_field]:
                if term in term_counts:
                    term_counts[term] += 1
                else:
                    term_counts[term] = 1

    result = []
    for term in term_counts:
        if term_counts[term] >= term_threshold:
            result.append({"discipline": solr_escape(term), "count": term_counts[term]})
    return result


async def fetch_website_solr_specialists(params):
    async with httpx.AsyncClient() as client:
        resp = await client.get(
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
