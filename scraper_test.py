import time
import os
import subprocess
import random
from playwright.sync_api import sync_playwright

def scrape_amazon_reviews(product_name, max_reviews=10):
    try:
        if not os.path.exists("/tmp/playwright_installed"):
            subprocess.run(["playwright", "install", "chromium"], check=True)
            with open("/tmp/playwright_installed", "w") as f: f.write("done")
    except: pass

    with sync_playwright() as p:
        # slow_mo helps bypass simple bot detection
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        
        scraped_data = []
        try:
            search_url = f"https://www.amazon.in/s?k={product_name.replace(' ', '+')}"
            page.goto(search_url, wait_until="domcontentloaded", timeout=60000)
            
            # --- FIX: Generic Product Selector ---
            # Instead of specific classes, we look for any link inside an H2 in the search results
            try:
                page.wait_for_selector("h2 a", timeout=15000)
                product_links = page.query_selector_all("h2 a")
                
                # Pick the first one that looks like a product link
                target_link = product_links[0]
                for link in product_links[:3]: # Check first 3 to skip ads
                    if "/dp/" in link.get_attribute("href"):
                        target_link = link
                        break
                
                target_link.click()
            except Exception as e:
                # If it fails, save a screenshot so you can see if it's a CAPTCHA
                page.screenshot(path="bot_check.png")
                return []

            page.wait_for_load_state("domcontentloaded")
            time.sleep(random.uniform(2, 4))

            # Scroll to reviews
            page.evaluate("window.scrollBy(0, 2000)")
            time.sleep(2)
            
            # Use multiple possible selectors for reviews
            review_containers = page.query_selector_all(".review")
            
            for container in review_containers:
                text_el = container.query_selector("[data-hook='review-body']")
                star_el = container.query_selector(".a-icon-alt")
                
                if text_el:
                    rev_text = text_el.inner_text().strip()
                    rev_rating = 0.0
                    if star_el:
                        try:
                            rev_rating = float(star_el.inner_text().split()[0])
                        except: pass

                    if len(rev_text) > 20:
                        scraped_data.append({"text": rev_text, "rating": rev_rating})
                
                if len(scraped_data) >= max_reviews:
                    break
                    
        except Exception as e:
            print(f"Scrape Error: {e}")
        finally:
            browser.close()
            
        return scraped_data
