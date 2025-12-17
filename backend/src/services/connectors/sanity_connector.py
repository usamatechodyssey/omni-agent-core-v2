
import requests
import json
from urllib.parse import quote
from typing import Dict, List, Any
from backend.src.services.connectors.cms_base import CMSBaseConnector

class SanityConnector(CMSBaseConnector):
    def __init__(self, credentials: Dict[str, str]):
        self.project_id = credentials.get("project_id")
        self.dataset = credentials.get("dataset")
        self.token = credentials.get("token") # Read-only token
        self.api_version = "v2021-10-21"
        
        if not all([self.project_id, self.dataset, self.token]):
            raise ValueError("Sanity credentials (project_id, dataset, token) are required.")
            
        # Build the base URL for API calls
        self.base_url = f"https://{self.project_id}.api.sanity.io/{self.api_version}/data/query/{self.dataset}"
        self.headers = {"Authorization": f"Bearer {self.token}"}
        
        self.is_connected = False

    def connect(self, credentials: Dict[str, str] = None) -> bool:
        """Tests the connection by making a simple, non-data-intensive query."""
        if not self.is_connected:
            print(f"🔌 [Sanity] Connecting to Project ID: {self.project_id}...")
            try:
                # Test query to check credentials
                test_query = '*[_type == "sanity.imageAsset"][0...1]'
                response = requests.get(self.base_url, headers=self.headers, params={'query': test_query})
                
                if response.status_code == 200:
                    self.is_connected = True
                    print("✅ [Sanity] Connection Successful.")
                    return True
                else:
                    print(f"❌ [Sanity] Connection Failed. Status: {response.status_code}, Response: {response.text}")
                    return False
            except Exception as e:
                print(f"❌ [Sanity] Connection Failed: {e}")
                return False
        return True

    def fetch_schema_structure(self) -> Dict[str, Any]:
        """
        🕵️‍♂️ DEEP DISCOVERY: Fetches 1 sample of EVERY type to map the full nesting.
        """
        if not self.is_connected: self.connect()
        
        print("🕵️‍♂️ Starting Deep Schema Discovery...")
        
        # Step 1: Get all unique document types (filtering out system types)
        types_query = "array::unique(*[!(_id in path('_.**')) && !(_type match 'sanity.*')]._type)"
        
        try:
            response = requests.get(self.base_url, headers=self.headers, params={'query': types_query})
            if response.status_code != 200:
                print(f"❌ Failed to fetch types: {response.text}")
                return {}
                
            user_types = response.json().get('result', [])
            print(f"📋 Found Types: {user_types}")

            schema_map = {}
            
            # Step 2: Loop through each type and fetch ONE full document
            for doc_type in user_types:
                # Query: "Give me the first item of this type"
                sample_query = f"*[_type == '{doc_type}'][0]"
                sample_response = requests.get(self.base_url, headers=self.headers, params={'query': sample_query})
                sample_doc = sample_response.json().get('result')
                
                if sample_doc:
                    # Step 3: Recursively extract structure
                    structure = self._extract_structure(sample_doc)
                    schema_map[doc_type] = structure
            
            print(f"✅ Full Database Map Created.")
            return schema_map

        except Exception as e:
            print(f"❌ Schema Discovery Error: {e}")
            return {}

    def _extract_structure(self, doc: Any, depth=0) -> Any:
        """
        Helper to map nested fields.
        Real Data: {"store": {"price": 20}} -> Map: {"store": {"price": "Number"}}
        """
        if depth > 3: return "..." # Stop infinite recursion
        
        if isinstance(doc, dict):
            structure = {}
            for key, value in doc.items():
                if key.startswith("_"): continue # Skip internal fields
                structure[key] = self._extract_structure(value, depth + 1)
            return structure
            
        elif isinstance(doc, list):
            # If list has items, check the first one to know what's inside
            if len(doc) > 0:
                return [self._extract_structure(doc[0], depth + 1)]
            return "List[]"
            
        elif isinstance(doc, (int, float)):
            return "Number"
        elif isinstance(doc, bool):
            return "Boolean"
        
        return "String"

    def execute_query(self, query: str) -> List[Dict[str, Any]]:
        """Executes a GROQ query against the Sanity HTTP API."""
        if not self.is_connected: self.connect()
        
        print(f"🚀 [Sanity] Executing GROQ Query: {query}")
        try:
            # URL-encode the query to handle special characters
            encoded_query = quote(query)
            
            response = requests.get(f"{self.base_url}?query={encoded_query}", headers=self.headers)
            
            if response.status_code == 200:
                results = response.json().get('result')
                if results is None: return []
                return results if isinstance(results, list) else [results]
            else:
                print(f"❌ [Sanity] Query Failed. Status: {response.status_code}, Details: {response.text}")
                return []
        except Exception as e:
            print(f"❌ [Sanity] Query execution error: {e}")
            return []