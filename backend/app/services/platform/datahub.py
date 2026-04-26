"""
DataHub integration service.
"""
from typing import List, Dict, Any, Optional
import httpx
from app.config import settings


class DataHubService:
    """Service for interacting with DataHub GMS API."""

    def __init__(self):
        self.base_url = settings.DATAHUB_GMS_URL
        self.token = settings.DATAHUB_GMS_TOKEN
        self.headers = {}
        if self.token:
            self.headers["Authorization"] = f"Bearer {self.token}"

    async def search_datasets(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search for datasets in DataHub."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/entities?action=search",
                json={
                    "input": query,
                    "entity": "dataset",
                    "start": 0,
                    "count": limit,
                },
                headers=self.headers,
            )
            response.raise_for_status()
            data = response.json()
            return data.get("value", {}).get("entities", [])

    async def get_dataset_schema(self, dataset_urn: str) -> Optional[Dict[str, Any]]:
        """Get schema information for a dataset."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/aspects/{dataset_urn}",
                params={"aspect": "schemaMetadata"},
                headers=self.headers,
            )
            if response.status_code == 404:
                return None
            response.raise_for_status()
            return response.json()

    async def get_dataset_properties(self, dataset_urn: str) -> Optional[Dict[str, Any]]:
        """Get properties for a dataset."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/aspects/{dataset_urn}",
                params={"aspect": "datasetProperties"},
                headers=self.headers,
            )
            if response.status_code == 404:
                return None
            response.raise_for_status()
            return response.json()


datahub_service = DataHubService()
