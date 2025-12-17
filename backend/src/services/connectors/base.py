from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

class NoSQLConnector(ABC):
    """
    Abstract Base Class for Universal NoSQL Connectivity.
    Any database (Mongo, DynamoDB, Firebase) must implement these methods.
    """

    @abstractmethod
    def connect(self):
        """Establish connection to the database."""
        pass

    @abstractmethod
    def disconnect(self):
        """Close the connection."""
        pass

    @abstractmethod
    def get_schema_summary(self) -> str:
        """
        Returns a string description of collections and fields.
        Crucial for the LLM to understand what to query.
        """
        pass

    @abstractmethod
    def find_one(self, collection: str, query: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Retrieve a single document matching the query."""
        pass

    @abstractmethod
    def find_many(self, collection: str, query: Dict[str, Any], limit: int = 5) -> List[Dict[str, Any]]:
        """Retrieve multiple documents matching the query."""
        pass