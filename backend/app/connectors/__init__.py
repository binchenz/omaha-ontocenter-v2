from .registry import register, get_connector
from .sql_connector import SQLConnector
from .tushare_connector import TushareConnector
from .csv_connector import CSVConnector
from .rest_connector import RESTConnector

register("postgresql", SQLConnector)
register("mysql", SQLConnector)
register("sqlite", SQLConnector)
register("tushare", TushareConnector)
register("csv", CSVConnector)
register("excel", CSVConnector)
register("rest_api", RESTConnector)

__all__ = ["get_connector", "SQLConnector", "TushareConnector", "CSVConnector", "RESTConnector"]
