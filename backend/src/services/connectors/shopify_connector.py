# backend/src/services/connectors/shopify_connector.py

import shopify
import time
from typing import List, Dict, Any

class ShopifyConnector:
    def __init__(self, credentials: Dict[str, str]):
        self.shop_url = credentials.get("shop_url")
        self.access_token = credentials.get("access_token")
        self.api_version = credentials.get("api_version", "2024-01") # Default stable version

        if not self.shop_url or not self.access_token:
            raise ValueError("Shopify credentials (shop_url, access_token) are required.")

        # Session Setup
        self.session = shopify.Session(self.shop_url, self.api_version, self.access_token)

    def fetch_all_products(self) -> List[Dict[str, Any]]:
        """
        Shopify Admin API se saare products aur unki images fetch karta hai.
        Pagination handle karta hai taake saara data aaye.
        """
        print(f"🛍️ [Shopify] Connecting to {self.shop_url}...")
        shopify.ShopifyResource.activate_session(self.session)
        
        product_list = []
        
        try:
            # Pehla page fetch karein (Limit 250 max hai)
            page = shopify.Product.find(limit=250)
            
            while page:
                for product in page:
                    if not product.images:
                        continue
                    
                    # Har image ko process karein
                    for image in product.images:
                        product_list.append({
                            # Unique ID: ProductID_ImageID
                            "id": f"{product.id}_{image.id}",
                            "image_path": image.src,
                            # Slug (Handle) taake user click karke product par ja sake
                            "slug": product.handle, 
                            "product_id": str(product.id)
                        })
                
                # Agla page check karein
                if page.has_next_page():
                    time.sleep(0.5) # Rate limit se bachne ke liye thoda wait
                    page = page.next_page()
                else:
                    break
                    
            print(f"✅ [Shopify] Fetched {len(product_list)} images successfully.")
            return product_list

        except Exception as e:
            print(f"❌ [Shopify] Error fetching products: {e}")
            return []
            
        finally:
            # Session close karna zaroori hai
            shopify.ShopifyResource.clear_session()

# Wrapper function jo Agent use karega
def fetch_all_products(credentials: dict):
    connector = ShopifyConnector(credentials)
    return connector.fetch_all_products()