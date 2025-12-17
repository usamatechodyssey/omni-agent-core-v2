import asyncio
import requests
import numpy as np
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from sqlalchemy.ext.asyncio import AsyncSession
from backend.src.models.ingestion import IngestionJob, JobStatus
from backend.src.services.vector_store.qdrant_adapter import get_vector_store
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from qdrant_client.http import models

# --- NEW IMPORT ---
from backend.src.services.ingestion.guardrail_factory import predict_with_model

# --- CONFIGURATION ---
MAX_PAGES_LIMIT = 50 

class SmartCrawler:
    def __init__(self, job_id: int, url: str, session_id: str, crawl_type: str, db: AsyncSession):
        self.job_id = job_id
        self.root_url = url
        self.session_id = session_id
        self.crawl_type = crawl_type
        self.db = db
        self.visited = set()
        self.vector_store = get_vector_store()
        # YAHAN SE MODEL LOAD HATA DIYA

    async def log_status(self, status: str, processed=0, total=0, error=None):
        try:
            job = await self.db.get(IngestionJob, self.job_id)
            if job:
                job.status = status
                job.pages_processed = processed
                job.total_pages_found = total
                if error:
                    job.error_message = str(error)
                await self.db.commit()
        except Exception as e:
            print(f"DB Log Error: {e}")

    async def is_ai_unsafe(self, text: str, url: str) -> bool: # <--- Async bana diya
        """
        Non-blocking AI Check using Factory.
        """
        sample_text = text[:300] + " ... " + text[len(text)//2 : len(text)//2 + 300]
        label = "This is an e-commerce product page with price, buy button, or shopping cart."
        
        # --- FIX: Call Factory Async Function ---
        # Ab ye server ko block nahi karega
        scores = await predict_with_model(sample_text, label)
        
        # Softmax Calculation
        probs = np.exp(scores) / np.sum(np.exp(scores))
        entailment_score = probs[1]
        
        print("\n" + "="*60)
        print(f"🤖 AI ANALYSIS REPORT for: {url}")
        print("-" * 60)
        print(f"📊 Scores -> Contradiction: {probs[0]:.2f}, Entailment: {probs[1]:.2f}, Neutral: {probs[2]:.2f}")
        print(f"🎯 Target Score (Entailment): {entailment_score:.4f} (Threshold: 0.5)")
        
        if entailment_score > 0.5:
            print(f"⛔ DECISION: BLOCKED")
            print("="*60 + "\n")
            return True
        else:
            print(f"✅ DECISION: ALLOWED")
            print("="*60 + "\n")
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
                        must=[
                            models.FieldCondition(
                                key="metadata.source",
                                match=models.MatchValue(value=self.root_url)
                            )
                        ]
                    )
                )
            )
        except Exception as e:
            print(f"Warning: Clean data failed: {e}")

    async def process_page(self, url: str, soup: BeautifulSoup) -> bool:
        for script in soup(["script", "style", "nav", "footer", "iframe", "noscript", "svg"]):
            script.extract()
            
        text = soup.get_text(separator=" ", strip=True)
        
        if len(text) < 200: 
            print(f"⚠️ Skipping {url} (Not enough text: {len(text)} chars)")
            return False

        # --- AWAIT HERE ---
        # Ab hum 'await' use kar rahe hain taake ye background mein chale
        if await self.is_ai_unsafe(text, url):
            return False

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
            await self.log_status(JobStatus.PROCESSING)
            await self.clean_existing_data()

            queue = [self.root_url]
            self.visited.add(self.root_url)
            total_processed = 0

            while queue and total_processed < MAX_PAGES_LIMIT:
                current_url = queue.pop(0)
                
                response = await self.fetch_page(current_url)
                if not response or response.status_code != 200:
                    continue

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