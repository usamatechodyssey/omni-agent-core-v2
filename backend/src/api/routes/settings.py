
import json
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import create_engine, inspect
from pymongo import MongoClient
from pydantic import BaseModel
from typing import Dict, List, Any, Tuple

# --- Internal Imports ---
from backend.src.db.session import get_db
from backend.src.models.user import User
from backend.src.models.integration import UserIntegration
from backend.src.api.routes.deps import get_current_user

# --- Connectors ---
from backend.src.services.connectors.sanity_connector import SanityConnector

# --- AI & LLM ---
from backend.src.services.llm.factory import get_llm_model
from langchain_core.messages import HumanMessage

router = APIRouter()

# ==========================================
# DATA MODELS
# ==========================================
class IntegrationUpdateRequest(BaseModel):
    provider: str
    credentials: Dict[str, Any]

class RefreshSchemaRequest(BaseModel):
    provider: str 

class ConnectedServiceResponse(BaseModel):
    provider: str
    is_active: bool
    description: str | None = None
    last_updated: str | None = None

class UserSettingsResponse(BaseModel):
    user_email: str
    connected_services: List[ConnectedServiceResponse]

# --- NEW: Bot Profile Model ---
class BotSettingsRequest(BaseModel):
    bot_name: str
    bot_instruction: str

# ==========================================
# THE DYNAMIC PROFILER (No Bias) 🧠
# ==========================================

async def generate_data_profile(schema_map: dict, provider: str) -> str:
    """
    Ye function bina kisi bias ke, sirf data structure dekh kar keywords nikalta hai.
    """
    try:
        if not schema_map: return f"Connected to {provider}."
        
        llm = get_llm_model() 
        schema_str = json.dumps(schema_map)[:3500] 
        
        prompt = f"""
        Act as a Database Architect. Your job is to analyze the provided Database Schema and generate a 'Semantic Description' for an AI Router.

        --- INPUT SCHEMA ({provider}) ---
        {schema_str}

        --- INSTRUCTIONS ---
        1. Analyze the Table Names (or Collections/Types) and Field Names deeply.
        2. Identify the core "Business Concepts" represented in this data.
        3. Construct a dense, keyword-rich summary that describes EXACTLY what is in this database.
        4. **STRICT RULE:** Do NOT use generic words like "solution" or "platform". Use specific nouns found in the schema (e.g., "invoices", "appointments", "inventory", "cement", "users").
        5. Do NOT guess. Only describe what you see in the schema keys.

        --- OUTPUT FORMAT ---
        Write a single paragraph (approx 30 words) describing the data contents.
        Description:
        """
        
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        return response.content.strip()
    except Exception as e:
        print(f"⚠️ Profiling failed: {e}")
        return f"Contains data from {provider}."

async def perform_discovery(provider: str, credentials: Dict[str, Any]) -> Tuple[Dict, str]:
    """
    Common discovery function for Connect and Refresh.
    """
    schema_map = {}
    description = None
    
    try:
        # --- CASE A: SANITY ---
        if provider == 'sanity':
            connector = SanityConnector(credentials=credentials)
            if connector.connect():
                schema_map = connector.fetch_schema_structure()
                description = await generate_data_profile(schema_map, 'Sanity CMS')

        # --- CASE B: SQL DATABASE ---
        elif provider == 'sql':
            db_url = credentials.get('connection_string') or credentials.get('url')
            if db_url:
                engine = create_engine(db_url)
                inspector = inspect(engine)
                tables = inspector.get_table_names()
                
                schema_map = {"tables": tables}
                if len(tables) < 15:
                    for t in tables:
                        try:
                            cols = [c['name'] for c in inspector.get_columns(t)]
                            schema_map[t] = cols
                        except: pass
                
                description = await generate_data_profile(schema_map, 'SQL Database')

        # --- CASE C: MONGODB ---
        elif provider == 'mongodb':
            mongo_uri = credentials.get('connection_string') or credentials.get('url')
            if mongo_uri:
                client = MongoClient(mongo_uri)
                db_name = client.get_database().name
                collections = client[db_name].list_collection_names()
                
                schema_map = {"collections": collections}
                for col in collections[:5]: 
                    one_doc = client[db_name][col].find_one()
                    if one_doc:
                        keys = [k for k in list(one_doc.keys()) if not k.startswith('_')]
                        schema_map[col] = keys

                description = await generate_data_profile(schema_map, 'MongoDB NoSQL')

        # --- CASE D: QDRANT / OTHERS ---
        elif provider == 'qdrant':
            description = "Contains uploaded documents, policies, and knowledge base."
        
        return schema_map, description

    except Exception as e:
        print(f"❌ Discovery Error for {provider}: {e}")
        return {}, f"Connected to {provider} (Auto-discovery failed: {str(e)})"

# ==========================================
# 1. SAVE / CONNECT INTEGRATION
# ==========================================
@router.post("/settings/integration", status_code=status.HTTP_201_CREATED)
async def save_or_update_integration(
    data: IntegrationUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        query = select(UserIntegration).where(
            UserIntegration.user_id == str(current_user.id),
            UserIntegration.provider == data.provider
        )
        result = await db.execute(query)
        existing_integration = result.scalars().first()

        credentials_json = json.dumps(data.credentials)
        schema_map, description = await perform_discovery(data.provider, data.credentials)

        if existing_integration:
            existing_integration.credentials = credentials_json
            existing_integration.is_active = True
            if schema_map: existing_integration.schema_map = schema_map
            if description: existing_integration.profile_description = description
            message = f"Integration for {data.provider} updated."
        else:
            new_integration = UserIntegration(
                user_id=str(current_user.id),
                provider=data.provider,
                is_active=True,
                schema_map=schema_map,
                profile_description=description
            )
            new_integration.credentials = credentials_json
            db.add(new_integration)
            message = f"Integration for {data.provider} connected."

        await db.commit()
        return {
            "message": message, 
            "provider": data.provider, 
            "profile": description
        }

    except Exception as e:
        await db.rollback()
        print(f"❌ Error saving integration: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ==========================================
# 2. REFRESH SCHEMA
# ==========================================
@router.post("/settings/integration/refresh")
async def refresh_integration_schema(
    data: RefreshSchemaRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    print(f"🔄 Refreshing schema for {data.provider} (User: {current_user.id})")
    
    try:
        stmt = select(UserIntegration).where(
            UserIntegration.user_id == str(current_user.id),
            UserIntegration.provider == data.provider
        )
        result = await db.execute(stmt)
        integration = result.scalars().first()

        if not integration:
            raise HTTPException(status_code=404, detail="Integration not found. Please connect first.")

        creds_str = integration.credentials 
        creds_dict = json.loads(creds_str)

        new_schema, new_description = await perform_discovery(data.provider, creds_dict)

        if new_schema:
            integration.schema_map = dict(new_schema)
        
        if new_description:
            integration.profile_description = new_description
            
        await db.commit()
        
        return {
            "message": "Schema and profile refreshed successfully!", 
            "provider": data.provider,
            "new_profile": new_description
        }

    except Exception as e:
        print(f"❌ Refresh Failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ==========================================
# 3. UPDATE BOT PROFILE (NEW ✅)
# ==========================================
@router.post("/settings/bot-profile")
async def update_bot_profile(
    data: BotSettingsRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    User yahan apne chatbot ka Naam aur Role set karega.
    """
    try:
        current_user.bot_name = data.bot_name
        current_user.bot_instruction = data.bot_instruction
        
        db.add(current_user)
        await db.commit()
        
        return {
            "message": "Bot profile updated successfully!", 
            "bot_name": data.bot_name,
            "bot_instruction": data.bot_instruction
        }
    except Exception as e:
        print(f"❌ Bot Profile Update Failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ==========================================
# 4. GET USER INTEGRATIONS
# ==========================================
@router.get("/settings/integrations", response_model=UserSettingsResponse)
async def get_user_integrations(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = select(UserIntegration).where(
        UserIntegration.user_id == str(current_user.id)
    )
    result = await db.execute(query)
    integrations = result.scalars().all()
    
    connected_services = [
        ConnectedServiceResponse(
            provider=i.provider, 
            is_active=i.is_active,
            description=i.profile_description, 
            last_updated=str(i.updated_at) if i.updated_at else str(i.created_at)
        )
        for i in integrations
    ]
    
    return {
        "user_email": current_user.email,
        "connected_services": connected_services
    }