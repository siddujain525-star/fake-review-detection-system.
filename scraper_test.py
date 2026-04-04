import time
import os
import subprocess
import random
from playwright.sync_api import sync_playwright

def scrape_amazon_reviews(product_name, max_reviews=10):
    # Ensure Playwright is installed
    try:
        if not os.path.exists("/tmp/playwright_installed"):
            subprocess.run(["playwright", "install", "chromium"], check=True)
            with open("/tmp/playwright_installed", "w") as f:
                f.write("done")
    except Exception as e:
        print(f"Playwright install note: {e}")

    with sync_playwright() as p:
        # Launching with a slower 'slow_mo' helps bypass simple bot checks
        browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-setuid-sandbox"])
        
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={'width': 1280, 'height': 720}
        )
        page = context.new_page()
        
        scraped_data = []
        try:
            # 1. Search Logic
            search_query = product_name.replace(" ", "+")
            search_url = f"https://www.amazon.in/s?k={search_query}"
            
            # Use 'networkidle' to ensure the page is fully loaded
            page.goto(search_url, wait_until="networkidle", timeout=60000)
            time.sleep(random.uniform(2, 4))
            
            # 2. Click the first product (Organic, not sponsored)
            # This targets the first link in a search result heading
            first_product = page.locator('div[data-component-type="s-search-result"] h2 a').first
            if first_product.count() > 0:
                first_product.click()
            else:
                # Fallback if the layout is different
                page.click("h2 a")

            page.wait_for_load_state("networkidle")
            time.sleep(2)

            # 3. Scroll to reviews
            page.evaluate("window.scrollBy(0, 1500)")
            time.sleep(2)
            
            # 4. Extract Review Blocks
            # Amazon often uses 'customer_review' in the ID or the class '.review'
            review_elements = page.query_selector_all(".review")
            
            for el in review_elements:
                text_el = el.query_selector("[data-hook='review-body']")
                rating_el = el.query_selector(".a-icon-alt")
                
                if text_el and rating_el:
                    review_text = text_el.inner_text().strip()
                    # Rating looks like "5.0 out of 5 stars"
                    rating_raw = rating_el.inner_text().split()[0]
                    
                    try:
                        rating_val = float(rating_raw)
                    except:
                        rating_val = 0.0

                    if len(review_text) > 20:
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
