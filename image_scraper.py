import requests
from bs4 import BeautifulSoup
import json
import os
import time
import re

class WikiArtScraper:
    def __init__(self, base_url="https://www.wikiart.org", save_dir="blossfeldt_images"):
        """Initialize the scraper with base URL and directory to save images"""
        self.base_url = base_url
        self.save_dir = save_dir
        self.session = requests.Session()
        # Set user agent to mimic a browser
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        })
        # Create directory if it doesn't exist
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)
    
    def get_artwork_urls(self, artist_path, language="de"):
        """Extract artwork URLs from the artist's page using JSON API"""
        all_artworks = []
        page = 1
        has_more = True
        
        while has_more:
            # WikiArt loads images through JSON API requests
            json_url = f"{self.base_url}/{language}/{artist_path}/mode/all-paintings?json=2&page={page}"
            print(f"Fetching page {page} from {json_url}")
            
            try:
                response = self.session.get(json_url)
                response.raise_for_status()
                data = response.json()
                
                # Extract artworks from the JSON response
                artworks = data.get("Paintings", [])
                if not artworks:
                    has_more = False
                    continue
                
                all_artworks.extend(artworks)
                
                # Check if there are more pages
                has_more = len(artworks) > 0
                page += 1
                
                # Be nice to the server
                time.sleep(1)
                
            except Exception as e:
                print(f"Error fetching page {page}: {e}")
                has_more = False
        
        return all_artworks

    def get_high_res_image_url(self, artwork_url, language="de"):
        """Get the high-resolution image URL from the artwork page"""
        full_url = f"{self.base_url}{artwork_url}"
        print(f"Fetching artwork page: {full_url}")
        
        try:
            response = self.session.get(full_url)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Look for high-resolution image URL in the page
            # This may need adjustment based on the actual structure
            image_element = soup.select_one("img.image-rotation")
            if image_element and image_element.get('src'):
                return image_element['src']
            
            # Alternative method: look for image URLs in JSON data
            scripts = soup.find_all('script', type='text/javascript')
            for script in scripts:
                if script.string and 'image' in script.string:
                    match = re.search(r'"image"\s*:\s*"([^"]+)"', script.string)
                    if match:
                        return match.group(1)
            
            return None
            
        except Exception as e:
            print(f"Error getting high-res image URL: {e}")
            return None

    def download_image(self, image_url, filename):
        """Download an image from the URL and save it to the specified filename"""
        try:
            response = self.session.get(image_url, stream=True)
            response.raise_for_status()
            
            with open(filename, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            print(f"Downloaded: {filename}")
            return True
            
        except Exception as e:
            print(f"Error downloading image: {e}")
            return False

    def scrape_artist(self, artist_path="karl-blossfeldt", language="de"):
        """Scrape all artwork images for a given artist"""
        artworks = self.get_artwork_urls(artist_path, language)
        print(f"Found {len(artworks)} artworks")
        
        for i, artwork in enumerate(artworks):
            title = artwork.get("title", f"artwork_{i}")
            # Clean the title to use as filename
            safe_title = "".join(c if c.isalnum() or c in " -_" else "_" for c in title)
            safe_title = safe_title.replace(" ", "_")
            
            # Get image URL directly from the artwork data
            image_url = artwork.get("image")
            if not image_url:
                # If not available, try to get it from the artwork page
                artwork_url = artwork.get("paintingUrl")
                if artwork_url:
                    image_url = self.get_high_res_image_url(artwork_url, language)
            
            if image_url:
                # If the image URL is relative, make it absolute
                if image_url.startswith("/"):
                    image_url = f"{self.base_url}{image_url}"
                
                # Extract file extension from URL
                extension = os.path.splitext(image_url)[1]
                if not extension:
                    extension = ".jpg"  # Default extension
                
                filename = os.path.join(self.save_dir, f"{safe_title}{extension}")
                self.download_image(image_url, filename)
            
            # Be nice to the server
            time.sleep(0.5)

    def extract_images_from_html(self, html_content):
        """Extract image URLs directly from HTML content"""
        soup = BeautifulSoup(html_content, 'html.parser')
        artwork_data = []
        
        # Look for artwork data in JSON format within scripts
        scripts = soup.find_all('script')
        for script in scripts:
            script_text = script.string if script.string else ""
            if "initialPortion" in script_text:
                match = re.search(r'initialPortion.+?items.+?_v.+?(\[.+?\])', script_text, re.DOTALL)
                if match:
                    try:
                        # Try to extract and parse the JSON array
                        json_str = match.group(1)
                        # Fix invalid JSON if needed
                        json_str = re.sub(r'(\w+)\s*:', r'"\1":', json_str)
                        data = json.loads(json_str)
                        
                        for item in data:
                            artwork_data.append({
                                "title": item.get("title", ""),
                                "year": item.get("year", ""),
                                "image": item.get("image", ""),
                                "paintingUrl": item.get("paintingUrl", "")
                            })
                    except json.JSONDecodeError as e:
                        print(f"Error parsing JSON: {e}")
        
        # Also look for image elements directly in the HTML
        if not artwork_data:
            img_elements = soup.select("img.lazy-load")
            for img in img_elements:
                # Try to get image source or data attribute
                img_src = img.get('data-src') or img.get('img-source') or ""
                artwork_data.append({
                    "title": img.get('title', img.get('alt', "")),
                    "image": img_src,
                    "paintingUrl": ""
                })
        
        return artwork_data

    def scrape_from_html(self, html_content):
        """Scrape artworks from provided HTML content"""
        artworks = self.extract_images_from_html(html_content)
        print(f"Found {len(artworks)} artworks in HTML")
        
        for i, artwork in enumerate(artworks):
            title = artwork.get("title", f"artwork_{i}")
            # Clean the title to use as filename
            safe_title = "".join(c if c.isalnum() or c in " -_" else "_" for c in title)
            safe_title = safe_title.replace(" ", "_")
            
            image_url = artwork.get("image")
            if image_url:
                # Extract file extension from URL
                extension = os.path.splitext(image_url)[1]
                if not extension:
                    extension = ".jpg"  # Default extension
                
                filename = os.path.join(self.save_dir, f"{safe_title}{extension}")
                self.download_image(image_url, filename)
            
            # Be nice to the server
            time.sleep(0.5)

# Example usage
if __name__ == "__main__":
    scraper = WikiArtScraper(save_dir="blossfeldt_images")
    
    # Option 1: Scrape from the live website
    scraper.scrape_artist("karl-blossfeldt")
    
    # Option 2: Scrape from provided HTML file
    # with open("wikiart_page.html", "r", encoding="utf-8") as f:
    #     html_content = f.read()
    #     scraper.scrape_from_html(html_content)