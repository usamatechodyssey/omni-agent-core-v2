
# import json
# from sqlalchemy.ext.asyncio import AsyncSession
# from sqlalchemy.future import select

# # --- Model Imports ---
# from backend.src.models.chat import ChatHistory
# from backend.src.models.integration import UserIntegration

# # --- Dynamic Factory & Tool Imports ---
# from backend.src.services.llm.factory import get_llm_model
# from backend.src.services.vector_store.qdrant_adapter import get_vector_store
# from backend.src.services.security.pii_scrubber import PIIScrubber

# # --- Agents ---
# from backend.src.services.tools.secure_agent import get_secure_agent 
# from backend.src.services.tools.nosql_agent import get_nosql_agent 
# from backend.src.services.tools.cms_agent import get_cms_agent

# # --- Router ---
# from backend.src.services.routing.semantic_router import SemanticRouter

# # --- LangChain Core ---
# from langchain_core.messages import HumanMessage, AIMessage
# from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

# # ==========================================
# # HELPER FUNCTIONS (UPDATED STRICT LOGIC)
# # ==========================================

# async def get_user_integrations(user_id: str, db: AsyncSession) -> dict:
#     if not user_id: return {}
    
#     query = select(UserIntegration).where(UserIntegration.user_id == user_id, UserIntegration.is_active == True)
#     result = await db.execute(query)
#     integrations = result.scalars().all()
    
#     settings = {}
#     for i in integrations:
#         try:
#             creds = json.loads(i.credentials)
#             creds['provider'] = i.provider
#             creds['schema_map'] = i.schema_map if i.schema_map else {}
            
#             # --- 🔥 FIX: NO DEFAULT DESCRIPTION ---
#             # Agar DB mein description NULL hai, to NULL hi rehne do.
#             # Hum isay Router mein add hi nahi karenge.
#             creds['description'] = i.profile_description 
            
#             settings[i.provider] = creds
#         except (json.JSONDecodeError, TypeError):
#             continue
#     return settings

# async def save_chat_to_db(db: AsyncSession, session_id: str, human_msg: str, ai_msg: str, provider: str):
#     if not session_id: return
#     safe_human = PIIScrubber.scrub(human_msg)
#     safe_ai = PIIScrubber.scrub(ai_msg)
#     new_chat = ChatHistory(
#         session_id=session_id, human_message=safe_human, ai_message=safe_ai, provider=provider
#     )
#     db.add(new_chat)
#     await db.commit()

# async def get_chat_history(session_id: str, db: AsyncSession):
#     if not session_id: return []
#     query = select(ChatHistory).where(ChatHistory.session_id == session_id).order_by(ChatHistory.timestamp.asc())
#     result = await db.execute(query)
#     return result.scalars().all()

# OMNI_SUPPORT_PROMPT = "You are OmniAgent. Answer based on the provided context or chat history."

# # ==========================================
# # MAIN CHAT LOGIC
# # ==========================================
# async def process_chat(message: str, session_id: str, user_id: str, db: AsyncSession):
    
#     # 1. User Settings
#     user_settings = await get_user_integrations(user_id, db)
    
#     # 2. LLM Check
#     llm_creds = user_settings.get('groq') or user_settings.get('openai')
#     if not llm_creds:
#         return "Please configure your AI Model in Settings."

#     # 3. Build Tool Map for Router (STRICT FILTERING)
#     tools_map = {}
#     for provider, config in user_settings.items():
#         if provider in ['sanity', 'sql', 'mongodb']:
#             # 🔥 Check: Agar Description hai, tabhi Router mein daalo
#             if config.get('description'):
#                 tools_map[provider] = config['description']
#             else:
#                 print(f"⚠️ [Router] Skipping {provider} - No Description found.")

#     # 4. SEMANTIC DECISION
#     selected_provider = None
#     if tools_map:
#         router = SemanticRouter()
#         selected_provider = router.route(message, tools_map)
#     else:
#         print("⚠️ [Router] No active tools with descriptions found.")
    
#     response_text = ""
#     provider_name = "general_chat"

#     # 5. Route to Winner
#     if selected_provider:
#         print(f"👉 [Router] Selected Tool: {selected_provider.upper()}")
#         try:
#             if selected_provider == 'sanity':
#                 schema = user_settings['sanity'].get('schema_map', {})
#                 agent = get_cms_agent(user_id=user_id, schema_map=schema, llm_credentials=llm_creds)
#                 res = await agent.ainvoke({"input": message})
#                 response_text = str(res.get('output', ''))
#                 provider_name = "cms_agent"

#             elif selected_provider == 'sql':
#                 role = "admin" if user_id == '99' else "customer"
#                 agent = get_secure_agent(int(user_id), role, user_settings['sql'], llm_credentials=llm_creds)
#                 res = await agent.ainvoke({"input": message})
#                 response_text = str(res.get('output', ''))
#                 provider_name = "sql_agent"

#             elif selected_provider == 'mongodb':
#                 agent = get_nosql_agent(user_id, user_settings['mongodb'], llm_credentials=llm_creds)
#                 res = await agent.ainvoke({"input": message})
#                 response_text = str(res.get('output', ''))
#                 provider_name = "nosql_agent"

#             # Anti-Hallucination
#             if not response_text or "error" in response_text.lower():
#                 response_text = "" # Trigger Fallback

#         except Exception as e:
#             print(f"❌ [Router] Execution Failed: {e}")
#             response_text = "" 

#     # 6. Fallback / RAG
#     if not response_text:
#         print("👉 [Router] Fallback to RAG/General Chat...")
#         try:
#             llm = get_llm_model(credentials=llm_creds)
            
#             context = ""
#             if 'qdrant' in user_settings:
#                 try:
#                     vector_store = get_vector_store(credentials=user_settings['qdrant'])
#                     docs = await vector_store.asimilarity_search(message, k=3)
#                     if docs:
#                         context = "\n\n".join([d.page_content for d in docs])
#                 except Exception as e:
#                     print(f"⚠️ RAG Warning: {e}")
            
#             system_instruction = OMNI_SUPPORT_PROMPT
#             if context: system_instruction = f"Context:\n{context}"

#             history = await get_chat_history(session_id, db)
#             formatted_history = []
#             for chat in history:
#                 formatted_history.append(HumanMessage(content=chat.human_message))
#                 if chat.ai_message: formatted_history.append(AIMessage(content=chat.ai_message))

#             prompt = ChatPromptTemplate.from_messages([
#                 ("system", system_instruction),
#                 MessagesPlaceholder(variable_name="chat_history"),
#                 ("human", "{question}")
#             ])
#             chain = prompt | llm
            
#             ai_response = await chain.ainvoke({"chat_history": formatted_history, "question": message})
#             response_text = ai_response.content
#             provider_name = "rag_fallback"

#         except Exception as e:
#             response_text = "I am currently unable to process your request."

#     await save_chat_to_db(db, session_id, message, response_text, provider_name)
#     return response_text
import json
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

# --- Model Imports ---
from backend.src.models.chat import ChatHistory
from backend.src.models.integration import UserIntegration
from backend.src.models.user import User  # Added User model for Bot Persona

# --- Dynamic Factory & Tool Imports ---
from backend.src.services.llm.factory import get_llm_model
from backend.src.services.vector_store.qdrant_adapter import get_vector_store
from backend.src.services.security.pii_scrubber import PIIScrubber

# --- Agents ---
from backend.src.services.tools.secure_agent import get_secure_agent 
from backend.src.services.tools.nosql_agent import get_nosql_agent 
from backend.src.services.tools.cms_agent import get_cms_agent

# --- Router ---
from backend.src.services.routing.semantic_router import SemanticRouter

# --- LangChain Core ---
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

# ==========================================
# HELPER FUNCTIONS
# ==========================================

async def get_user_integrations(user_id: str, db: AsyncSession) -> dict:
    """Fetches active integrations and filters valid descriptions."""
    if not user_id: return {}
    
    query = select(UserIntegration).where(UserIntegration.user_id == user_id, UserIntegration.is_active == True)
    result = await db.execute(query)
    integrations = result.scalars().all()
    
    settings = {}
    for i in integrations:
        try:
            creds = json.loads(i.credentials)
            creds['provider'] = i.provider
            creds['schema_map'] = i.schema_map if i.schema_map else {}
            
            # --- STRICT CHECK ---
            if i.profile_description:
                creds['description'] = i.profile_description
            
            settings[i.provider] = creds
        except (json.JSONDecodeError, TypeError):
            continue
    return settings

async def save_chat_to_db(db: AsyncSession, session_id: str, human_msg: str, ai_msg: str, provider: str):
    """Saves chat history with PII redaction."""
    if not session_id: return
    safe_human = PIIScrubber.scrub(human_msg)
    safe_ai = PIIScrubber.scrub(ai_msg)
    new_chat = ChatHistory(
        session_id=session_id, human_message=safe_human, ai_message=safe_ai, provider=provider
    )
    db.add(new_chat)
    await db.commit()

async def get_chat_history(session_id: str, db: AsyncSession):
    """Retrieves past conversation history."""
    if not session_id: return []
    query = select(ChatHistory).where(ChatHistory.session_id == session_id).order_by(ChatHistory.timestamp.asc())
    result = await db.execute(query)
    return result.scalars().all()

async def get_bot_persona(user_id: str, db: AsyncSession):
    """Fetches custom Bot Name and Instructions from User table."""
    try:
        # User ID ko int mein convert karke query karein
        stmt = select(User).where(User.id == int(user_id))
        result = await db.execute(stmt)
        user = result.scalars().first()
        
        if user:
            return {
                "name": getattr(user, "bot_name", "OmniAgent"),
                "instruction": getattr(user, "bot_instruction", "You are a helpful AI assistant.")
            }
    except Exception as e:
        print(f"⚠️ Error fetching persona: {e}")
        pass
    
    # Fallback Default Persona
    return {"name": "OmniAgent", "instruction": "You are a helpful AI assistant."}

# ==========================================
# MAIN CHAT LOGIC
# ==========================================
async def process_chat(message: str, session_id: str, user_id: str, db: AsyncSession):
    
    # 1. Fetch User Settings & Persona
    user_settings = await get_user_integrations(user_id, db)
    bot_persona = await get_bot_persona(user_id, db) # <--- Persona Load kiya
    
    # 2. LLM Check
    llm_creds = user_settings.get('groq') or user_settings.get('openai')
    if not llm_creds:
        return "Please configure your AI Model in Settings."

    # 3. Build Tool Map for Router
    tools_map = {}
    for provider, config in user_settings.items():
        if provider in ['sanity', 'sql', 'mongodb']:
            if config.get('description'):
                tools_map[provider] = config['description']

    # 4. SEMANTIC DECISION (Router)
    selected_provider = None
    if tools_map:
        router = SemanticRouter() # Singleton Instance
        selected_provider = router.route(message, tools_map)
    
    response_text = ""
    provider_name = "general_chat"

    # 5. Route to Winner
    if selected_provider:
        print(f"👉 [Router] Selected Tool: {selected_provider.upper()}")
        try:
            if selected_provider == 'sanity':
                schema = user_settings['sanity'].get('schema_map', {})
                agent = get_cms_agent(user_id=user_id, schema_map=schema, llm_credentials=llm_creds)
                res = await agent.ainvoke({"input": message})
                response_text = str(res.get('output', ''))
                provider_name = "cms_agent"

            elif selected_provider == 'sql':
                role = "admin" if user_id == '99' else "customer"
                agent = get_secure_agent(int(user_id), role, user_settings['sql'], llm_credentials=llm_creds)
                res = await agent.ainvoke({"input": message})
                response_text = str(res.get('output', ''))
                provider_name = "sql_agent"

            elif selected_provider == 'mongodb':
                agent = get_nosql_agent(user_id, user_settings['mongodb'], llm_credentials=llm_creds)
                res = await agent.ainvoke({"input": message})
                response_text = str(res.get('output', ''))
                provider_name = "nosql_agent"

            # Anti-Hallucination
            if not response_text or "error" in response_text.lower():
                print(f"⚠️ [Router] Tool {selected_provider} failed. Triggering Fallback.")
                response_text = "" 

        except Exception as e:
            print(f"❌ [Router] Execution Failed: {e}")
            response_text = "" 

    # 6. Fallback / RAG (Using Custom Persona)
    if not response_text:
        print("👉 [Router] Fallback to RAG/General Chat...")
        try:
            llm = get_llm_model(credentials=llm_creds)
            
            # Context from Vector DB
            context = ""
            if 'qdrant' in user_settings:
                try:
                    vector_store = get_vector_store(credentials=user_settings['qdrant'])
                    docs = await vector_store.asimilarity_search(message, k=3)
                    if docs:
                        context = "\n\n".join([d.page_content for d in docs])
                except Exception as e:
                    print(f"⚠️ RAG Warning: {e}")
            
            # --- 🔥 DYNAMIC SYSTEM PROMPT ---
            system_instruction = f"""
            IDENTITY: You are '{bot_persona['name']}'.
            MISSION: {bot_persona['instruction']}
            
            CONTEXT FROM KNOWLEDGE BASE:
            {context if context else "No specific documents found."}
            
            Answer the user's question based on the context above or your general knowledge if permitted by your mission.
            """

            # History Load
            history = await get_chat_history(session_id, db)
            formatted_history = []
            for chat in history:
                formatted_history.append(HumanMessage(content=chat.human_message))
                if chat.ai_message: formatted_history.append(AIMessage(content=chat.ai_message))

            # LLM Call
            prompt = ChatPromptTemplate.from_messages([
                ("system", system_instruction),
                MessagesPlaceholder(variable_name="chat_history"),
                ("human", "{question}")
            ])
            chain = prompt | llm
            
            ai_response = await chain.ainvoke({"chat_history": formatted_history, "question": message})
            response_text = ai_response.content
            provider_name = "rag_fallback"

        except Exception as e:
            print(f"❌ Fallback Error: {e}")
            response_text = "I am currently unable to process your request. Please check your AI configuration."

    # 7. Save to DB
    await save_chat_to_db(db, session_id, message, response_text, provider_name)
    return response_text
# import json
# from sqlalchemy.ext.asyncio import AsyncSession
# from sqlalchemy.future import select

# # --- Model Imports ---
# from backend.src.models.chat import ChatHistory
# from backend.src.models.integration import UserIntegration
# from backend.src.models.user import User  # Added User model for Bot Persona

# # --- Dynamic Factory & Tool Imports ---
# from backend.src.services.llm.factory import get_llm_model
# from backend.src.services.vector_store.qdrant_adapter import get_vector_store
# from backend.src.services.security.pii_scrubber import PIIScrubber

# # --- Agents ---
# from backend.src.services.tools.secure_agent import get_secure_agent 
# from backend.src.services.tools.nosql_agent import get_nosql_agent 
# from backend.src.services.tools.cms_agent import get_cms_agent

# # --- Router ---
# from backend.src.services.routing.semantic_router import SemanticRouter

# # --- LangChain Core ---
# from langchain_core.messages import HumanMessage, AIMessage
# from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

# # ==========================================
# # HELPER FUNCTIONS
# # ==========================================

# async def get_user_integrations(user_id: str, db: AsyncSession) -> dict:
#     """Fetches active integrations and filters valid descriptions."""
#     if not user_id: return {}
    
#     query = select(UserIntegration).where(UserIntegration.user_id == user_id, UserIntegration.is_active == True)
#     result = await db.execute(query)
#     integrations = result.scalars().all()
    
#     settings = {}
#     for i in integrations:
#         try:
#             creds = json.loads(i.credentials)
#             creds['provider'] = i.provider
#             creds['schema_map'] = i.schema_map if i.schema_map else {}
            
#             # --- STRICT CHECK ---
#             # Agar Description NULL hai to dictionary mein mat daalo
#             # Taake Router confuse na ho
#             if i.profile_description:
#                 creds['description'] = i.profile_description
            
#             settings[i.provider] = creds
#         except (json.JSONDecodeError, TypeError):
#             continue
#     return settings

# async def save_chat_to_db(db: AsyncSession, session_id: str, human_msg: str, ai_msg: str, provider: str):
#     """Saves chat history with PII redaction."""
#     if not session_id: return
#     safe_human = PIIScrubber.scrub(human_msg)
#     safe_ai = PIIScrubber.scrub(ai_msg)
#     new_chat = ChatHistory(
#         session_id=session_id, human_message=safe_human, ai_message=safe_ai, provider=provider
#     )
#     db.add(new_chat)
#     await db.commit()

# async def get_chat_history(session_id: str, db: AsyncSession):
#     """Retrieves past conversation history."""
#     if not session_id: return []
#     query = select(ChatHistory).where(ChatHistory.session_id == session_id).order_by(ChatHistory.timestamp.asc())
#     result = await db.execute(query)
#     return result.scalars().all()

# async def get_bot_persona(user_id: str, db: AsyncSession):
#     """Fetches custom Bot Name and Instructions from User table."""
#     try:
#         result = await db.execute(select(User).where(User.id == int(user_id)))
#         user = result.scalars().first()
#         if user:
#             return {
#                 "name": getattr(user, "bot_name", "OmniAgent"),
#                 "instruction": getattr(user, "bot_instruction", "You are a helpful AI assistant.")
#             }
#     except Exception:
#         pass
#     return {"name": "OmniAgent", "instruction": "You are a helpful AI assistant."}

# # ==========================================
# # MAIN CHAT LOGIC
# # ==========================================
# async def process_chat(message: str, session_id: str, user_id: str, db: AsyncSession):
    
#     # 1. Fetch User Settings & Persona
#     user_settings = await get_user_integrations(user_id, db)
#     bot_persona = await get_bot_persona(user_id, db)
    
#     # 2. LLM Check
#     llm_creds = user_settings.get('groq') or user_settings.get('openai')
#     if not llm_creds:
#         return "Please configure your AI Model in Settings."

#     # 3. Build Tool Map for Router (STRICT FILTERING)
#     tools_map = {}
#     for provider, config in user_settings.items():
#         if provider in ['sanity', 'sql', 'mongodb']:
#             # Sirf tab add karo agar description exist karti hai
#             if config.get('description'):
#                 tools_map[provider] = config['description']
#             else:
#                 print(f"⚠️ [Router] Skipping {provider} - No Description found.")

#     # 4. SEMANTIC DECISION (Router)
#     selected_provider = None
#     if tools_map:
#         router = SemanticRouter() # Singleton Instance
#         selected_provider = router.route(message, tools_map)
#     else:
#         print("⚠️ [Router] No active tools with descriptions found.")
    
#     response_text = ""
#     provider_name = "general_chat"

#     # 5. Route to Winner (Tool Execution)
#     if selected_provider:
#         print(f"👉 [Router] Selected Tool: {selected_provider.upper()}")
#         try:
#             if selected_provider == 'sanity':
#                 schema = user_settings['sanity'].get('schema_map', {})
#                 agent = get_cms_agent(user_id=user_id, schema_map=schema, llm_credentials=llm_creds)
#                 res = await agent.ainvoke({"input": message})
#                 response_text = str(res.get('output', ''))
#                 provider_name = "cms_agent"

#             elif selected_provider == 'sql':
#                 role = "admin" if user_id == '99' else "customer"
#                 agent = get_secure_agent(int(user_id), role, user_settings['sql'], llm_credentials=llm_creds)
#                 res = await agent.ainvoke({"input": message})
#                 response_text = str(res.get('output', ''))
#                 provider_name = "sql_agent"

#             elif selected_provider == 'mongodb':
#                 agent = get_nosql_agent(user_id, user_settings['mongodb'], llm_credentials=llm_creds)
#                 res = await agent.ainvoke({"input": message})
#                 response_text = str(res.get('output', ''))
#                 provider_name = "nosql_agent"

#             # Anti-Hallucination Check
#             if not response_text or "error" in response_text.lower():
#                 print(f"⚠️ [Router] Tool {selected_provider} failed/empty. Triggering Fallback.")
#                 response_text = "" # Clears response to trigger fallback below

#         except Exception as e:
#             print(f"❌ [Router] Execution Failed: {e}")
#             response_text = "" 

#     # 6. Fallback / RAG (General Chat)
#     if not response_text:
#         print("👉 [Router] Fallback to RAG/General Chat...")
#         try:
#             llm = get_llm_model(credentials=llm_creds)
            
#             # Context from Vector DB
#             context = ""
#             if 'qdrant' in user_settings:
#                 try:
#                     vector_store = get_vector_store(credentials=user_settings['qdrant'])
#                     docs = await vector_store.asimilarity_search(message, k=3)
#                     if docs:
#                         context = "\n\n".join([d.page_content for d in docs])
#                 except Exception as e:
#                     print(f"⚠️ RAG Warning: {e}")
            
#             # --- DYNAMIC SYSTEM PROMPT (PERSONA) ---
#             system_instruction = f"""
#             IDENTITY: You are '{bot_persona['name']}'.
#             MISSION: {bot_persona['instruction']}
            
#             CONTEXT FROM KNOWLEDGE BASE:
#             {context if context else "No specific documents found."}
            
#             Answer the user's question based on the context above or your general knowledge if permitted by your mission.
#             """

#             # History Load
#             history = await get_chat_history(session_id, db)
#             formatted_history = []
#             for chat in history:
#                 formatted_history.append(HumanMessage(content=chat.human_message))
#                 if chat.ai_message: formatted_history.append(AIMessage(content=chat.ai_message))

#             # LLM Call
#             prompt = ChatPromptTemplate.from_messages([
#                 ("system", system_instruction),
#                 MessagesPlaceholder(variable_name="chat_history"),
#                 ("human", "{question}")
#             ])
#             chain = prompt | llm
            
#             ai_response = await chain.ainvoke({"chat_history": formatted_history, "question": message})
#             response_text = ai_response.content
#             provider_name = "rag_fallback"

#         except Exception as e:
#             print(f"❌ Fallback Error: {e}")
#             response_text = "I am currently unable to process your request. Please check your AI configuration."

#     # 7. Save to DB
#     await save_chat_to_db(db, session_id, message, response_text, provider_name)
#     return response_text