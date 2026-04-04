import time
import os
import random
import re
from playwright.sync_api import sync_playwright

def scrape_amazon_reviews(product_name, max_reviews=10):
    """
    Optimized Amazon Scraper for Streamlit Cloud.
    Uses direct navigation and stealth headers to bypass timeouts.
    """
    scraped_data = []
    
    with sync_playwright() as p:
        # Launch with stealth arguments
        browser = p.chromium.launch(
            headless=True, 
            args=[
                "--no-sandbox", 
                "--disable-setuid-sandbox", 
                "--disable-blink-features=AutomationControlled"
            ]
        )
        
        # High-quality desktop context
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={'width': 1280, 'height': 800}
        )
        
        page = context.new_page()

        try:
            # 1. Direct Search URL (Faster than typing in a search bar)
            search_url = f"https://www.amazon.in/s?k={product_name.replace(' ', '+')}"
            
            # Using 'domcontentloaded' is much faster than 'networkidle'
            page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
            
            # 2. Identify the first real product link (skipping ads if possible)
            # We look for the standard Amazon DP (Detail Page) pattern
            try:
                page.wait_for_selector("a[href*='/dp/']", timeout=10000)
                product_links = page.query_selector_all("a[href*='/dp/']")
                
                if not product_links:
                    page.screenshot(path="bot_check.png")
                    return []

                # Get the link and go there directly
                target_path = product_links[0].get_attribute("href")
                target_url = target_path if target_path.startswith("http") else f"https://www.amazon.in{target_path}"
                
                # Navigate to the actual product page
                page.goto(target_url, wait_until="domcontentloaded", timeout=30000)
                time.sleep(random.uniform(1, 2)) # Human-like pause

            except Exception as e:
                page.screenshot(path="bot_check.png")
                print(f"Search Error: {e}")
                return []

            # 3. Extracting Reviews
            # Amazon's review containers usually have 'data-hook="review"'
            page.wait_for_selector("[data-hook='review']", timeout=10000)
            review_elements = page.query_selector_all("[data-hook='review']")

            for el in review_elements:
                # Get review text
                body = el.query_selector("[data-hook='review-body']")
                # Get star rating
                stars = el.query_selector("[data-hook='review-star-rating'], .a-icon-star")
                
                if body:
                    text = body.inner_text().strip().replace("Read more", "")
                    
                    # Extract numeric rating from string like "4.0 out of 5 stars"
                    rating = 0.0
                    if stars:
                        star_text = stars.inner_text() or stars.get_attribute("class")
                        match = re.search(r"(\d+\.\d+|\d+)", star_text)
                        if match:
                            rating = float(match.group(1))

                    if len(text) > 15:
                        scraped_data.append({"text": text, "rating": rating})
                
                if len(scraped_data) >= max_reviews:
                    break
                    
        except Exception as e:
            print(f"Scraper Runtime Error: {e}")
            page.screenshot(path="bot_check.png")
        finally:
            browser.close()
            
    return scraped_data
