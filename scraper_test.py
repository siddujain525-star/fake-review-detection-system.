import time
import os
import subprocess
from playwright.sync_api import sync_playwright

def scrape_amazon_reviews(product_name, max_reviews=10):
    # 1. Ensure Playwright is installed
    try:
        if not os.path.exists("/tmp/playwright_installed"):
            subprocess.run(["playwright", "install", "chromium"], check=True)
            with open("/tmp/playwright_installed", "w") as f:
                f.write("done")
    except Exception as e:
        print(f"Playwright install note: {e}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={'width': 1920, 'height': 1080}
        )
        page = context.new_page()
        
        scraped_data = []
        try:
            # 2. SEARCH: Instead of going to a URL, go to the Search Results
            search_query = product_name.replace(" ", "+")
            search_url = f"https://www.amazon.in/s?k={search_query}"
            page.goto(search_url, wait_until="domcontentloaded", timeout=60000)
            
            # 3. CLICK: Find the first product that isn't an ad (Sponsored)
            # This selector targets the first organic product title
            first_product_selector = "h2 a.a-link-normal.s-line-clamp-2"
            page.wait_for_selector(first_product_selector)
            page.click(first_product_selector)
            
            # Wait for the product page to load
            page.wait_for_load_state("domcontentloaded")
            time.sleep(2)

            # 4. SCROLL & FIND REVIEWS:
            page.evaluate("window.scrollBy(0, 2000)") 
            time.sleep(2)
            
            # Target the individual review containers
            review_containers = page.query_selector_all(".review")
            
            for container in review_containers:
                # Extract Text
                text_el = container.query_selector("[data-hook='review-body']")
                # Extract Rating (Amazon uses "X.0 out of 5 stars")
                rating_el = container.query_selector(".a-icon-alt")
                
                if text_el and rating_el:
                    review_text = text_el.inner_text().strip()
                    rating_text = rating_el.inner_text().split()[0] # Get "4.0"
                    
                    try:
                        rating_val = float(rating_text)
                    except:
                        rating_val = 0.0

                    if len(review_text) > 15:
                        scraped_data.append({
                            "text": review_text,
                            "rating": rating_val
                        })
                
                if len(scraped_data) >= max_reviews:
                    break
                    
        except Exception as e:
            print(f"Scraping error: {e}")
        finally:
            browser.close()
            
        return scraped_data
