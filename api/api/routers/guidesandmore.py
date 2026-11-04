from typing import Annotated
from fastapi import APIRouter, HTTPException, Query
from api.metrics import REQUEST_HISTOGRAM
from api.schemas import main as schemas
from api.guidesandmore import get_results

router = APIRouter(prefix="/guidesandmore", tags=["guidesandmore"])


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
