from typing import Annotated
from fastapi import APIRouter, HTTPException, Query
from api.metrics import REQUEST_HISTOGRAM
from api import schemas
from api.clients.solr_client import NotFoundError
from api.onlinejournals_record import record_for
from api.onlinejournals_results import (
    get_onlinejournals_results,
    get_onlinejournals_browse_academic_discipline,
)
from api.academic_disciplines import get_onlinejournals_academic_disciplines
from api import specialists

router = APIRouter(prefix="/onlinejournals", tags=["onlinejournals"])


@router.get(
    "/records/{id}",
    responses={
        404: {
            "description": "Bad request: The record was not found",
            "model": schemas.Response404,
        }
    },
    response_model_exclude_none=True,
)
@REQUEST_HISTOGRAM.labels(datastore="onlinejournals", route="record").time()
def get_record(id: str) -> schemas.OnlinejournalsRecord:
    """
    Gets a record from catalog solr. The record is fetched by the solr id, which
    is the mms_id for an Alma record or a htid with a 11 prefix for a HathiTrust
    record
    """
    try:
        result = record_for(id)
        return result
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Item not found")


@REQUEST_HISTOGRAM.labels(datastore="onlinejournals", route="results").time()
@router.get("/search", response_model_exclude_none=True)
def get_search_results(
    query: str = "",
    offset: int = 0,
    limit: int = 10,
    filters: Annotated[list[str], Query()] = [],
    sort: schemas.Sort = schemas.Sort.relevance,
) -> schemas.OnlinejournalsResults:
    """
    Does a search in catalog solr
    """
    results = get_onlinejournals_results(
        {
            "query": query,
            "offset": offset,
            "limit": limit,
            "filters": filters,
            "sort": sort,
        }
    )
    return results


@REQUEST_HISTOGRAM.labels(datastore="onlinejournals", route="specialists").time()
@router.get("/specialists", response_model_exclude_none=True)
def get_specialists(
    query: str = "",
    filters: Annotated[list[str], Query()] = [],
) -> schemas.Specialists:
    """
    Looks up specialists associated with given query
    """
    results = specialists.get_onlinejournals_specialists(
        {
            "query": query,
            "filters": filters,
        }
    )
    return results


@router.get("/academic_disciplines")
def get_academic_disciplines() -> list[schemas.BrowseAcademicDiscipline]:
    return get_onlinejournals_academic_disciplines()


@REQUEST_HISTOGRAM.labels(
    datastore="onlinejournals", route="browse_academic_discipline"
).time()
@router.get(
    "/browse_academic_discipline/{academic_discipline}",
    response_model_exclude_none=True,
)
def get_browse_academic_discipline(
    academic_discipline: str, offset: int = 0, limit: int = 10
) -> schemas.OnlinejournalsResults:
    return get_onlinejournals_browse_academic_discipline(
        {"limit": limit, "offset": offset, "academic_discipline": academic_discipline}
    )
