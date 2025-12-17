
import json
import asyncio
from typing import Type
from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool
from backend.src.services.connectors.mongo_connector import MongoConnector
from typing import Dict, Optional

# --- NoSQLQueryInput Schema (Same as before) ---
class NoSQLQueryInput(BaseModel):
    collection: str = Field(..., description="The name of the collection to query (e.g., 'users', 'activity_logs').")
    query_json: str = Field(..., description="A valid JSON string representing the query filter.")

class NoSQLQueryTool(BaseTool):
    name: str = "nosql_database_tool"
    description: str = """
    Use this tool to query the NoSQL User Database. 
    Useful for retrieving User Profiles and Activity Logs.
    """
    args_schema: Type[BaseModel] = NoSQLQueryInput
    
    # --- DYNAMIC INJECTION ---
    user_id: str
    db_credentials: Dict[str, str] # User's Mongo URL will come here

    def _run(self, collection: str, query_json: str) -> str:
        # 1. Initialize connector WITH User Credentials
        # Note: Future-proofing to select connector based on provider
        connector = MongoConnector(credentials=self.db_credentials)
        
        try:
            # 2. Parse Query
            query_dict = json.loads(query_json.replace("'", '"')) 
            
            # 3. Security Checks (Injection & RBAC)
            query_str = str(query_dict)
            if "$where" in query_str or "$function" in query_str:
                return "⛔ SECURITY ALERT: Malicious operators detected."

            # Force user_id filter
            query_dict['user_id'] = self.user_id
            
            print(f"🔎 [NoSQL Tool] Executing Query on '{collection}': {query_dict}")

            # 4. Execute
            results = connector.find_many(collection, query_dict, limit=5)
            
            if not results:
                return "No records found matching your request."
            
            return f"Found {len(results)} records:\n{json.dumps(results, indent=2, default=str)}"

        except json.JSONDecodeError:
            return "❌ Error: Invalid JSON query format."
        except Exception as e:
            return f"❌ System Error: {str(e)}"

    async def _arun(self, collection: str, query_json: str):
        """Async wrapper for the tool."""
        return await asyncio.to_thread(self._run, collection, query_json)