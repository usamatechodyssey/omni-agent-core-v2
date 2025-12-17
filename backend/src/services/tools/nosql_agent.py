
from langchain.agents import create_agent
from backend.src.services.llm.factory import get_llm_model
from backend.src.services.tools.nosql_tool import NoSQLQueryTool
from typing import Optional, Dict

# --- THE CONSTITUTION (Same as before) ---
NOSQL_SYSTEM_PROMPT = """You are a User Data Assistant with access to a NoSQL Database.
Your job is to retrieve user profile details and activity logs using the 'nosql_database_tool'.

--- CRITICAL RULES FOR QUERYING ---
1. **DO NOT** include 'user_id' or '_id' in the 'query_json'. 
   - The tool AUTOMATICALLY applies the security filter for the current user.
   - If you want to fetch the user's profile, just send an empty query: "{{}}"
   
2. **DO NOT** try to select specific fields in the query_json.
   - Incorrect: {{"fields": ["email"]}} 
   - Correct: {{}} (Fetch the whole document, then you extract the email).

3. You are acting on behalf of User ID: {user_id}.

--- AVAILABLE COLLECTIONS ---
1. 'users': Contains profile info (name, email, membership_tier).
2. 'activity_logs': Contains login history and actions.

--- EXAMPLES ---
- User: "Show my profile" -> Tool Input: collection='users', query_json='{{}}'
- User: "Show my login history" -> Tool Input: collection='activity_logs', query_json='{{"action": "login"}}'
"""

class AgentAdapter:
    """Wrapper for V1 Agent compatibility"""
    def __init__(self, agent):
        self.agent = agent
    
    async def ainvoke(self, input_dict):
        user_text = input_dict.get("input", "")
        payload = {"messages": [("user", user_text)]}
        result = await self.agent.ainvoke(payload)
        last_message = result["messages"][-1]
        return {"output": last_message.content}

# --- DYNAMIC AGENT FACTORY (UPDATED) ---
def get_nosql_agent(
    user_id: str,
    llm_credentials: Optional[Dict[str, str]] = None # <--- Added this
):
    """
    Creates a NoSQL Agent using the user's specific LLM credentials.
    """
    # 1. Load User's LLM
    llm = get_llm_model(credentials=llm_credentials)
    
    # 2. Initialize the tool
    tool = NoSQLQueryTool(user_id=str(user_id))
    tools = [tool]

    # 3. Create Agent
    agent_runnable = create_agent(
        model=llm,
        tools=tools,
        system_prompt=NOSQL_SYSTEM_PROMPT.format(user_id=user_id)
    )
    
    return AgentAdapter(agent_runnable)