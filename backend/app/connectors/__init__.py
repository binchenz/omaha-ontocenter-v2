from .registry import register, get_connector
from .sql_connector import SQLConnector
from .csv_connector import CSVConnector
from .rest_connector import RESTConnector
from .mongodb_connector import MongoDBConnector

register("postgresql", SQLConnector)
register("mysql", SQLConnector)
register("sqlite", SQLConnector)
register("csv", CSVConnector)
register("excel", CSVConnector)
register("rest_api", RESTConnector)
register("mongodb", MongoDBConnector)

__all__ = ["get_connector", "SQLConnector", "CSVConnector", "RESTConnector", "MongoDBConnector"]
