from dataclasses import dataclass
import os
import fastapi_structured_logging

fastapi_structured_logging.setup_logging()


@dataclass(frozen=True)
class Services:
    """
    Global Configuration Services
    """

    app_env: str
    project_root: str
    solr_url: str
    website_solr_url: str
    solr_cloud_on: bool
    solr_user: str
    solr_password: str
    parser_url: str
    alma_api_url: str
    primo_api_url: str
    open_url_root: str
    lib_key_host: str
    lib_key_library_id: str
    lib_key_key: str
    proxy_prefix: str
    alma_api_key: str


S = Services(
    app_env=os.getenv("APP_ENV") or "development",
    project_root=os.path.abspath(os.path.dirname(__file__)),
    solr_url=os.getenv("SOLR_URL") or "http://solr:8983",
    website_solr_url=os.getenv("WEBSITE_SOLR_URL") or "http://website-solr:8983",
    solr_cloud_on=os.getenv("SOLR_CLOUD_ON") == "true",
    solr_user=os.getenv("SOLR_USER") or "solr",
    solr_password=os.getenv("SOLR_PASSWORD") or "SolrRocks",
    parser_url=os.getenv("PARSER_URL") or "http://parser:4567",
    alma_api_url="https://api-na.hosted.exlibrisgroup.com/almaws/v1",
    primo_api_url="https://api-na.hosted.exlibrisgroup.com/primo/v1",
    open_url_root="https://mgetit.lib.umich.edu/resolve",
    lib_key_host=os.getenv("LIB_KEY_HOST") or "http://lib_key_host",
    lib_key_library_id=os.getenv("LIB_KEY_LIBRARY_ID") or "lib_key_library_id",
    lib_key_key=os.getenv("LIB_KEY_KEY") or "lib_key_key",
    proxy_prefix="https://proxy.lib.umich.edu/login?qurl=",
    alma_api_key=os.getenv("ALMA_API_KEY") or "your_alma_api_key",
)
