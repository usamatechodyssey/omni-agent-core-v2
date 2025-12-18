import asyncio
import requests
import json # Credentials decode karne ke liye
import numpy as np
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select # Query karne ke liye

from backend.src.models.ingestion import IngestionJob, JobStatus
from backend.src.models.integration import UserIntegration # integration model import kiya
from backend.src.services.vector_store.qdrant_adapter import get_vector_store
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from qdrant_client.http import models

from backend.src.services.ingestion.guardrail_factory import predict_with_model

MAX_PAGES_LIMIT = 50 

class SmartCrawler:
    # 1. Init mein 'user_id' add kiya taake hum uski settings dhoond saken
    def __init__(self, job_id: int, url: str, session_id: str, crawl_type: str, db: AsyncSession, user_id: str):
        self.job_id = job_id
        self.root_url = url
        self.session_id = session_id
        self.crawl_type = crawl_type
        self.db = db
        self.user_id = user_id # Owner ID
        self.visited = set()
        self.vector_store = None # Shuru mein None rakhein, verification ke baad fill hoga

    async def log_status(self, status: str, processed=0, total=0, error=None):
        try:
            # SQL Alchemy 2.0 style query
            result = await self.db.execute(select(IngestionJob).where(IngestionJob.id == self.job_id))
            job = result.scalars().first()
            if job:
                job.status = status
                job.items_processed = processed # Column name match karein (items_processed)
                job.total_items = total
                if error:
                    job.error_message = str(error)
                await self.db.commit()
        except Exception as e:
            print(f"DB Log Error: {e}")

    # --- NEW: STRICT DATABASE VERIFICATION SKILL ---
    async def verify_and_connect_db(self) -> bool:
        """
        Check if user has a valid Qdrant Cloud integration.
        """
        print(f"🔍 Verifying Database for User ID: {self.user_id}")
        try:
            stmt = select(UserIntegration).where(
                UserIntegration.user_id == str(self.user_id),
                UserIntegration.provider == "qdrant",
                UserIntegration.is_active == True
            )
            result = await self.db.execute(stmt)
            integration = result.scalars().first()

            if not integration:
                error_msg = "❌ No Qdrant Cloud connected. Please go to 'Settings' and connect your database first."
                print(error_msg)
                await self.log_status(JobStatus.FAILED, error=error_msg)
                return False

            # User ki encrypted/json credentials nikalen
            creds = json.loads(integration.credentials) if isinstance(integration.credentials, str) else integration.credentials
            
            # Smart Adapter ko user ki chabiyan (keys) bhejein
            self.vector_store = get_vector_store(credentials=creds)
            return True

        except Exception as e:
            await self.log_status(JobStatus.FAILED, error=f"Database Connection Error: {str(e)}")
            return False

    async def is_ai_unsafe(self, text: str, url: str) -> bool:
        sample_text = text[:300] + " ... " + text[len(text)//2 : len(text)//2 + 300]
        label = "This is an e-commerce product page with price, buy button, or shopping cart."
        
        scores = await predict_with_model(sample_text, label)
        probs = np.exp(scores) / np.sum(np.exp(scores))
        entailment_score = probs[1]
        
        if entailment_score > 0.5:
            print(f"⛔ AI BLOCKED (E-commerce): {url}")
            return True
        return False

    async def fetch_page(self, url: str):
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            return await asyncio.to_thread(requests.get, url, headers=headers, timeout=10)
        except Exception:
            return None

    async def clean_existing_data(self):
        print(f"INFO: Cleaning old data for source: {self.root_url}")
        try:
            self.vector_store.client.delete(
                collection_name=self.vector_store.collection_name,
                points_selector=models.FilterSelector(
                    filter=models.Filter(
                        must=[models.FieldCondition(key="metadata.source", match=models.MatchValue(value=self.root_url))]
                    )
                )
            )
        except Exception as e:
            print(f"Warning: Clean data failed: {e}")

    async def process_page(self, url: str, soup: BeautifulSoup) -> bool:
        for script in soup(["script", "style", "nav", "footer", "iframe", "noscript", "svg"]):
            script.extract()
            
        text = soup.get_text(separator=" ", strip=True)
        if len(text) < 200: return False

        if await self.is_ai_unsafe(text, url): return False

        splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        docs = [Document(page_content=text, metadata={
            "source": self.root_url, 
            "specific_url": url,
            "session_id": self.session_id,
            "type": "web_scrape"
        })]
        split_docs = splitter.split_documents(docs)

        await self.vector_store.aadd_documents(split_docs)
        return True

    async def start(self):
        try:
            # 1. PEHLA KAAM: Database check karo
            db_ready = await self.verify_and_connect_db()
            if not db_ready:
                return # Stop process if no DB

            await self.log_status(JobStatus.PROCESSING)
            await self.clean_existing_data()

            queue = [self.root_url]
            self.visited.add(self.root_url)
            total_processed = 0

            while queue and total_processed < MAX_PAGES_LIMIT:
                current_url = queue.pop(0)
                response = await self.fetch_page(current_url)
                if not response or response.status_code != 200: continue

                soup = BeautifulSoup(response.content, 'html.parser')
                success = await self.process_page(current_url, soup)
                
                if not success:
                    if current_url == self.root_url:
                        await self.log_status(JobStatus.FAILED, error="Root URL blocked. Identified as E-commerce.")
                        return
                    continue

                total_processed += 1
                
                if self.crawl_type == "full_site":
                    for link in soup.find_all('a', href=True):
                        full_link = urljoin(self.root_url, link['href'])
                        if self.root_url in full_link and full_link not in self.visited:
                            self.visited.add(full_link)
                            queue.append(full_link)

                await self.log_status(JobStatus.PROCESSING, processed=total_processed, total=len(queue)+total_processed)
                await asyncio.sleep(0.5) 

            await self.log_status(JobStatus.COMPLETED, processed=total_processed)
            print(f"SUCCESS: Crawling finished. Processed {total_processed} pages.")

        except Exception as e:
            print(f"ERROR: Crawling failed: {e}")
            await self.log_status(JobStatus.FAILED, error=str(e))