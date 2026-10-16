# from typing import Annotated
from fastapi import APIRouter, HTTPException
from api.metrics import REQUEST_HISTOGRAM
from api import schemas
from api.clients.solr_client import NotFoundError
from api.databases import record_for
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
