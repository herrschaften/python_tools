import requests
from bs4 import BeautifulSoup
import os
import time
import re

def download_pdv_images(category="signs-symbols", start_page=1, end_page=196):
    """
    Download all images from PublicDomainVectors.org for a specific category
    """
    base_url = "https://publicdomainvectors.org"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    # Create download directory
    download_dir = f"pdv_{category}_images"
    os.makedirs(download_dir, exist_ok=True)
    
    # Start crawling pages
    for page in range(start_page, end_page + 1):
        # Construct page URL
        if page == 1:
            page_url = f"{base_url}/en/free-clipart/{category}/"
        else:
            page_url = f"{base_url}/en/free-clipart/{category}/{page}"
        
        print(f"Processing page {page}/{end_page}")
        
        try:
            # Get the page
            response = requests.get(page_url, headers=headers)
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Find all vector images
            vectors = soup.select("div.vector.text-center")
            
            for i, vector in enumerate(vectors):
                try:
                    # Get the link and image
                    link = vector.select_one("div.vector-thumbnail-wrap a")
                    if not link:
                        continue
                    
                    img = link.select_one("img")
                    if not img:
                        continue
                    
                    # Get image URL and title
                    img_url = img.get("src", "")
                    if not img_url.startswith("http"):
                        img_url = base_url + img_url
                    
                    title = img.get("alt", "") or img.get("title", "")
                    
                    # Clean title for filename
                    safe_title = re.sub(r'[^\w\s-]', '', title).strip().replace(' ', '_')
                    if not safe_title:
                        safe_title = f"image_{page}_{i}"
                    
                    # Get file extension from URL
                    extension = os.path.splitext(img_url)[1]
                    if not extension:
                        extension = ".webp"  # Default extension for this site
                    
                    # Create filename
                    filename = f"{safe_title}{extension}"
                    filepath = os.path.join(download_dir, filename)
                    
                    # Download the image
                    print(f"Downloading: {filename}")
                    img_response = requests.get(img_url, headers=headers)
                    
                    # Save the image
                    with open(filepath, "wb") as f:
                        f.write(img_response.content)
                    
                    print(f"Saved: {filepath}")
                    
                    # Be nice to the server
                    time.sleep(0.5)
                    
                except Exception as e:
                    print(f"Error downloading image: {e}")
            
            print(f"Completed page {page}")
            # Wait between pages
            time.sleep(2)
            
        except Exception as e:
            print(f"Error processing page {page}: {e}")

if __name__ == "__main__":
    # Just run this function to download all images
    download_pdv_images(
        category="signs-symbols",  # Change this to the category you want
        start_page=1,
        end_page=196  # Total number of pages
    )