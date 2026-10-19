from fastapi import APIRouter, HTTPException, Query
from typing import Annotated
from api.metrics import REQUEST_HISTOGRAM
from api.schemas import main as schemas
from api.clients.exlibris_client import NotFoundError
from api.primo import record_for, get_results

router = APIRouter(prefix="/articles", tags=["articles"])


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
@REQUEST_HISTOGRAM.labels(datastore="articles", route="record").time()
async def get_record(id: str) -> schemas.ArticlesRecord:
    """
    Gets a record from catalog solr. The record is fetched by the solr id, which
    is the mms_id for an Alma record or a htid with a 11 prefix for a HathiTrust
    record
    """
    try:
        result = await record_for(id)
        return result
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Item not found")


@REQUEST_HISTOGRAM.labels(datastore="catalog", route="results").time()
@router.get(
    "/search", response_model_exclude_none=True, response_model=schemas.ArticlesResults
)
async def get_search_results(
    query: str = "",
    offset: int = 0,
    limit: int = 10,
    include_citation_only: bool = False,
    open_access: bool = False,
    online: bool = False,
    exclude_newspapers: bool = False,
    peer_reviewed: bool = False,
    filters: Annotated[list[str], Query()] = [],
    sort: schemas.ArticlesSort = schemas.ArticlesSort.relevance,
):
    """
    Does a search in catalog solr
    """
    results = await get_results(
        {
            "query": query,
            "offset": offset,
            "limit": limit,
            "include_citation_only": include_citation_only,
            "open_access": open_access,
            "online": online,
            "exclude_newspapers": exclude_newspapers,
            "peer_reviewed": peer_reviewed,
            "filters": filters,
            "sort": sort,
        }
    )
    return results
