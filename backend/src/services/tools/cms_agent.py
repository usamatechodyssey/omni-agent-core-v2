
import json
from langchain.agents import create_agent
from backend.src.services.llm.factory import get_llm_model
from backend.src.services.tools.cms_tool import CMSQueryTool
from typing import Optional, Dict

# --- THE CMS EXPERT PROMPT (ANTI-YAP VERSION 🤐) ---
CMS_SYSTEM_PROMPT = """You are a Sanity GROQ Query Generator.
Your goal is to query the database based on the user's request.

--- KNOWLEDGE BASE (SCHEMA) ---
{schema_map}

--- RULES (READ CAREFULLY) ---
1. **NO EXPLANATIONS:** Do NOT say "Here is the query" or "I will search for...".
2. **JUST THE QUERY:** Directly call the 'cms_query_tool' with the GROQ string.
3. **USE THE SCHEMA:** Look at the schema map above. If `price` is inside `variants`, use `variants[].price`.
4. **SYNTAX:** `*[_type == "product" && title match "Blue*"]`

--- ERROR HANDLING ---
If the query fails or returns empty, just say: "No products found matching your criteria."
Do NOT make up fake products from Amazon or other websites.

User Input: {input}
"""

# --- AGENT ADAPTER ---
class AgentAdapter:
    def __init__(self, agent):
        self.agent = agent
    
    async def ainvoke(self, input_dict):
        # Hum input ko thoda modify karke bhejenge taake AI focus kare
        user_text = input_dict.get("input", "")
        # Force instruction appended to user query
        strict_input = f"{user_text} (Return ONLY the GROQ query tool call. Do not explain.)"
        
        payload = {"messages": [("user", strict_input)]}
        result = await self.agent.ainvoke(payload)
        last_message = result["messages"][-1]
        return {"output": last_message.content}

# --- DYNAMIC AGENT FACTORY ---
def get_cms_agent(
    user_id: str, 
    schema_map: dict,
    llm_credentials: Optional[Dict[str, str]] = None
):
    # 1. Load User's LLM
    llm = get_llm_model(credentials=llm_credentials)
    
    # 2. Initialize Tool
    tool = CMSQueryTool(user_id=str(user_id))
    tools = [tool]

    # Convert schema to string
    schema_str = json.dumps(schema_map, indent=2)

    # 3. Create Agent
    agent_runnable = create_agent(
        model=llm,
        tools=tools,
        system_prompt=CMS_SYSTEM_PROMPT.format(schema_map=schema_str, input="{input}")
    )
    
    return AgentAdapter(agent_runnable)