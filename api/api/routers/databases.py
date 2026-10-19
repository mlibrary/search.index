from typing import Annotated
from fastapi import APIRouter, HTTPException, Query
from api.metrics import REQUEST_HISTOGRAM
from api.schemas import main as schemas
from api.clients.solr_client import NotFoundError
from api.databases import record_for, get_results
# from api.academic_disciplines import get_databases_academic_disciplines
# from api import specialists

router = APIRouter(prefix="/databases", tags=["databases"])


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
@REQUEST_HISTOGRAM.labels(datastore="databases", route="record").time()
async def get_record(id: str) -> schemas.DatabasesRecord:
    """
    Gets a record from website solr. The record is fetched by the solr id
    """
    try:
        result = await record_for(id)
        return result
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Item not found")


@REQUEST_HISTOGRAM.labels(datastore="onlinejournals", route="results").time()
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
    sort: schemas.Sort = schemas.DatabasesSort.relevance,
) -> schemas.DatabasesResults:
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
