from abc import ABC, abstractmethod
from typing import Dict, Any, List

class CMSBaseConnector(ABC):
    """
    Abstract Interface for Headless CMS Integrations.
    """

    @abstractmethod
    def connect(self, credentials: Dict[str, str]) -> bool:
        """
        Validate credentials and establish connection.
        Returns True if successful.
        """
        pass

    @abstractmethod
    def fetch_schema_structure(self) -> Dict[str, List[str]]:
        """
        Introspects the CMS to find available Types and Fields.
        Example Return: {'product': ['title', 'price'], 'author': ['name']}
        """
        pass

    @abstractmethod
    def execute_query(self, query: str) -> List[Dict[str, Any]]:
        """
        Executes a raw query (GROQ, GraphQL) and returns JSON data.
        """
        pass