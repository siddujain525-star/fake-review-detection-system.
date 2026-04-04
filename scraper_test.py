import time
import os
import subprocess
import random
from playwright.sync_api import sync_playwright

def scrape_amazon_reviews(product_name, max_reviews=100):
    # Ensure Playwright browsers are installed (Only for Streamlit Cloud)
    try:
        if not os.path.exists("/home/appuser/.cache/ms-playwright"):
            subprocess.run(["playwright", "install", "chromium"], check=True)
    except: 
        pass

    with sync_playwright() as p:
        # 1. Launch with extra arguments to bypass headless detection
        browser = p.chromium.launch(
            headless=True, 
            args=[
                "--no-sandbox", 
                "--disable-setuid-sandbox", 
                "--disable-blink-features=AutomationControlled"
            ]
        )
        
        # 2. Use a high-quality User-Agent and viewport
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={'width': 1920, 'height': 1080}
        )
        
        page = context.new_page()
        scraped_data = []

        try:
            # 3. Direct Search URL
            search_url = f"https://www.amazon.in/s?k={product_name.replace(' ', '+')}"
            page.goto(search_url, wait_until="networkidle", timeout=60000)
            
            # Check for "Robot Check" (CAPTCHA)
            if "robot" in page.title().lower() or "captcha" in page.content().lower():
                page.screenshot(path="bot_check.png")
                return []

            # 4. Find the first product link
            # We look for links containing '/dp/' (Standard Amazon Product URL format)
            page.wait_for_selector("a[href*='/dp/']", timeout=15000)
            product_links = page.query_selector_all("a[href*='/dp/']")
            
            if not product_links:
                page.screenshot(path="bot_check.png")
                return []

            # Get the href of the first valid result and go there directly 
            # (Clicking sometimes opens new tabs which breaks the script)
            target_href = product_links[0].get_attribute("href")
            if not target_href.startswith("http"):
                target_href = "https://www.amazon.in" + target_href
            
            page.goto(target_href, wait_until="networkidle", timeout=60000)
            time.sleep(random.uniform(2, 4))

            # 5. Extract reviews using multiple selector fallbacks
            # Amazon often A/B tests different layouts
            review_containers = page.query_selector_all("[data-hook='review']")
            
            if not review_containers:
                # Try fallback selector
                review_containers = page.query_selector_all(".review")

            for container in review_containers:
                # Text content
                text_el = container.query_selector("[data-hook='review-body']")
                # Star rating
                star_el = container.query_selector("[data-hook='review-star-rating'], .a-icon-star")
                
                if text_el:
                    rev_text = text_el.inner_text().strip()
                    # Clean up "Read more" or extra labels
                    rev_text = rev_text.replace("Read more", "").strip()
                    
                    rev_rating = 0.0
                    if star_el:
                        try:
                            # Usually looks like "4.0 out of 5 stars"
                            rating_str = star_el.inner_text() or star_el.get_attribute("class")
                            # Extract the first number found
                            import re
                            match = re.search(r"(\d+\.\d+|\d+)", rating_str)
                            if match:
                                rev_rating = float(match.group(1))
                        except: 
                            pass

                    if len(rev_text) > 10:
                        scraped_data.append({"text": rev_text, "rating": rev_rating})
                
                if len(scraped_data) >= max_reviews:
                    break
                    
        except Exception as e:
            print(f"Scrape Error: {e}")
            page.screenshot(path="bot_check.png") # Diagnostic for Streamlit
        finally:
            browser.close()
            
        return scraped_data
