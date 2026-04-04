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
            with open("/tmp/playwright_installed", "w") as f: f.write("done")
    except: pass

    with sync_playwright() as p:
        # Launch with specific arguments for Linux servers
        browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-gpu"])
        
        # Use a very specific, modern User-Agent
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        
        scraped_data = []
        try:
            # 1. Search with a timeout and 'commit' load state
            search_url = f"https://www.amazon.in/s?k={product_name.replace(' ', '+')}"
            page.goto(search_url, wait_until="domcontentloaded")
            
            # 2. Wait for ANY link inside an H2 (the most generic product link selector)
            # This is less likely to time out than the specific class name
            page.wait_for_selector("h2 a", timeout=15000)
            
            # Click the first organic result
            links = page.query_selector_all("h2 a")
            # Skip the first 2 links if they are sponsored ads
            target_link = links[2] if len(links) > 2 else links[0]
            target_link.click()
            
            page.wait_for_load_state("domcontentloaded")
            time.sleep(random.uniform(2, 4)) # Human-like pause

            # 3. Scroll and grab reviews using multiple selectors
            page.evaluate("window.scrollBy(0, 2000)")
            time.sleep(2)
            
            # Wide net for review text
            review_containers = page.query_selector_all(".review")
            
            for container in review_containers:
                # Amazon's review body hook
                text_el = container.query_selector("[data-hook='review-body']")
                # Amazon's star rating hook
                star_el = container.query_selector(".a-icon-alt")
                
                if text_el:
                    rev_text = text_el.inner_text().strip()
                    rev_rating = 0.0
                    
                    if star_el:
                        try:
                            # Extracts '4.0' from '4.0 out of 5 stars'
                            rev_rating = float(star_el.inner_text().split()[0])
                        except: pass

                    if len(rev_text) > 20:
                        scraped_data.append({"text": rev_text, "rating": rev_rating})
                
                if len(scraped_data) >= max_reviews:
                    break
                    
        except Exception as e:
            # If it fails, take a screenshot so you can see the CAPTCHA in your repo
            page.screenshot(path="error_debug.png")
            print(f"Scrape Error: {e}")
        finally:
            browser.close()
            
        return scraped_data
