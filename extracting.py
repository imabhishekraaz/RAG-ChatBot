import hashlib
import io
import os
import sys
import time
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from pypdf import PdfReader
import requests
import urllib3

# SSL warnings suppress karne ke liye
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

START_URL = "https://www.mangalayatan.in/"  # APNA URL YAHAN DALEIN

# Normalize domain (handles www vs non-www)
def get_clean_domain(url):
  netloc = urlparse(url).netloc.lower()
  return netloc[4:] if netloc.startswith("www.") else netloc

BASE_DOMAIN = get_clean_domain(START_URL)

visited_urls = set()
urls_to_visit = [START_URL]
seen_content_hashes = set()

headers = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like"
        " Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
    ),
    "Accept-Language": "en-US,en;q=0.5",
}


def get_text_hash(text):
  clean_str = " ".join(text.lower().split())
  return hashlib.md5(clean_str.encode("utf-8")).hexdigest()


def filter_unique_blocks(raw_text_lines):
  unique_lines = []
  for line in raw_text_lines:
    line_clean = line.strip()
    if len(line_clean) < 15:  # Reduced minimum threshold
      continue
    line_hash = get_text_hash(line_clean)
    if line_hash in seen_content_hashes:
      continue
    seen_content_hashes.add(line_hash)
    unique_lines.append(line_clean)
  return "\n\n".join(unique_lines)


print(f"[*] Starting crawl on: {START_URL}")
print(f"[*] Target Domain: {BASE_DOMAIN}")

with open("clean_university_data.txt", "w", encoding="utf-8") as out_file:
  while urls_to_visit:
    current_url = urls_to_visit.pop(0)

    if current_url in visited_urls or any(
        current_url.lower().endswith(ext)
        for ext in [".jpg", ".png", ".jpeg", ".zip", ".mp4", ".svg", ".css", ".js"]
    ):
      continue

    try:
      print(f"[>] Crawling: {current_url}")
      res = requests.get(
          current_url, headers=headers, timeout=15, verify=False
      )
      visited_urls.add(current_url)

      if res.status_code != 200:
        print(f"[-] Status code {res.status_code} for {current_url}")
        continue

      content_type = res.headers.get("Content-Type", "").lower()

      # 1. PDF Handling
      if (
          "application/pdf" in content_type
          or current_url.lower().endswith(".pdf")
      ):
        try:
          pdf_file = io.BytesIO(res.content)
          reader = PdfReader(pdf_file)
          extracted_lines = []
          for page in reader.pages:
            t = page.extract_text()
            if t:
              extracted_lines.extend(t.split("\n"))

          clean_pdf_text = filter_unique_blocks(extracted_lines)
          if clean_pdf_text:
            out_file.write(
                f"\n\n{'='*60}\nSOURCE (PDF):"
                f" {current_url}\n{'='*60}\n\n{clean_pdf_text}\n"
            )
            out_file.flush()  # Disk par write confirm karne ke liye
            os.fsync(out_file.fileno())
            print(f"    [+] Saved PDF data")
        except Exception as e:
          print(f"    [-] PDF Extraction failed: {e}")
        continue

      # 2. HTML Handling
      if "text/html" in content_type:
        soup = BeautifulSoup(res.text, "html.parser")

        for tag in soup(
            ["script", "style", "nav", "footer", "header", "aside", "noscript"]
        ):
          tag.decompose()

        raw_lines = [
            elem.get_text(strip=True)
            for elem in soup.find_all(
                ["p", "h1", "h2", "h3", "h4", "h5", "li", "td", "div", "span"]
            )
        ]
        clean_web_text = filter_unique_blocks(raw_lines)

        if clean_web_text:
          out_file.write(
              f"\n\n{'='*60}\nSOURCE (WEB):"
              f" {current_url}\n{'='*60}\n\n{clean_web_text}\n"
          )
          out_file.flush()  # Disk par write confirm karne ke liye
          os.fsync(out_file.fileno())
          print(f"    [+] Saved HTML data")

        # Links Collection
        for a_tag in soup.find_all("a", href=True):
          full_link = urljoin(current_url, a_tag["href"]).split("#")[0].strip()
          link_domain = get_clean_domain(full_link)

          if (
              link_domain == BASE_DOMAIN
              and full_link not in visited_urls
              and full_link not in urls_to_visit
          ):
            urls_to_visit.append(full_link)

      time.sleep(0.3)

    except Exception as e:
      print(f"[-] Error crawling {current_url}: {e}")

print(f"\n[✓] Finished. Output saved to clean_university_data.txt")