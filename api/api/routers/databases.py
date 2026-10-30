from typing import Annotated
from fastapi import APIRouter, HTTPException, Query
from api.metrics import REQUEST_HISTOGRAM
from api.schemas import main as schemas
from api.clients.solr_client import NotFoundError
from api.databases import record_for, get_results, get_browse_academic_discipline
from api.academic_disciplines import get_databases_academic_disciplines
from api import specialists

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


@REQUEST_HISTOGRAM.labels(datastore="databases", route="results").time()
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


@REQUEST_HISTOGRAM.labels(datastore="databases", route="specialists").time()
@router.get(
    "/specialists",
    response_model_exclude_none=True,
    response_model_exclude_defaults=True,
)
async def get_specialists(
    query: str = "",
    filters: Annotated[list[str], Query()] = [],
) -> schemas.Specialists:
    """
    Looks up specialists associated with given query
    """
    results = await specialists.get_specialists(
        "databases",
        {
            "query": query,
            "filters": filters,
        },
    )
    return results


@router.get("/academic_disciplines")
async def get_academic_disciplines() -> list[schemas.BrowseAcademicDiscipline]:
    return await get_databases_academic_disciplines()


@REQUEST_HISTOGRAM.labels(
    datastore="databases", route="browse_academic_discipline"
).time()
@router.get(
    "/browse_academic_discipline/{academic_discipline}",
    response_model_exclude_none=True,
)
async def get_browse_academic_discipline_results(
    academic_discipline: str, offset: int = 0, limit: int = 10
) -> schemas.DatabasesResults:
    return await get_browse_academic_discipline(
        {"limit": limit, "offset": offset, "academic_discipline": academic_discipline}
    )
