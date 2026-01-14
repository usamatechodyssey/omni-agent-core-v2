# # backend/src/api/routes/visual.py
# import json
# import asyncio
# from fastapi import (
#     APIRouter,
#     Depends,
#     UploadFile,
#     File,
#     HTTPException,
#     BackgroundTasks
# )
# from sqlalchemy.ext.asyncio import AsyncSession
# from sqlalchemy.future import select
# from qdrant_client import QdrantClient
# from qdrant_client.http import models

# # =========================
# # Auth & DB Imports
# # =========================
# from backend.src.api.routes.deps import get_current_user
# from backend.src.db.session import get_db, AsyncSessionLocal
# from backend.src.models.user import User
# from backend.src.models.integration import UserIntegration
# from backend.src.models.ingestion import IngestionJob, JobStatus

# # =========================
# # Visual Services
# # =========================
# from backend.src.services.visual.engine import get_image_embedding
# from backend.src.services.visual.agent import run_visual_sync

# router = APIRouter()

# # ======================================================
# # 1. VISUAL SYNC (BACKGROUND)
# # ======================================================
# @router.post("/visual/sync")
# async def trigger_visual_sync(
#     background_tasks: BackgroundTasks,
#     db: AsyncSession = Depends(get_db),
#     current_user: User = Depends(get_current_user)
# ):
#     try:
#         job = IngestionJob(
#             session_id=f"visual_sync_{current_user.id}",
#             ingestion_type="visual_sync",
#             source_name="Store Integration (Visual)",
#             status=JobStatus.PENDING,
#             total_items=0,
#             items_processed=0
#         )

#         db.add(job)
#         await db.commit()
#         await db.refresh(job)

#         background_tasks.add_task(
#             run_visual_sync,
#             str(current_user.id),
#             job.id,
#             AsyncSessionLocal
#         )

#         return {
#             "status": "processing",
#             "message": "Visual Sync started successfully.",
#             "job_id": job.id
#         }

#     except Exception as e:
#         print(f"❌ Visual Sync Failed: {e}")
#         raise HTTPException(status_code=500, detail=str(e))


# # ======================================================
# # 2. VISUAL SEARCH (QDRANT 1.16.1 – DEDUPLICATED)
# # ======================================================
# @router.post("/visual/search")
# async def search_visual_products(
#     file: UploadFile = File(...),
#     db: AsyncSession = Depends(get_db),
#     current_user: User = Depends(get_current_user)
# ):
#     """
#     Image → Embedding → Qdrant query_points → Unique Results
#     """

#     # ----------------------------------
#     # 1. Load Qdrant Integration
#     # ----------------------------------
#     stmt = select(UserIntegration).where(
#         UserIntegration.user_id == str(current_user.id),
#         UserIntegration.provider == "qdrant",
#         UserIntegration.is_active == True
#     )

#     result = await db.execute(stmt)
#     integration = result.scalars().first()

#     if not integration:
#         raise HTTPException(
#             status_code=400,
#             detail="Qdrant integration not found."
#         )

#     try:
#         creds = json.loads(integration.credentials)
#         qdrant_url = creds["url"]
#         qdrant_key = creds["api_key"]
#         collection_name = "visual_search_products"
#     except Exception:
#         raise HTTPException(
#             status_code=500,
#             detail="Invalid Qdrant credentials format."
#         )

#     # ----------------------------------
#     # 2. Image → Vector
#     # ----------------------------------
#     try:
#         image_bytes = await file.read()
#         vector = get_image_embedding(image_bytes)

#         if not vector:
#             raise ValueError("Empty embedding returned")
#     except Exception as e:
#         raise HTTPException(
#             status_code=400,
#             detail=f"Image processing failed: {e}"
#         )

#     # ----------------------------------
#     # 3. Qdrant Search (query_points)
#     # ----------------------------------
#     try:
#         def run_search():
#             client = QdrantClient(
#                 url=qdrant_url,
#                 api_key=qdrant_key
#             )

#             # NOTE: Limit increased to 25 to ensure we have enough results 
#             # after removing duplicates (variants with same image).
#             return client.query_points(
#                 collection_name=collection_name,
#                 query=vector,
#                 limit=25,
#                 with_payload=True,
#                 query_filter=models.Filter(
#                     must=[
#                         models.FieldCondition(
#                             key="user_id",
#                             match=models.MatchValue(
#                                 value=str(current_user.id)
#                             )
#                         )
#                     ]
#                 )
#             )

#         # Execute search in thread
#         search_response = await asyncio.to_thread(run_search)
        
#         # Get points from response object
#         hits = search_response.points

#         # ----------------------------------
#         # 4. Format & Remove Duplicates
#         # ----------------------------------
#         results = []
#         seen_products = set()  # To track unique product IDs

#         for hit in hits:
#             if hit.score < 0.50:
#                 continue

#             payload = hit.payload or {}
#             product_id = payload.get("product_id")

#             # ✅ DUPLICATE CHECK:
#             # Agar ye product ID pehle aa chuka hai (higher score ke sath),
#             # toh is wale ko skip karo.
#             if product_id in seen_products:
#                 continue
            
#             seen_products.add(product_id)

#             results.append({
#                 "product_id": product_id,
#                 "slug": payload.get("slug"),
#                 "image_path": payload.get("image_url"),
#                 "similarity": hit.score
#             })

#             # Optional: Limit final output to top 10 unique products
#             if len(results) >= 10:
#                 break

#         return {"results": results}

#     except Exception as e:
#         print(f"❌ Visual Search Failed: {e}")

#         msg = str(e)
#         if "dimension" in msg.lower():
#             msg = "Vector dimension mismatch. Please re-run Visual Sync."
#         if "not found" in msg.lower():
#             msg = "Visual search collection not found. Run Sync first."

#         raise HTTPException(status_code=500, detail=msg)
import json
import asyncio
from fastapi import (
    APIRouter,
    Depends,
    UploadFile,
    File,
    HTTPException,
    BackgroundTasks,
    Request,  # <--- NEW: Request object for headers/origin check
    status
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from qdrant_client import QdrantClient
from qdrant_client.http import models

# =========================
# Auth & DB Imports
# =========================
# 👇 Change: Humne naya auth method import kiya
from backend.src.api.routes.deps import get_current_user, get_current_user_by_api_key
from backend.src.db.session import get_db, AsyncSessionLocal
from backend.src.models.user import User
from backend.src.models.integration import UserIntegration
from backend.src.models.ingestion import IngestionJob, JobStatus

# =========================
# Visual Services
# =========================
from backend.src.services.visual.engine import get_image_embedding
from backend.src.services.visual.agent import run_visual_sync

router = APIRouter()

# ======================================================
# HELPER: DOMAIN LOCK SECURITY 🔐
# ======================================================
def check_domain_authorization(user: User, request: Request):
    """
    Check if the request is coming from an allowed domain.
    Logic copied from chat.py for consistency.
    """
    # 1. Browser headers check karein
    client_origin = request.headers.get("origin") or request.headers.get("referer") or ""
    
    # 2. Agar user ne "*" set kiya hai, to sab allow hai
    if user.allowed_domains == "*":
        return True
        
    # 3. Allowed domains ki list banao
    allowed = [d.strip() for d in user.allowed_domains.split(",")]
    
    # 4. Check karo ke origin match karta hai ya nahi
    is_authorized = any(domain in client_origin for domain in allowed)
    
    if not is_authorized:
        print(f"🚫 [Visual Security] Blocked unauthorized domain: {client_origin}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Domain not authorized to use this API."
        )

# ======================================================
# 1. VISUAL SYNC (Dashboard Only - Uses JWT)
# ======================================================
@router.post("/visual/sync")
async def trigger_visual_sync(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    # NOTE: Sync humesha Dashboard se hota hai, isliye JWT (get_current_user) rakha hai.
    current_user: User = Depends(get_current_user)
):
    try:
        job = IngestionJob(
            session_id=f"visual_sync_{current_user.id}",
            ingestion_type="visual_sync",
            source_name="Store Integration (Visual)",
            status=JobStatus.PENDING,
            total_items=0,
            items_processed=0
        )

        db.add(job)
        await db.commit()
        await db.refresh(job)

        background_tasks.add_task(
            run_visual_sync,
            str(current_user.id),
            job.id,
            AsyncSessionLocal
        )

        return {
            "status": "processing",
            "message": "Visual Sync started successfully.",
            "job_id": job.id
        }

    except Exception as e:
        print(f"❌ Visual Sync Failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ======================================================
# 2. VISUAL SEARCH (Public Widget - Uses API Key + Domain Lock)
# ======================================================
@router.post("/visual/search")
async def search_visual_products(
    request: Request, # <--- Browser Request Access
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    # 🔥 CHANGE: Ab ye API Key se authenticate hoga (Widget Friendly)
    current_user: User = Depends(get_current_user_by_api_key)
):
    """
    Image → Embedding → Qdrant query_points → Unique Results
    Secured by API Key & Domain Lock.
    """
    
    # 🔒 1. Domain Security Check
    check_domain_authorization(current_user, request)

    # ----------------------------------
    # 2. Load Qdrant Integration
    # ----------------------------------
    stmt = select(UserIntegration).where(
        UserIntegration.user_id == str(current_user.id),
        UserIntegration.provider == "qdrant",
        UserIntegration.is_active == True
    )

    result = await db.execute(stmt)
    integration = result.scalars().first()

    if not integration:
        raise HTTPException(
            status_code=400,
            detail="Qdrant integration not found."
        )

    try:
        creds = json.loads(integration.credentials)
        qdrant_url = creds["url"]
        qdrant_key = creds["api_key"]
       # 🔥 CHANGE: Look for 'visual_collection_name' specifically
        # This prevents conflict with Chat's 'collection_name'
        collection_name = creds.get("visual_collection_name", "visual_search_products")
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Invalid Qdrant credentials format."
        )

    # ----------------------------------
    # 3. Image → Vector
    # ----------------------------------
    try:
        image_bytes = await file.read()
        vector = get_image_embedding(image_bytes)

        if not vector:
            raise ValueError("Empty embedding returned")
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Image processing failed: {e}"
        )

    # ----------------------------------
    # 4. Qdrant Search (query_points)
    # ----------------------------------
    try:
        def run_search():
            client = QdrantClient(
                url=qdrant_url,
                api_key=qdrant_key
            )

            # Limit 25 taake duplicates hatane ke baad bhi kafi results bachein
            return client.query_points(
                collection_name=collection_name,
                query=vector,
                limit=25,
                with_payload=True,
                query_filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="user_id",
                            match=models.MatchValue(
                                value=str(current_user.id)
                            )
                        )
                    ]
                )
            )

        # Execute search in thread
        search_response = await asyncio.to_thread(run_search)
        
        # Get points from response object
        hits = search_response.points

        # ----------------------------------
        # 5. Format & Remove Duplicates
        # ----------------------------------
        results = []
        seen_products = set()  # To track unique product IDs

        for hit in hits:
            if hit.score < 0.50:
                continue

            payload = hit.payload or {}
            product_id = payload.get("product_id")

            # ✅ DUPLICATE CHECK
            if product_id in seen_products:
                continue
            
            seen_products.add(product_id)

            results.append({
                "product_id": product_id,
                "slug": payload.get("slug"),
                "image_path": payload.get("image_url"),
                "similarity": hit.score
            })

            # Optional: Limit final output to top 10 unique products
            if len(results) >= 10:
                break

        return {"results": results}

    except Exception as e:
        print(f"❌ Visual Search Failed: {e}")

        msg = str(e)
        if "dimension" in msg.lower():
            msg = "Vector dimension mismatch. Please re-run Visual Sync."
        if "not found" in msg.lower():
            msg = "Visual search collection not found. Run Sync first."

        raise HTTPException(status_code=500, detail=msg)