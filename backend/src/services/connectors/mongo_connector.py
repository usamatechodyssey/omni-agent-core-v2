
import pymongo
from typing import List, Dict, Any, Optional
from backend.src.services.connectors.base import NoSQLConnector

class MongoConnector(NoSQLConnector):
    def __init__(self, credentials: Dict[str, str]):
        """
        Initializes with user-specific credentials.
        """
        # User ki di hui connection string use karega
        # e.g., "mongodb+srv://user:pass@cluster..."
        self.uri = credentials.get("url")
        if not self.uri:
            raise ValueError("MongoDB connection URL ('url') is missing in credentials.")
            
        # Database ka naam URL se nikalne ki koshish (agar / ke baad hai)
        # Ya credentials se direct le lo
        self.db_name = credentials.get("database_name", self.uri.split("/")[-1].split("?")[0])
        
        self.client = None
        self.db = None
        
        # SSL/TLS arguments for cloud databases like Atlas
        self.connect_args = {
            'tls': True,
            'tlsAllowInvalidCertificates': True # Development ke liye OK, Production mein False hona chahiye
        }

    def connect(self):
        if not self.client:
            print(f"🔌 [NoSQL] Connecting to MongoDB Cluster...")
            try:
                # Use serverSelectionTimeoutMS to fail fast if connection is bad
                self.client = pymongo.MongoClient(self.uri, serverSelectionTimeoutMS=5000, **self.connect_args)
                # Ye line check karegi ke connection waqayi bana ya nahi
                self.client.server_info() 
                self.db = self.client[self.db_name]
                print("✅ [NoSQL] MongoDB Connection Successful.")
            except pymongo.errors.ConnectionFailure as e:
                print(f"❌ [NoSQL] MongoDB Connection Failed: {e}")
                raise e

    def disconnect(self):
        if self.client:
            self.client.close()
            self.client = None
            print("🔌 [NoSQL] Disconnected from MongoDB.")

    def get_schema_summary(self) -> str:
        self.connect()
        summary = []
        try:
            collections = self.db.list_collection_names()
            for col_name in collections:
                sample = self.db[col_name].find_one()
                if sample:
                    if '_id' in sample: del sample['_id']
                    keys = list(sample.keys())
                    summary.append(f"Collection: '{col_name}' -> Fields: {keys}")
        except Exception as e:
            return f"Error fetching schema: {e}"
        return "\n".join(summary)

    def find_one(self, collection: str, query: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        self.connect()
        try:
            result = self.db[collection].find_one(query)
            if result and '_id' in result:
                result['_id'] = str(result['_id'])
            return result
        except Exception as e:
            return None

    def find_many(self, collection: str, query: Dict[str, Any], limit: int = 5) -> List[Dict[str, Any]]:
        self.connect()
        try:
            cursor = self.db[collection].find(query).limit(limit)
            results = [doc for doc in cursor]
            for doc in results:
                if '_id' in doc:
                    doc['_id'] = str(doc['_id'])
            return results
        except Exception as e:
            return []