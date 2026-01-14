# backend/src/services/connectors/woocommerce_connector.py

from woocommerce import API
from typing import List, Dict, Any

class WooCommerceConnector:
    def __init__(self, credentials: Dict[str, str]):
        self.url = credentials.get("website_url") or credentials.get("url")
        self.consumer_key = credentials.get("consumer_key")
        self.consumer_secret = credentials.get("consumer_secret")

        if not all([self.url, self.consumer_key, self.consumer_secret]):
            raise ValueError("WooCommerce credentials (url, consumer_key, consumer_secret) are required.")

        # API Setup
        self.wcapi = API(
            url=self.url,
            consumer_key=self.consumer_key,
            consumer_secret=self.consumer_secret,
            version="wc/v3",
            timeout=20  # Thoda zyada time dete hain slow WP sites ke liye
        )

    def fetch_all_products(self) -> List[Dict[str, Any]]:
        """
        WooCommerce API se paginated products fetch karta hai.
        """
        print(f"🛒 [WooCommerce] Connecting to {self.url}...")
        
        product_list = []
        page = 1
        per_page = 50  # Reasonable chunk size
        
        try:
            while True:
                # API Call
                response = self.wcapi.get("products", params={"per_page": per_page, "page": page, "status": "publish"})
                
                if response.status_code != 200:
                    print(f"⚠️ [WooCommerce] Error on page {page}: {response.status_code} - {response.text}")
                    break
                
                products = response.json()
                
                # Agar products khatam ho gaye, to loop roko
                if not products:
                    break
                
                for product in products:
                    # Agar image nahi hai to skip karo
                    if not product.get("images"):
                        continue
                        
                    for image in product["images"]:
                        product_list.append({
                            # Unique ID: ProductID_ImageID
                            "id": f"{product['id']}_{image['id']}",
                            "image_path": image["src"],
                            "slug": product["slug"], # Product URL slug
                            "product_id": str(product['id'])
                        })
                
                print(f"   -> Page {page} fetched ({len(products)} items)")
                page += 1

            print(f"✅ [WooCommerce] Fetched {len(product_list)} images successfully.")
            return product_list

        except Exception as e:
            print(f"❌ [WooCommerce] Connection Error: {e}")
            return []

# Wrapper function for Agent
def fetch_all_products(credentials: dict):
    connector = WooCommerceConnector(credentials)
    return connector.fetch_all_products()