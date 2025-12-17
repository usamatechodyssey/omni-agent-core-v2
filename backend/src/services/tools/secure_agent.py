
from langchain.agents import create_agent
from backend.src.services.llm.factory import get_llm_model
from backend.src.services.tools.sql_tool import get_sql_toolkit # Updated Import
from typing import Optional, Dict

# --- PROMPTS (Same as before) ---
ADMIN_PREFIX = "You are a PostgreSQL expert... full access..."
CUSTOMER_PREFIX = """You are a SQL helper for User ID: {user_id}.
CRITICAL: For every query, you MUST add a "WHERE user_id = {user_id}" clause.
Never show data of other users.
Always present data in a clean MARKDOWN TABLE.
"""

# --- AGENT ADAPTER (Same as before) ---
class AgentAdapter:
    def __init__(self, agent):
        self.agent = agent
    
    async def ainvoke(self, input_dict):
        user_text = input_dict.get("input", "")
        payload = {"messages": [("user", user_text)]}
        result = await self.agent.ainvoke(payload)
        last_message = result["messages"][-1]
        return {"output": last_message.content}

# --- DYNAMIC AGENT FACTORY ---
def get_secure_agent(
    user_id: int, 
    role: str,
    db_credentials: Dict[str, str],
    llm_credentials: Optional[Dict[str, str]] = None
):
    """
    Creates a Secure SQL Agent using the specific user's databases and LLM.
    """
    # 1. Load User's LLM (via factory)
    llm = get_llm_model(credentials=llm_credentials)
    
    # 2. Get User-specific SQL Toolkit
    toolkit = get_sql_toolkit(db_credentials, llm_credentials)
    tools = toolkit.get_tools() # Toolkit se tools nikalo

    # 3. Select the right security prompt
    if role == "admin":
        system_prefix = ADMIN_PREFIX
    else:
        system_prefix = CUSTOMER_PREFIX.format(user_id=user_id)

    # 4. Create the Agent (New V1 'create_agent' syntax)
    agent_runnable = create_agent(
        model=llm,
        tools=tools,
        system_prompt=system_prefix
    )
    
    return AgentAdapter(agent_runnable)