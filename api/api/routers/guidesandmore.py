from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from api.clients.solr_client import NotFoundError
from api.guidesandmore import get_results, record_for
from api.metrics import REQUEST_HISTOGRAM
from api.schemas import main as schemas

router = APIRouter(prefix="/guidesandmore", tags=["guidesandmore"])


@router.get(
    "/records/{id}",
    responses={
        404: {
            "description": "Bad request: The record was not found",
            "model": schemas.Response404,
        }
    },
    response_model_exclude_none=True,
    response_model_exclude_defaults=True,
)
@REQUEST_HISTOGRAM.labels(datastore="guidesandmore", route="record").time()
async def get_record(id: str) -> schemas.GuidesandmoreRecord:
    """
    Gets a record from website solr. The record is fetched by the solr id.
    """
    try:
        result = await record_for(id)
        return result
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Item not found")


@REQUEST_HISTOGRAM.labels(datastore="guidesandmore", route="results").time()
@router.get(
    "/search",
    response_model_exclude_none=True,
    response_model_exclude_defaults=True,
)
async def get_search_results(
    query: str = "",
    offset: int = 0,
    limit: int = 10,
    filters: Annotated[list[str], Query()] = [],
    sort: schemas.GuidesandmoreSort = schemas.GuidesandmoreSort.relevance,
) -> schemas.GuidesandmoreResults:
    """
    Does a search in catalog solr
    """
    results = await get_results(
        {
            "query": query,
            "offset": offset,
            "limit": limit,
            "filters": filters,
            "sort": sort,
        }
    )
    return results
