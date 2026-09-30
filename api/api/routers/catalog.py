from typing import Annotated
from fastapi import APIRouter, HTTPException, Query
from api.metrics import REQUEST_HISTOGRAM
from api import schemas
from api.clients.solr_client import NotFoundError
from api.record import catalog_record_for
from api.results import get_catalog_results
from api import specialists

router = APIRouter(prefix="/catalog", tags=["catalog"])


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
@REQUEST_HISTOGRAM.labels(datastore="catalog", route="record").time()
async def get_record(id: str, ht_search_only: bool = False) -> schemas.Record:
    """
    Gets a record from catalog solr. The record is fetched by the solr id, which
    is the mms_id for an Alma record or a htid with a 11 prefix for a HathiTrust
    record
    """
    try:
        result = await catalog_record_for(id, ht_search_only)
        return result
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Item not found")


@REQUEST_HISTOGRAM.labels(datastore="catalog", route="results").time()
@router.get("/search", response_model_exclude_none=True)
async def get_search_results(
    query: str = "",
    offset: int = 0,
    limit: int = 10,
    filters: Annotated[list[str], Query()] = [],
    ht_search_only: bool = False,
    sort: schemas.Sort = schemas.Sort.relevance,
) -> schemas.Results:
    """
    Does a search in catalog solr
    """
    results = await get_catalog_results(
        {
            "query": query,
            "offset": offset,
            "limit": limit,
            "filters": filters,
            "ht_search_only": ht_search_only,
            "sort": sort,
        }
    )
    return results


@REQUEST_HISTOGRAM.labels(datastore="catalog", route="specialists").time()
@router.get("/specialists", response_model_exclude_none=True)
def get_specialists(
    query: str = "",
    filters: Annotated[list[str], Query()] = [],
    ht_search_only: bool = False,
) -> schemas.Specialists:
    """
    Looks up specialists associated with given query
    """
    results = specialists.get_catalog_specialists(
        {
            "query": query,
            "filters": filters,
            "ht_search_only": ht_search_only,
        }
    )
    return results
