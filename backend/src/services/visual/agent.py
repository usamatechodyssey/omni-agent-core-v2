# import asyncio
# import json
# import requests
# import concurrent.futures
# from uuid import uuid4
# from sqlalchemy.future import select
# from qdrant_client.http import models

# # Internal Modules
# from backend.src.models.integration import UserIntegration
# from backend.src.models.ingestion import IngestionJob, JobStatus
# from backend.src.services.vector_store.qdrant_adapter import get_vector_store
# from backend.src.services.visual.engine import get_image_embedding

# # Connectors
# from backend.src.services.connectors.sanity_connector import SanityConnector
# from backend.src.services.connectors.shopify_connector import fetch_all_products as fetch_shopify
# from backend.src.services.connectors.woocommerce_connector import fetch_all_products as fetch_woo

# # --- OPTIMIZATION CONFIG ---
# BATCH_SIZE = 100 
# MAX_WORKERS = 20

# # --- 🔥 SAFE LOGGING HELPER ---
# async def update_job_safe(db_factory, job_id: int, status: str, processed=0, total=0, error=None):
#     try:
#         async with db_factory() as db:
#             result = await db.execute(select(IngestionJob).where(IngestionJob.id == job_id))
#             job = result.scalars().first()
#             if job:
#                 job.status = status
#                 job.items_processed = processed
#                 job.total_items = total
#                 if error:
#                     job.error_message = str(error)
#                 await db.commit()
#     except Exception as e:
#         print(f"⚠️ Status Update Failed: {e}")

# async def fetch_products_from_source(provider: str, credentials: dict):
#     products = []
#     print(f"🔄 [Visual Agent] Fetching products from {provider}...")
#     try:
#         if provider == 'sanity':
#             connector = SanityConnector(credentials)
#             query = """*[_type == "product" && defined(variants)]{
#                 _id, "slug": slug.current, "variants": variants[]{ _key, images[]{ asset->{url} } }
#             }"""
#             raw_data = connector.execute_query(query)
#             for item in raw_data:
#                 if not item.get('variants'): continue
#                 for variant in item['variants']:
#                     if not variant.get('images'): continue
#                     for img in variant['images']:
#                         if img.get('asset'):
#                             products.append({
#                                 "id": f"{item['_id']}_{variant['_key']}",
#                                 "image_path": img['asset']['url'],
#                                 "slug": item.get('slug'),
#                                 "product_id": item['_id']
#                             })
#         elif provider == 'shopify':
#             products = await asyncio.to_thread(fetch_shopify, credentials)
#         elif provider == 'woocommerce':
#             products = await asyncio.to_thread(fetch_woo, credentials)
#         return products
#     except Exception as e:
#         print(f"❌ Fetch Error: {e}")
#         return []

# def download_and_vectorize(product):
#     # Ensure we use the correct key for image path
#     image_url = product.get('image_path') or product.get('image_url')
    
#     if not image_url:
#         return None

#     try:
#         response = requests.get(image_url, timeout=5)
#         if response.status_code != 200: return None
#         image_bytes = response.content
#         vector = get_image_embedding(image_bytes)
#         if not vector: return None
#         return {"product": product, "vector": vector}
#     except Exception:
#         return None

# async def run_visual_sync(user_id: str, job_id: int, db_factory):
#     """
#     High Performance Sync: Uses ThreadPool for parallel processing.
#     """
#     print(f"🚀 [Visual Agent] Starting Optimized Sync Job {job_id} for User: {user_id}")
    
#     try:
#         await update_job_safe(db_factory, job_id, JobStatus.PROCESSING)

#         # 1. Credentials Fetch
#         async with db_factory() as db:
#             stmt = select(UserIntegration).where(
#                 UserIntegration.user_id == str(user_id),
#                 UserIntegration.is_active == True
#             )
#             result = await db.execute(stmt)
#             integrations = result.scalars().all()

#         qdrant_config = None
#         store_config = None
#         store_provider = None

#         for i in integrations:
#             if i.provider == 'qdrant':
#                 qdrant_config = json.loads(i.credentials)
#             elif i.provider in ['sanity', 'shopify', 'woocommerce']:
#                 store_config = json.loads(i.credentials)
#                 store_provider = i.provider

#         if not qdrant_config or not store_config:
#             await update_job_safe(db_factory, job_id, JobStatus.FAILED, error="Missing Database or Store connection.")
#             return

#         # 2. Connect Qdrant & Setup Collection
#         vector_store = get_vector_store(credentials=qdrant_config)
#         collection_name = "visual_search_products"
        
#         # Reset Collection
#         try:
#             vector_store.client.delete_collection(collection_name)
#         except: pass
        
#         vector_store.client.create_collection(
#             collection_name=collection_name,
#             vectors_config=models.VectorParams(size=2048, distance=models.Distance.COSINE)
#         )

#         # ✅ FIXED: Create Payload Index for 'user_id'
#         # Ye zaroori hai taake Qdrant filter query allow kare
#         print(f"🛠️ [Visual Agent] Creating index for user_id on {collection_name}...")
#         vector_store.client.create_payload_index(
#             collection_name=collection_name,
#             field_name="user_id",
#             field_schema=models.PayloadSchemaType.KEYWORD
#         )

#         # 3. Fetch Products
#         products = await fetch_products_from_source(store_provider, store_config)
#         total_products = len(products)
#         await update_job_safe(db_factory, job_id, JobStatus.PROCESSING, total=total_products)

#         if not products:
#             await update_job_safe(db_factory, job_id, JobStatus.COMPLETED, error="No products found.")
#             return

#         print(f"⚡ Processing {total_products} images in batches of {BATCH_SIZE}...")

#         # 4. OPTIMIZED BATCH PROCESSING
#         processed_count = 0
#         loop = asyncio.get_running_loop()
        
#         for i in range(0, total_products, BATCH_SIZE):
#             batch = products[i : i + BATCH_SIZE]
#             points = []

#             with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
#                 futures = [
#                     loop.run_in_executor(executor, download_and_vectorize, item) 
#                     for item in batch
#                 ]
#                 results = await asyncio.gather(*futures)

#             for res in results:
#                 if res:
#                     prod = res['product']
#                     # Use .get() to avoid KeyError if keys differ across providers
#                     img_url = prod.get('image_path') or prod.get('image_url')
                    
#                     points.append(models.PointStruct(
#                         id=str(uuid4()), 
#                         vector=res['vector'],
#                         payload={
#                             "product_id": prod.get('product_id'),
#                             "slug": prod.get('slug'),
#                             "image_url": img_url,
#                             "user_id": str(user_id),
#                             "source": store_provider
#                         }
#                     ))

#             if points:
#                 await asyncio.to_thread(
#                     vector_store.client.upsert,
#                     collection_name=collection_name, 
#                     points=points
#                 )
#                 processed_count += len(points)

#             # --- SAFE STATUS UPDATE ---
#             await update_job_safe(db_factory, job_id, JobStatus.PROCESSING, processed=processed_count, total=total_products)
#             print(f"   -> Batch {i//BATCH_SIZE + 1} done. ({processed_count}/{total_products})")

#         # Final Success
#         await update_job_safe(db_factory, job_id, JobStatus.COMPLETED, processed=processed_count, total=total_products)
#         print(f"🎉 Job {job_id} Complete. {processed_count} images indexed.")

#     except Exception as e:
#         print(f"❌ Job {job_id} Failed: {e}")
#         await update_job_safe(db_factory, job_id, JobStatus.FAILED, error=str(e))
import asyncio
import json
import requests
import concurrent.futures
from uuid import uuid4
from sqlalchemy.future import select
from qdrant_client.http import models

# Internal Modules
from backend.src.models.integration import UserIntegration
from backend.src.models.ingestion import IngestionJob, JobStatus
from backend.src.services.vector_store.qdrant_adapter import get_vector_store
from backend.src.services.visual.engine import get_image_embedding

# Connectors
from backend.src.services.connectors.sanity_connector import SanityConnector
from backend.src.services.connectors.shopify_connector import fetch_all_products as fetch_shopify
from backend.src.services.connectors.woocommerce_connector import fetch_all_products as fetch_woo

# --- OPTIMIZATION CONFIG ---
BATCH_SIZE = 100 
MAX_WORKERS = 20

# --- 🔥 SAFE LOGGING HELPER ---
async def update_job_safe(db_factory, job_id: int, status: str, processed=0, total=0, error=None, message=None):
    try:
        async with db_factory() as db:
            result = await db.execute(select(IngestionJob).where(IngestionJob.id == job_id))
            job = result.scalars().first()
            if job:
                job.status = status
                job.items_processed = processed
                job.total_items = total
                if error:
                    job.error_message = str(error)
                # Agar hum koi custom message save karna chahein
                if message:
                     print(f"📝 Job Log: {message}")
                await db.commit()
    except Exception as e:
        print(f"⚠️ Status Update Failed: {e}")

async def fetch_products_from_source(provider: str, credentials: dict):
    products = []
    print(f"🔄 [Visual Agent] Fetching products from {provider}...")
    try:
        if provider == 'sanity':
            connector = SanityConnector(credentials)
            query = """*[_type == "product" && defined(variants)]{
                _id, "slug": slug.current, "variants": variants[]{ _key, images[]{ asset->{url} } }
            }"""
            raw_data = connector.execute_query(query)
            for item in raw_data:
                if not item.get('variants'): continue
                for variant in item['variants']:
                    if not variant.get('images'): continue
                    for img in variant['images']:
                        if img.get('asset'):
                            products.append({
                                "id": f"{item['_id']}_{variant['_key']}",
                                "image_path": img['asset']['url'],
                                "slug": item.get('slug'),
                                "product_id": item['_id']
                            })
        elif provider == 'shopify':
            products = await asyncio.to_thread(fetch_shopify, credentials)
        elif provider == 'woocommerce':
            products = await asyncio.to_thread(fetch_woo, credentials)
        return products
    except Exception as e:
        print(f"❌ Fetch Error: {e}")
        return []

def download_and_vectorize(product):
    # Ensure we use the correct key for image path
    image_url = product.get('image_path') or product.get('image_url')
    
    if not image_url:
        return None

    try:
        response = requests.get(image_url, timeout=5)
        if response.status_code != 200: return None
        image_bytes = response.content
        vector = get_image_embedding(image_bytes)
        if not vector: return None
        return {"product": product, "vector": vector}
    except Exception:
        return None

# --- 🧠 SMART DIFF HELPER ---
async def get_current_qdrant_state(client, collection_name, user_id):
    """
    Qdrant se sirf IDs aur Image URLs fetch karta hai taake hum compare kar sakein.
    Returns: Dict { 'product_unique_id::image_url': 'qdrant_uuid' }
    """
    state = {}
    next_offset = None
    
    print(f"🕵️ Scanning existing Qdrant data for User: {user_id} in '{collection_name}'...")
    
    while True:
        # Scroll through points (Pagination)
        records, next_offset = await asyncio.to_thread(
            client.scroll,
            collection_name=collection_name,
            scroll_filter=models.Filter(
                must=[models.FieldCondition(key="user_id", match=models.MatchValue(value=str(user_id)))]
            ),
            limit=1000,
            with_payload=True,
            with_vectors=False, # Vector download karne ki zarurat nahi, slow hota hai
            offset=next_offset
        )
        
        for point in records:
            payload = point.payload or {}
            
            prod_id = payload.get("product_id")
            img_url = payload.get("image_url")
            
            if prod_id and img_url:
                # Composite key create karte hain uniquely identify karne ke liye
                key = f"{prod_id}::{img_url}"
                state[key] = point.id # Save Qdrant UUID (Delete karne ke kaam ayega)
        
        if next_offset is None:
            break
            
    print(f"✅ Found {len(state)} existing records in DB.")
    return state

async def run_visual_sync(user_id: str, job_id: int, db_factory):
    """
    🚀 Smart Incremental Sync:
    1. Fetch Source Data
    2. Fetch DB State
    3. Calculate Diff (Add/Delete)
    4. Execute Updates
    """
    print(f"🚀 [Visual Agent] Starting Smart Sync Job {job_id} for User: {user_id}")
    
    try:
        await update_job_safe(db_factory, job_id, JobStatus.PROCESSING)

        # 1. Credentials Fetch
        async with db_factory() as db:
            stmt = select(UserIntegration).where(
                UserIntegration.user_id == str(user_id),
                UserIntegration.is_active == True
            )
            result = await db.execute(stmt)
            integrations = result.scalars().all()

        qdrant_config = None
        store_config = None
        store_provider = None

        for i in integrations:
            if i.provider == 'qdrant':
                qdrant_config = json.loads(i.credentials)
            elif i.provider in ['sanity', 'shopify', 'woocommerce']:
                store_config = json.loads(i.credentials)
                store_provider = i.provider

        if not qdrant_config or not store_config:
            await update_job_safe(db_factory, job_id, JobStatus.FAILED, error="Missing Database or Store connection.")
            return

        # 2. Connect Qdrant & Check Collection
        vector_store = get_vector_store(credentials=qdrant_config)
        
         # 🔥 CRITICAL FIX: Explicitly look for 'visual_collection_name'
        # Agar user ne visual naam nahi diya, to default 'visual_search_products' use karo.
        # Hum 'collection_name' (jo chat ke liye hai) use NAHI karenge taake mix na ho.
        collection_name = qdrant_config.get("visual_collection_name", "visual_search_products")
        
        client = vector_store.client
        
        # Ensure Collection Exists
        if not client.collection_exists(collection_name):
             print(f"🛠️ Creating new collection: {collection_name}")
             client.create_collection(
                collection_name=collection_name,
                vectors_config=models.VectorParams(size=2048, distance=models.Distance.COSINE)
            )
             client.create_payload_index(
                collection_name=collection_name,
                field_name="user_id",
                field_schema=models.PayloadSchemaType.KEYWORD
            )

        # 3. Fetch Data from Source (Fresh List)
        source_products = await fetch_products_from_source(store_provider, store_config)
        if not source_products:
            await update_job_safe(db_factory, job_id, JobStatus.COMPLETED, error="No products found in store.")
            return

        # 4. Fetch Data from Qdrant (Existing List)
        # Map: "ProductID::ImageURL" -> QdrantUUID
        db_state = await get_current_qdrant_state(client, collection_name, user_id)

        # 5. 🧠 CALCULATE THE DIFF (The Magic)
        points_to_delete = []
        items_to_process = []
        
        # A. Identify New Items & Unchanged Items
        source_keys = set()
        
        for prod in source_products:
            prod_id = prod.get('product_id')
            img_url = prod.get('image_path') or prod.get('image_url')
            
            if not prod_id or not img_url: continue
            
            key = f"{prod_id}::{img_url}"
            source_keys.add(key)
            
            if key in db_state:
                # Already exists and Image URL is exact match -> SKIP (Save Time)
                continue
            else:
                # New Item (or URL changed, which creates a new key) -> PROCESS
                items_to_process.append(prod)

        # B. Identify Deleted Items
        # Agar koi cheez DB mein hai, lekin Source (source_keys) mein nahi, to wo delete hogi.
        for db_key, db_uuid in db_state.items():
            if db_key not in source_keys:
                points_to_delete.append(db_uuid)

        # Stats
        total_source = len(source_products)
        to_add_count = len(items_to_process)
        to_delete_count = len(points_to_delete)
        unchanged_count = total_source - to_add_count

        print(f"📊 Sync Analysis for User {user_id}:")
        print(f"   - Collection: {collection_name}")
        print(f"   - Total in Store: {total_source}")
        print(f"   - Unchanged (Skipping): {unchanged_count}")
        print(f"   - To Add/Update: {to_add_count}")
        print(f"   - To Delete (Removed from Store): {to_delete_count}")

        # 6. EXECUTE DELETE (Agar kuch delete karna ho)
        if points_to_delete:
            print(f"🗑️ Deleting {to_delete_count} obsolete records...")
            # Qdrant delete by Point ID (UUID)
            # Batching deletes if too many
            chunk_size = 1000
            for i in range(0, len(points_to_delete), chunk_size):
                chunk = points_to_delete[i:i + chunk_size]
                client.delete(
                    collection_name=collection_name,
                    points_selector=models.PointIdsList(points=chunk)
                )

        # 7. EXECUTE ADD/UPDATE (Batch Processing)
        if items_to_process:
            print(f"⚡ Processing {to_add_count} new images...")
            processed_count = 0
            
            # Initial status update
            await update_job_safe(db_factory, job_id, JobStatus.PROCESSING, total=to_add_count, processed=0)
            
            loop = asyncio.get_running_loop()
            
            for i in range(0, len(items_to_process), BATCH_SIZE):
                batch = items_to_process[i : i + BATCH_SIZE]
                points = []

                # Parallel Download & Vectorize
                with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                    futures = [
                        loop.run_in_executor(executor, download_and_vectorize, item) 
                        for item in batch
                    ]
                    results = await asyncio.gather(*futures)

                for res in results:
                    if res:
                        prod = res['product']
                        img_url = prod.get('image_path') or prod.get('image_url')
                        
                        points.append(models.PointStruct(
                            id=str(uuid4()), 
                            vector=res['vector'],
                            payload={
                                "product_id": prod.get('product_id'),
                                "slug": prod.get('slug'),
                                "image_url": img_url,
                                "user_id": str(user_id),
                                "source": store_provider
                            }
                        ))

                if points:
                    await asyncio.to_thread(
                        client.upsert,
                        collection_name=collection_name, 
                        points=points
                    )
                    processed_count += len(points)

                # Progress Update
                await update_job_safe(db_factory, job_id, JobStatus.PROCESSING, processed=processed_count, total=to_add_count)
                print(f"   -> Batch {i//BATCH_SIZE + 1} done. ({processed_count}/{to_add_count})")
        else:
            print("✨ No new images to process.")

        # Final Success
        final_msg = f"Sync Complete. Added: {to_add_count}, Deleted: {to_delete_count}, Skipped: {unchanged_count}"
        await update_job_safe(db_factory, job_id, JobStatus.COMPLETED, processed=to_add_count, total=to_add_count, message=final_msg)
        print(f"🎉 {final_msg}")

    except Exception as e:
        print(f"❌ Job {job_id} Failed: {e}")
        await update_job_safe(db_factory, job_id, JobStatus.FAILED, error=str(e))