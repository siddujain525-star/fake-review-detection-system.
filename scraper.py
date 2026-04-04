import undetected_chromedriver as uc
from bs4 import BeautifulSoup
import time
import random

def get_live_reviews(product_name):
    options = uc.ChromeOptions()
    # In 2026, '--headless=new' is the standard for staying undetected
    options.add_argument('--headless=new') 
    
    driver = uc.Chrome(options=options)
    reviews_data = []

    try:
        # 1. Search Amazon.in
        search_url = f"https://www.amazon.in/s?k={product_name.replace(' ', '+')}"
        driver.get(search_url)
        time.sleep(random.uniform(2, 4)) # Mimic human pause
        
        # 2. Click the first product
        first_result = driver.find_element("css selector", "h2 a")
        driver.get(first_result.get_attribute("href"))
        time.sleep(2)
        
        # 3. Parse the Page
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        # Select individual review blocks
        review_blocks = soup.select(".review")
        
        for block in review_blocks[:10]: # Limit to 10 for speed
            text = block.select_one("[data-hook='review-body']").get_text(strip=True)
            # Extract numerical rating (e.g., "4.0 out of 5 stars" -> 4.0)
            rating_str = block.select_one(".a-icon-alt").get_text()
            rating = float(rating_str.split()[0])
            
            reviews_data.append({"text": text, "rating": rating})
            
    except Exception as e:
        print(f"Error during scraping: {e}")
    finally:
        driver.quit()
        
    return reviews_data
