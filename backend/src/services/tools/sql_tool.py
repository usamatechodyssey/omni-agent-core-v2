
from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits import SQLDatabaseToolkit
from backend.src.services.llm.factory import get_llm_model
from typing import Optional, Dict

# --- DYNAMIC FUNCTIONS ---

def get_database_connection(db_credentials: Dict[str, str]) -> SQLDatabase:
    """
    User ki di hui connection string se connect karta hai.
    """
    db_uri = db_credentials.get("url")
    if not db_uri:
        raise ValueError("SQL Database URL not found in user's settings.")

    # --- FIX for SQLAlchemy Async Driver ---
    # Ensure the URL is compatible with the synchronous SQLDatabase object
    if "+asyncpg" in db_uri:
        db_uri = db_uri.replace("+asyncpg", "") # Sync object needs sync driver
    
    print(f"INFO: [SQL Tool] Connecting to user's SQL DB: {db_uri[:30]}...")

    db = SQLDatabase.from_uri(
        db_uri,
        sample_rows_in_table_info=2 # 2 samples kafi hain
    )
    return db

def get_sql_toolkit(
    db_credentials: Dict[str, str], 
    llm_credentials: Optional[Dict[str, str]] = None
) -> SQLDatabaseToolkit:
    """
    User ke DB aur User ke LLM se Toolkit banata hai.
    """
    # 1. Connect to User's DB
    db = get_database_connection(db_credentials)
    
    # 2. Load User's LLM
    llm = get_llm_model(credentials=llm_credentials)
    
    # 3. Create Toolkit
    toolkit = SQLDatabaseToolkit(db=db, llm=llm)
    return toolkit