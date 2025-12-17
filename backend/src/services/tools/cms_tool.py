
import json
import ast
from typing import Type
from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool
from sqlalchemy.future import select

# Imports for DB access & Connector
from backend.src.db.session import AsyncSessionLocal 
from backend.src.models.integration import UserIntegration
# Ab hum Mock nahi, Real use karenge
from backend.src.services.connectors.sanity_connector import SanityConnector

class CMSQueryInput(BaseModel):
    query: str = Field(..., description="The query string (GROQ/GraphQL) to execute.")

class CMSQueryTool(BaseTool):
    name: str = "cms_query_tool"
    description: str = """
    Use this tool to fetch products, offers, or content from the CMS.
    Input should be a specific query string (e.g., GROQ for Sanity).
    """
    args_schema: Type[BaseModel] = CMSQueryInput
    user_id: str

    def _run(self, query: str) -> str:
        raise NotImplementedError("Use _arun for async execution")

    async def _arun(self, query: str) -> str:
        print(f"🛒 [CMS Tool] Processing Query: {query}")
        
        try:
            async with AsyncSessionLocal() as db:
                # 1. Fetch Integration
                stmt = select(UserIntegration).where(
                    UserIntegration.user_id == self.user_id,
                    UserIntegration.provider == 'sanity', # Specifically find Sanity
                    UserIntegration.is_active == True
                )
                result = await db.execute(stmt)
                integration = result.scalars().first()
                
                if not integration:
                    return "Error: No active Sanity integration found. Please connect first."

                # 2. Decrypt & Parse Credentials
                creds_dict = {}
                try:
                    creds_str = integration.credentials
                    creds_dict = json.loads(creds_str)
                except Exception as e:
                    print(f"❌ [CMS Tool] Credential parsing failed: {e}")
                    return "Error: Invalid Sanity credentials format in database."

                # 3. Connect & Execute (FIX IS HERE)
                # Pass the credentials to the connector
                connector = SanityConnector(credentials=creds_dict)
                
                if not connector.connect():
                    return "Error: Could not connect to Sanity. Please check your credentials."

                data = connector.execute_query(query)
                
                if not data:
                    return "No data found matching your query."
                
                return json.dumps(data, indent=2)

        except Exception as e:
            print(f"❌ [CMS Tool] CRITICAL ERROR: {e}")
            import traceback
            traceback.print_exc()
            return f"Error executing CMS query: {str(e)}"