import pytest
import json
from httpx import Response
from api.clients.exlibris_client import AlmaClient
from api.services import S


@pytest.fixture()
def loan():
    loan = None
    with open("tests/fixtures/loans/alma_loans_example.json") as data:
        loan = json.load(data)
    return loan


@pytest.fixture
def empty_loan_data():
    return json.loads('{"total_record_count": 0}')


@pytest.fixture
def alma_error_string():
    return '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\r\n<web_service_result xmlns="http://com/exlibris/urm/general/xmlbeans">\r\n            <errorsExist>true</errorsExist>\r\n            <errorList>\r\n                        <error>\r\n                                    <errorCode>UNAUTHORIZED</errorCode>\r\n                                    <errorMessage>API-key not defined or not configured to allow this API.</errorMessage>\r\n                        </error>\r\n            </errorList>\r\n</web_service_result>'


@pytest.fixture()
def mms_id(loan):
    return loan["item_loan"][0]["mms_id"]


@pytest.mark.asyncio
async def test_alma_client_get_loans_gets_one_page(loan, mms_id, respx_mock):
    respx_mock.get(f"{S.alma_api_url}/bibs/{mms_id}/loans?limit=100").mock(
        Response(200, json=loan)
    )

    assert await AlmaClient().get_loans(mms_id) == loan


@pytest.mark.asyncio
async def test_alma_client_get_loans_gets_all_results(loan, mms_id, respx_mock):
    loan["total_record_count"] = 101

    respx_mock.get(f"{S.alma_api_url}/bibs/{mms_id}/loans?limit=100").mock(
        Response(200, json=loan)
    )

    respx_mock.get(f"{S.alma_api_url}/bibs/{mms_id}/loans?limit=100&offset=100").mock(
        Response(200, json=loan)
    )

    loans = await AlmaClient().get_loans(mms_id)
    assert len(loans["item_loan"]) == 2


@pytest.mark.asyncio
async def test_alma_client_get_loans_handles_no_loans(
    empty_loan_data, mms_id, respx_mock
):
    respx_mock.get(f"{S.alma_api_url}/bibs/{mms_id}/loans?limit=100").mock(
        Response(
            200,
            json=empty_loan_data,
        )
    )
    loans = await AlmaClient().get_loans(mms_id)
    assert len(loans["item_loan"]) == 0


@pytest.mark.asyncio
async def test_alma_client_get_loans_handles_error_response(
    alma_error_string, mms_id, respx_mock
):
    respx_mock.get(f"{S.alma_api_url}/bibs/{mms_id}/loans?limit=100").mock(
        Response(500, content=alma_error_string)
    )
    loans = await AlmaClient().get_loans(mms_id)
    # resturns a response with no loans. We do want it to log the situation.
    assert len(loans["item_loan"]) == 0
