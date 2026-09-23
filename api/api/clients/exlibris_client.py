import requests
from api.services import S
from api.metrics import ALMA_LOAN_HISTOGRAM
import xml.etree.ElementTree as ET
import fastapi_structured_logging

logger = fastapi_structured_logging.get_logger()


class NotFoundError(Exception):
    pass


class ExlibrisClient:
    def __init__(self) -> None:
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"apikey {S.alma_api_key}",
                "Accept": "application/json",
                "Content-Type": "application/json",
            }
        )

    def get_error_string(self, error_string):
        ns = {"alma": "http://com/exlibris/urm/general/xmlbeans"}
        root = ET.fromstring(error_string)
        result = []
        for error in root.findall(".//alma:error", ns):
            code = error.find("alma:errorCode", ns)
            message = error.find("alma:errorMessage", ns)
            result.append(f"code: {code.text}, message: {message.text}")

        return " | ".join(result)


class AlmaClient(ExlibrisClient):
    base_url = S.alma_api_url

    @ALMA_LOAN_HISTOGRAM.time()
    def get_loans(self, mms_id: str):
        limit = 100
        offset = 0
        url = f"{self.base_url}/bibs/{mms_id}/loans"
        total = 0
        result = {"item_loan": [], "total_record_count": 0}

        try:
            response = self.session.get(url, params={"limit": limit})
            response.raise_for_status()
            result = response.json()
            total = result["total_record_count"]
        except requests.exceptions.HTTPError as e:
            logger.error(
                f"HTTP error occurred: {e} {self.get_error_string(response.text)}"
            )
        except requests.exceptions.RequestException as e:
            logger.error("A request error occurred:", e)

        if total > 100:
            while total > offset + limit:
                offset = offset + limit
                response = self.session.get(
                    url, params={"limit": limit, "offset": offset}
                )
                for loan in response.json().get("item_loan", []):
                    result["item_loan"].append(loan)

        if "item_loan" not in result:
            result["item_loan"] = []

        return result


class PrimoClient(ExlibrisClient):
    base_url = S.primo_api_url

    def get_record(self, id: str):
        params = {
            "q": f"id,exact,{id}",
            "scope": "CentralIndex",
            "tab": "CentralIndex",
            "vid": "01UMICH_INST:UMICH",
            "pcAvailability": "true",
        }
        url = f"{self.base_url}/search"
        try:
            response = self.session.get(url, params=params)
            response.raise_for_status()
            body = response.json()
            if body["info"]["total"] == 0:
                raise NotFoundError()
            return body["docs"][0]
        except requests.exceptions.HTTPError as e:
            logger.error(
                f"HTTP error occurred: {e} {self.get_error_string(response.text)}"
            )
        except requests.exceptions.RequestException as e:
            logger.error("A request error occurred:", e)
