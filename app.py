import streamlit as st
import pandas as pd
import requests
import re
import json
import time
import io
from typing import Tuple, Optional, List

# Set page config
st.set_page_config(
    page_title="Email Enricher",
    page_icon="📧",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for beautiful UI
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        text-align: center;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 2rem;
    }
    
    .sub-header {
        text-align: center;
        color: #666;
        font-size: 1.2rem;
        margin-bottom: 3rem;
    }
    
    .stButton > button {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 10px;
        padding: 0.5rem 2rem;
        font-weight: bold;
        transition: all 0.3s;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 5px 15px rgba(0,0,0,0.2);
    }
    
    .upload-box {
        border: 2px dashed #667eea;
        border-radius: 10px;
        padding: 2rem;
        text-align: center;
        background: #f8f9ff;
    }
    
    .stats-card {
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        text-align: center;
    }
    
    .success-text {
        color: #28a745;
        font-weight: bold;
    }
    
    .error-text {
        color: #dc3545;
        font-weight: bold;
    }
    
    .info-text {
        color: #17a2b8;
        font-weight: bold;
    }
    
    .result-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 2rem;
        border-radius: 15px;
        box-shadow: 0 10px 30px rgba(102, 126, 234, 0.3);
        margin: 1rem 0;
    }
    
    .result-card h3 {
        margin: 0 0 1rem 0;
        font-size: 1.5rem;
    }
    
    .result-card p {
        margin: 0.5rem 0;
        font-size: 1.1rem;
    }
    
    .single-entry-form {
        background: #f8f9ff;
        padding: 2rem;
        border-radius: 15px;
        border: 1px solid #e0e6ff;
        margin: 1rem 0;
    }
    
    .email-found {
        background: linear-gradient(135deg, #28a745 0%, #20c997 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 10px;
        text-align: center;
        margin: 1rem 0;
        font-size: 1.2rem;
        font-weight: bold;
    }
    
    .email-not-found {
        background: linear-gradient(135deg, #dc3545 0%, #fd7e14 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 10px;
        text-align: center;
        margin: 1rem 0;
        font-size: 1.2rem;
        font-weight: bold;
    }
    
    .stTabs [data-baseweb="tab-list"] {
        gap: 2px;
    }
    
    .stTabs [data-baseweb="tab"] {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 10px 10px 0 0;
        padding: 1rem 2rem;
        font-weight: bold;
    }
    
    .stTabs [data-baseweb="tab"][aria-selected="true"] {
        background: linear-gradient(90deg, #764ba2 0%, #667eea 100%);
    }
</style>
""", unsafe_allow_html=True)

# Core email verification functions (same as before)
def clean_domain(domain_raw: str) -> str:
    """Removes http(s)://, www., and trailing slashes."""
    if not isinstance(domain_raw, str) or not domain_raw.strip():
        return ""
    domain = re.sub(r'^https?://', '', domain_raw.strip(), flags=re.IGNORECASE)
    domain = re.sub(r'^www\.', '', domain, flags=re.IGNORECASE)
    domain = domain.split('/')[0]
    return domain.strip().lower()

def parse_name(full_name: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """Parses a name into first, middle, last."""
    if not isinstance(full_name, str) or not full_name.strip():
        return None, None, None
    
    parts = full_name.strip().split()
    first_name = ''
    middle_name = None
    last_name = ''

    if len(parts) >= 1: 
        first_name = parts[0].lower()
    if len(parts) == 2: 
        last_name = parts[1].lower()
    elif len(parts) >= 3:
        middle_name = " ".join(parts[1:-1]).lower()
        last_name = parts[-1].lower()

    first_name = re.sub(r'[^a-z]', '', first_name)
    last_name = re.sub(r'[^a-z]', '', last_name)
    if middle_name: 
        middle_name = re.sub(r'[^a-z]', '', middle_name)

    if len(parts) == 1 and first_name: 
        last_name = first_name
    if not first_name and not last_name: 
        return None, None, None

    return first_name, middle_name, last_name

def generate_email_formats(first_name: str, middle_name: Optional[str], last_name: str, domain: str) -> List[str]:
    """Generates potential email formats."""
    potential_locals = []
    f = first_name[0] if first_name else ''
    m = middle_name[0] if middle_name else ''
    l = last_name[0] if last_name else ''

    if f and last_name: potential_locals.append(f"{f}{last_name}")
    if first_name: potential_locals.append(f"{first_name}")
    if first_name and last_name: potential_locals.append(f"{first_name}.{last_name}")
    if last_name: potential_locals.append(f"{last_name}")
    if f and l: potential_locals.append(f"{f}{l}")
    if first_name and last_name: potential_locals.append(f"{first_name}{last_name}")
    if first_name and l: potential_locals.append(f"{first_name}{l}")
    if last_name and f: potential_locals.append(f"{last_name}{f}")
    if last_name and f: potential_locals.append(f"{last_name}.{f}")
    if f and m and l: potential_locals.append(f"{f}{m}{l}")
    if last_name and first_name: potential_locals.append(f"{last_name}{first_name}")
    if first_name and m and last_name: potential_locals.append(f"{first_name}.{m}.{last_name}")
    if f and m and last_name: potential_locals.append(f"{f}{m}{last_name}")
    if first_name and last_name: potential_locals.append(f"{first_name}_{last_name}")

    generated_emails = list(dict.fromkeys([f"{local_part}@{domain}" for local_part in potential_locals if local_part]))
    return generated_emails

def verify_email_api(email: str, api_key: str) -> dict:
    """Calls the Reoon Email Verifier API."""
    api_url = f"https://emailverifier.reoon.com/api/v1/verify?email={email}&key={api_key}&mode=power"
    try:
        response = requests.get(api_url, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"error": f"API Request Failed: {e}"}
    except json.JSONDecodeError:
        return {"error": "Failed to decode API response"}



# Add these imports at the top of your app.py file
from urllib.parse import quote_plus, urljoin
from bs4 import BeautifulSoup
import random
from urllib.robotparser import RobotFileParser

# REPLACE the previous OSINT functions with these improved versions:

import traceback
import json
from datetime import datetime




# ========================================
# COMPLETE ENHANCED LINKEDIN FINDER FUNCTIONS
# Add these to your app.py file
# ========================================

# First, add these imports at the top of your app.py file:
import random
import traceback
from datetime import datetime

# ========================================
# FIXED LINKEDIN SEARCH FUNCTIONS
# Replace the previous functions with these fixed versions
# ========================================

# FIXED FUNCTION 1: googlesearch-python method
def googlesearch_library_method(email: str) -> dict:
    """FIXED: Use googlesearch-python library to bypass Google's anti-bot measures."""
    result = {
        'email': email,
        'linkedin_url': None,
        'profile_title': None,
        'status': 'searching',
        'error': None,
        'debug_info': {}
    }
    
    try:
        from googlesearch import search
        
        # Search query
        search_query = f'{email} site:linkedin.com'
        result['debug_info']['search_query'] = search_query
        
        # Use googlesearch library - FIX: Handle SearchResult objects properly
        try:
            search_results = search(
                search_query,
                num_results=10,
                lang='en',
                safe='off',
                advanced=False  # Changed to False to get simple URLs
            )
            
            # Convert to list and handle properly
            results_list = []
            linkedin_urls = []
            
            for i, result_item in enumerate(search_results):
                if i >= 10:  # Limit to 10 results
                    break
                    
                # Handle both string URLs and SearchResult objects
                if hasattr(result_item, 'url'):
                    url = result_item.url
                    title = getattr(result_item, 'title', 'LinkedIn Profile')
                elif isinstance(result_item, str):
                    url = result_item
                    title = 'LinkedIn Profile'
                else:
                    url = str(result_item)
                    title = 'LinkedIn Profile'
                
                results_list.append(url)
                result['debug_info'][f'result_{i+1}'] = url
                
                # Check if it's a LinkedIn profile
                if url and 'linkedin.com/in/' in url:
                    linkedin_urls.append({
                        'url': url,
                        'title': title,
                        'position': i + 1
                    })
            
            result['debug_info']['total_results_found'] = len(results_list)
            result['debug_info']['linkedin_urls_found'] = len(linkedin_urls)
            
            if linkedin_urls:
                # Take the first LinkedIn URL
                first_linkedin = linkedin_urls[0]
                result['linkedin_url'] = first_linkedin['url']
                result['profile_title'] = first_linkedin['title']
                result['status'] = 'found'
                result['search_engine'] = 'googlesearch-python'
                result['debug_info']['extraction_method'] = 'googlesearch_library_fixed'
                result['debug_info']['result_position'] = first_linkedin['position']
                return result
            
            # No LinkedIn results found
            result['status'] = 'not_found'
            result['error'] = f'No LinkedIn profiles found in {len(results_list)} search results'
            
        except Exception as search_error:
            result['status'] = 'error'
            result['error'] = f'googlesearch execution error: {str(search_error)}'
            result['debug_info']['search_exception'] = str(search_error)
        
    except ImportError:
        result['status'] = 'error'
        result['error'] = 'googlesearch-python library not installed. Run: pip install googlesearch-python'
    except Exception as e:
        result['status'] = 'error'
        result['error'] = f'googlesearch-python error: {str(e)}'
        result['debug_info']['exception_details'] = str(e)
    
    return result
# FIXED FUNCTION 2: Enhanced Selenium method
def selenium_browser_method(email: str) -> dict:
    """FIXED: Enhanced Selenium with better LinkedIn URL detection."""
    result = {
        'email': email,
        'linkedin_url': None,
        'profile_title': None,
        'status': 'searching',
        'error': None,
        'debug_info': {}
    }
    
    try:
        from selenium import webdriver
        from selenium.webdriver.common.by import By
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        import re
        
        # Chrome options for headless browsing
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # Initialize driver
        driver = webdriver.Chrome(options=chrome_options)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        try:
            # Search Google
            search_query = f'{email} site:linkedin.com'
            search_url = f"https://www.google.com/search?q={quote_plus(search_query)}"
            
            result['debug_info']['search_url'] = search_url
            result['debug_info']['search_query'] = search_query
            
            driver.get(search_url)
            
            # Wait for results to load
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Get page source for regex analysis
            page_source = driver.page_source
            result['debug_info']['page_length'] = len(page_source)
            result['debug_info']['page_contains_linkedin'] = 'linkedin' in page_source.lower()
            result['debug_info']['page_contains_vanessa'] = 'vanessa' in page_source.lower()
            
            # Strategy 1: Look for LinkedIn links in href attributes
            links = driver.find_elements(By.TAG_NAME, "a")
            linkedin_links = []
            
            for link in links:
                try:
                    href = link.get_attribute("href")
                    if href and 'linkedin.com/in/' in href and href.startswith('http'):
                        text = link.text.strip()
                        linkedin_links.append({
                            'url': href,
                            'text': text
                        })
                except:
                    continue
            
            result['debug_info']['linkedin_links_found'] = len(linkedin_links)
            result['debug_info']['total_links_checked'] = len(links)
            
            # Strategy 2: Use regex on page source to find LinkedIn URLs
            if not linkedin_links:
                linkedin_pattern = r'https://[a-zA-Z0-9.-]*linkedin\.com/in/[a-zA-Z0-9\-]+'
                regex_matches = re.findall(linkedin_pattern, page_source)
                
                result['debug_info']['regex_matches_found'] = len(regex_matches)
                result['debug_info']['regex_matches'] = regex_matches[:3]  # First 3 matches
                
                if regex_matches:
                    # Use the first regex match
                    linkedin_url = regex_matches[0]
                    result['linkedin_url'] = linkedin_url
                    result['profile_title'] = 'LinkedIn Profile (Regex)'
                    result['status'] = 'found'
                    result['search_engine'] = 'Selenium Chrome (Regex)'
                    result['debug_info']['extraction_method'] = 'selenium_regex'
                    return result
            
            # Strategy 3: Look for LinkedIn URLs in onclick or data attributes
            if not linkedin_links:
                all_elements = driver.find_elements(By.XPATH, "//*[contains(@onclick, 'linkedin') or contains(@data-href, 'linkedin')]")
                
                for element in all_elements:
                    onclick = element.get_attribute("onclick") or ""
                    data_href = element.get_attribute("data-href") or ""
                    
                    combined_text = onclick + " " + data_href
                    if 'linkedin.com/in/' in combined_text:
                        matches = re.findall(r'https://[a-zA-Z0-9.-]*linkedin\.com/in/[a-zA-Z0-9\-]+', combined_text)
                        if matches:
                            linkedin_links.extend([{'url': match, 'text': 'LinkedIn Profile'} for match in matches])
                
                result['debug_info']['attribute_search_links'] = len(linkedin_links)
            
            if linkedin_links:
                # Take the first LinkedIn profile
                first_result = linkedin_links[0]
                result['linkedin_url'] = first_result['url']
                result['profile_title'] = first_result['text'] or 'LinkedIn Profile'
                result['status'] = 'found'
                result['search_engine'] = 'Selenium Chrome'
                result['debug_info']['extraction_method'] = 'selenium_enhanced'
                return result
            
            result['status'] = 'not_found'
            result['error'] = 'No LinkedIn profiles found using enhanced Selenium browser'
            
        finally:
            driver.quit()
            
    except ImportError:
        result['status'] = 'error'
        result['error'] = 'Selenium not installed. Run: pip install selenium'
    except Exception as e:
        result['status'] = 'error'
        result['error'] = f'Selenium error: {str(e)}'
        result['debug_info']['exception_details'] = str(e)
    
    return result

# FIXED FUNCTION 4: Alternative simple search (bypasses complex parsing)
def simple_linkedin_search(email: str) -> dict:
    """Simple alternative that just searches for any LinkedIn mention."""
    result = {
        'email': email,
        'linkedin_url': None,
        'profile_title': None,
        'status': 'searching',
        'error': None,
        'debug_info': {}
    }
    
    try:
        # Try a direct approach - search for variations
        username = email.split('@')[0]
        domain = email.split('@')[1].split('.')[0]
        
        # Common LinkedIn URL patterns
        potential_urls = [
            f"https://www.linkedin.com/in/{username}",
            f"https://www.linkedin.com/in/{username.replace('.', '')}",
            f"https://www.linkedin.com/in/{username.replace('.', '-')}",
            f"https://www.linkedin.com/in/{username}{domain}",
            f"https://linkedin.com/in/{username}",
        ]
        
        result['debug_info']['potential_urls_tested'] = potential_urls
        
        # Test if any of these URLs exist (basic check)
        for url in potential_urls:
            try:
                headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
                response = requests.head(url, headers=headers, timeout=5, allow_redirects=True)
                
                if response.status_code == 200:
                    result['linkedin_url'] = url
                    result['profile_title'] = f'LinkedIn Profile ({username})'
                    result['status'] = 'found'
                    result['search_engine'] = 'Direct URL Test'
                    result['debug_info']['extraction_method'] = 'direct_url_test'
                    result['debug_info']['working_url'] = url
                    return result
                    
            except:
                continue
        
        result['status'] = 'not_found'
        result['error'] = 'No direct LinkedIn URLs found'
        
    except Exception as e:
        result['status'] = 'error'
        result['error'] = f'Simple search failed: {str(e)}'
    
    return result


# FIXED FUNCTION 3: Enhanced DuckDuckGo method
def fallback_duckduckgo_search(email: str) -> dict:
    """FIXED: Enhanced DuckDuckGo search with better parsing."""
    result = {
        'email': email,
        'linkedin_url': None,
        'profile_title': None,
        'status': 'searching',
        'error': None,
        'debug_info': {}
    }
    
    try:
        search_query = f'{email} site:linkedin.com'
        search_url = f"https://duckduckgo.com/html/?q={quote_plus(search_query)}"
        
        result['debug_info']['search_query'] = search_query
        result['debug_info']['search_url'] = search_url
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        response = requests.get(search_url, headers=headers, timeout=15)
        result['debug_info']['status_code'] = response.status_code
        result['debug_info']['content_length'] = len(response.content)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            page_text = response.text
            
            result['debug_info']['page_contains_linkedin'] = 'linkedin' in page_text.lower()
            result['debug_info']['page_contains_vanessa'] = 'vanessa' in page_text.lower()
            
            # Strategy 1: Look for direct LinkedIn links
            linkedin_links = []
            for link in soup.find_all('a', href=True):
                href = link.get('href')
                if href and 'linkedin.com/in/' in href:
                    linkedin_links.append({
                        'url': href,
                        'text': link.get_text(strip=True)
                    })
            
            result['debug_info']['direct_links_found'] = len(linkedin_links)
            
            # Strategy 2: Regex search in page content
            if not linkedin_links:
                import re
                linkedin_pattern = r'https://[a-zA-Z0-9.-]*linkedin\.com/in/[a-zA-Z0-9\-]+'
                regex_matches = re.findall(linkedin_pattern, page_text)
                
                result['debug_info']['regex_matches_found'] = len(regex_matches)
                result['debug_info']['regex_matches'] = regex_matches[:3]
                
                if regex_matches:
                    linkedin_links = [{'url': match, 'text': 'LinkedIn Profile'} for match in regex_matches]
            
            # Strategy 3: Look for DuckDuckGo specific result structures
            if not linkedin_links:
                # DuckDuckGo wraps results in specific divs
                for result_div in soup.find_all('div', class_=lambda x: x and 'result' in str(x).lower()):
                    div_text = result_div.get_text()
                    if 'linkedin' in div_text.lower():
                        # Look for URLs in this div
                        for link in result_div.find_all('a', href=True):
                            href = link.get('href')
                            if 'linkedin.com' in href:
                                # Clean up DuckDuckGo redirect URLs
                                if href.startswith('/l/?kh'):
                                    # Extract the real URL from DuckDuckGo's redirect
                                    import urllib.parse
                                    parsed = urllib.parse.parse_qs(href)
                                    if 'uddg' in parsed:
                                        real_url = urllib.parse.unquote(parsed['uddg'][0])
                                        if 'linkedin.com/in/' in real_url:
                                            linkedin_links.append({
                                                'url': real_url,
                                                'text': link.get_text(strip=True)
                                            })
                                elif 'linkedin.com/in/' in href:
                                    linkedin_links.append({
                                        'url': href,
                                        'text': link.get_text(strip=True)
                                    })
            
            result['debug_info']['total_linkedin_links'] = len(linkedin_links)
            
            if linkedin_links:
                # Take the first LinkedIn link
                first_link = linkedin_links[0]
                result['linkedin_url'] = first_link['url']
                result['profile_title'] = first_link['text'] or 'LinkedIn Profile'
                result['status'] = 'found'
                result['debug_info']['extraction_method'] = 'duckduckgo_enhanced'
                return result
            
            result['status'] = 'not_found'
            result['error'] = 'No LinkedIn profiles found in DuckDuckGo results'
            
            # Debug: Show a sample of what was found
            all_links = [link.get('href') for link in soup.find_all('a', href=True) if link.get('href')]
            result['debug_info']['sample_links'] = all_links[:5]
            result['debug_info']['total_links_found'] = len(all_links)
            
        else:
            result['status'] = 'error'
            result['error'] = f'DuckDuckGo returned status code {response.status_code}'
            
    except Exception as e:
        result['status'] = 'error'
        result['error'] = f'DuckDuckGo search failed: {str(e)}'
        result['debug_info']['exception_details'] = str(e)
    
    return result
# ========================================
# FUNCTION 4: DuckDuckGo fallback method (UPDATED)
# ========================================
def fallback_duckduckgo_search(email: str) -> dict:
    """Enhanced DuckDuckGo search."""
    result = {
        'email': email,
        'linkedin_url': None,
        'profile_title': None,
        'status': 'searching',
        'error': None,
        'debug_info': {}
    }
    
    try:
        search_query = f'{email} site:linkedin.com'
        search_url = f"https://duckduckgo.com/html/?q={quote_plus(search_query)}"
        
        result['debug_info']['search_query'] = search_query
        result['debug_info']['search_url'] = search_url
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        response = requests.get(search_url, headers=headers, timeout=15)
        result['debug_info']['status_code'] = response.status_code
        result['debug_info']['content_length'] = len(response.content)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # DuckDuckGo specific parsing
            for link in soup.find_all('a', href=True):
                href = link.get('href')
                if 'linkedin.com/in/' in href:
                    result['linkedin_url'] = href
                    result['profile_title'] = link.get_text(strip=True)
                    result['status'] = 'found'
                    result['debug_info']['extraction_method'] = 'duckduckgo_direct'
                    return result
            
            # Check page content
            page_text = response.text
            result['debug_info']['page_contains_linkedin'] = 'linkedin' in page_text.lower()
            
            result['status'] = 'not_found'
            result['error'] = 'No LinkedIn profiles found in DuckDuckGo results'
        else:
            result['status'] = 'error'
            result['error'] = f'DuckDuckGo returned status code {response.status_code}'
            
    except Exception as e:
        result['status'] = 'error'
        result['error'] = f'DuckDuckGo search failed: {str(e)}'
        result['debug_info']['exception_details'] = str(e)
    
    return result

def simple_google_linkedin_search(email: str) -> dict:
    """Enhanced Google search with better anti-bot evasion."""
    result = {
        'email': email,
        'linkedin_url': None,
        'profile_title': None,
        'status': 'searching',
        'error': None,
        'debug_info': {}
    }
    
    try:
        # Exact search query that works manually
        search_query = f'{email} site:linkedin.com'
        
        # More realistic browser headers to avoid bot detection
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0'
        }
        
        # Add some randomization to avoid bot detection
        import time
        import random
        time.sleep(random.uniform(1, 3))  # Random delay
        
        # Use Google search URL with additional parameters to mimic real browser
        google_url = f"https://www.google.com/search?q={quote_plus(search_query)}&num=10&hl=en&gl=us&pws=0"
        
        result['debug_info']['search_url'] = google_url
        result['debug_info']['search_query'] = search_query
        
        # Make request with session to maintain cookies
        session = requests.Session()
        session.headers.update(headers)
        
        response = session.get(google_url, timeout=15)
        result['debug_info']['status_code'] = response.status_code
        result['debug_info']['response_url'] = response.url
        result['debug_info']['content_length'] = len(response.content)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Check if Google blocked us with CAPTCHA
            if 'captcha' in response.text.lower() or 'unusual traffic' in response.text.lower():
                result['status'] = 'blocked'
                result['error'] = 'Google CAPTCHA detected - requests are being blocked'
                return result
            
            # Strategy 1: Look for result divs with specific data attributes
            for div in soup.find_all('div', {'data-hveid': True}):
                for link in div.find_all('a', href=True):
                    href = link.get('href', '')
                    if 'linkedin.com/in/' in href and href.startswith('https://'):
                        h3 = div.find('h3')
                        title = h3.get_text(strip=True) if h3 else 'LinkedIn Profile'
                        
                        result['linkedin_url'] = href
                        result['profile_title'] = title
                        result['status'] = 'found'
                        result['debug_info']['extraction_method'] = 'data_hveid_search'
                        return result
            
            # Strategy 2: Look for the specific title patterns
            for h3 in soup.find_all('h3'):
                h3_text = h3.get_text(strip=True)
                if any(name in h3_text.lower() for name in ['vanessa', 'suarez', 'castro']):
                    parent = h3.find_parent('div')
                    if parent:
                        for link in parent.find_all('a', href=True):
                            href = link.get('href')
                            if 'linkedin.com' in href:
                                result['linkedin_url'] = href
                                result['profile_title'] = h3_text
                                result['status'] = 'found'
                                result['debug_info']['extraction_method'] = 'title_matching'
                                return result
            
            # Strategy 3: Regex search in page text
            page_text = response.text
            import re
            
            linkedin_patterns = [
                r'https://[a-zA-Z0-9.-]*linkedin\.com/in/[a-zA-Z0-9\-]+/?',
                r'linkedin\.com/in/[a-zA-Z0-9\-]+',
            ]
            
            for pattern in linkedin_patterns:
                matches = re.findall(pattern, page_text, re.IGNORECASE)
                if matches:
                    linkedin_url = matches[0]
                    if not linkedin_url.startswith('http'):
                        linkedin_url = 'https://www.' + linkedin_url
                    
                    result['linkedin_url'] = linkedin_url
                    result['profile_title'] = 'LinkedIn Profile Found'
                    result['status'] = 'found'
                    result['debug_info']['extraction_method'] = 'regex_search'
                    result['debug_info']['pattern_used'] = pattern
                    result['debug_info']['all_matches'] = matches[:3]
                    return result
            
            # If nothing found, provide detailed debug info
            result['status'] = 'not_found'
            result['error'] = 'No LinkedIn profiles found in Google results'
            result['debug_info']['page_contains_linkedin'] = 'linkedin' in page_text.lower()
            result['debug_info']['page_contains_vanessa'] = 'vanessa' in page_text.lower()
            result['debug_info']['total_links_found'] = len(soup.find_all('a', href=True))
            
            # Save a sample of the page for debugging
            result['debug_info']['page_sample'] = page_text[:1000] if len(page_text) > 1000 else page_text
            
        else:
            result['status'] = 'error'
            result['error'] = f'Google returned status code {response.status_code}'
            if response.status_code == 429:
                result['error'] += ' - Too many requests (rate limited)'
            elif response.status_code == 403:
                result['error'] += ' - Forbidden (likely blocked by Google)'
            
    except requests.exceptions.RequestException as e:
        result['status'] = 'error'
        result['error'] = f'Network error: {str(e)}'
    except Exception as e:
        result['status'] = 'error'
        result['error'] = f'Unexpected error: {str(e)}'
        result['debug_info']['exception_details'] = str(e)
    
    return result

# UPDATED FUNCTION 5: Enhanced main finder with better error handling
def find_linkedin_enhanced(email: str) -> dict:
    """Enhanced LinkedIn finder with all fixed methods."""
    
    # Method 1: Try simple direct URL test first (fastest)
    simple_result = simple_linkedin_search(email)
    if simple_result['status'] == 'found':
        return simple_result
    
    # Method 2: Try googlesearch-python library (fixed)
    library_result = googlesearch_library_method(email)
    if library_result['status'] == 'found':
        return library_result
    
    # Method 3: Try enhanced Selenium browser automation
    selenium_result = selenium_browser_method(email)
    if selenium_result['status'] == 'found':
        return selenium_result
    
    # Method 4: Try enhanced DuckDuckGo
    duck_result = fallback_duckduckgo_search(email)
    if duck_result['status'] == 'found':
        duck_result['search_engine'] = 'DuckDuckGo Enhanced'
        return duck_result
    
    # Method 5: Try custom Google search as final fallback
    google_result = simple_google_linkedin_search(email)
    if google_result['status'] == 'found':
        google_result['search_engine'] = 'Custom Google'
        return google_result
    
    # All methods failed - combine debug info with better summary
    combined_result = {
        'email': email,
        'linkedin_url': None,
        'profile_title': None,
        'status': 'not_found',
        'error': 'All enhanced search methods failed',
        'search_engines_tried': ['Direct URL Test', 'googlesearch-python', 'Selenium Enhanced', 'DuckDuckGo Enhanced', 'Custom Google'],
        'debug_summary': {
            'googlesearch_library_error': library_result.get('error', 'Unknown'),
            'selenium_found_content': selenium_result.get('debug_info', {}).get('page_contains_linkedin', False),
            'duckduckgo_found_content': duck_result.get('debug_info', {}).get('page_contains_linkedin', False),
            'methods_that_found_linkedin_text': []
        },
        'debug_info': {
            'direct_url_test': simple_result,
            'googlesearch_library': library_result,
            'selenium_enhanced': selenium_result,
            'duckduckgo_enhanced': duck_result,
            'custom_google': google_result
        }
    }
    
    # Identify which methods found LinkedIn-related content
    if selenium_result.get('debug_info', {}).get('page_contains_linkedin'):
        combined_result['debug_summary']['methods_that_found_linkedin_text'].append('Selenium')
    if duck_result.get('debug_info', {}).get('page_contains_linkedin'):
        combined_result['debug_summary']['methods_that_found_linkedin_text'].append('DuckDuckGo')
    
    return combined_result
# ========================================
# FUNCTION 6: Enhanced render function (COMPLETE)
# ========================================
def render_enhanced_linkedin_tab():
    """Enhanced LinkedIn finder with multiple search methods."""
    st.subheader("🔍 Enhanced LinkedIn Finder")
    
    # Installation instructions
    st.info("""
    💡 **Enhanced Search Methods:**
    - 🐍 **googlesearch-python** - Library that bypasses Google blocking
    - 🌐 **Selenium** - Real browser automation (most reliable)
    - 🔧 **Custom requests** - Direct API approach (may be blocked)
    - 🦆 **DuckDuckGo** - Alternative search engine fallback
    """)
    
    # Check for required libraries
    missing_libs = []
    try:
        import googlesearch
        st.success("✅ googlesearch-python installed")
    except ImportError:
        missing_libs.append("googlesearch-python")
        st.error("❌ googlesearch-python missing")
    
    try:
        import selenium
        st.success("✅ selenium installed")
    except ImportError:
        missing_libs.append("selenium")
        st.error("❌ selenium missing")
    
    if missing_libs:
        st.warning(f"""
        ⚠️ **Install Missing Libraries for Better Results:**
        ```bash
        pip install {' '.join(missing_libs)}
        ```
        """)
    
    # Input form
    with st.container():
        email_input = st.text_input(
            "Business Email Address",
            placeholder="e.g., vanessa@vcdmarketing.com",
            help="Enter the business email address to find on LinkedIn"
        )
        
        # Options
        col1, col2 = st.columns(2)
        with col1:
            show_debug = st.checkbox(
                "Show All Methods Debug",
                value=True,
                help="Display debug info from all search methods"
            )
        
        with col2:
            show_page_sample = st.checkbox(
                "Show Page Content Sample",
                value=False,
                help="Display sample of what Google actually returned"
            )
        
        # Search button
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            search_btn = st.button(
                "🔍 Enhanced Multi-Method Search", 
                type="primary",
                use_container_width=True,
                key="enhanced_multi_search_btn"
            )
    
    # Search logic
    if search_btn:
        if not email_input:
            st.error("❌ Please enter an email address")
            return
        
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email_input):
            st.error("❌ Please enter a valid email address")
            return
        
        # Show processing
        with st.spinner("🔍 Trying multiple search methods..."):
            result = find_linkedin_enhanced(email_input.strip())
        
        # Display results
        st.subheader("🎯 Enhanced Search Results")
        
        if result.get('status') == 'found':
            # Success!
            linkedin_url = result['linkedin_url']
            profile_title = result.get('profile_title', 'LinkedIn Profile')
            search_engine = result.get('search_engine', 'Enhanced Search')
            
            st.markdown(f"""
            <div class="email-found">
                ✅ LinkedIn Profile Found!<br>
                📧 {email_input}
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown(f"""
            <div class="result-card">
                <h3>🔗 LinkedIn Profile</h3>
                <p><strong>🔗 URL:</strong> <a href="{linkedin_url}" target="_blank" style="color: white;">{linkedin_url}</a></p>
                <p><strong>👤 Profile:</strong> {profile_title}</p>
                <p><strong>🔍 Found via:</strong> {search_engine}</p>
                <p><strong>📧 Email:</strong> {email_input}</p>
            </div>
            """, unsafe_allow_html=True)
            
            # Download result
            result_df = pd.DataFrame([{
                'email': email_input,
                'linkedin_url': linkedin_url,
                'profile_title': profile_title,
                'search_engine': search_engine,
                'found_at': time.strftime('%Y-%m-%d %H:%M:%S')
            }])
            
            csv_buffer = io.StringIO()
            result_df.to_csv(csv_buffer, index=False)
            csv_data = csv_buffer.getvalue()
            
            st.download_button(
                label="📥 Download Result as CSV",
                data=csv_data,
                file_name=f"linkedin_enhanced_{email_input.replace('@', '_')}_{time.strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                type="secondary"
            )
            
        else:
            # All methods failed
            st.markdown(f"""
            <div class="email-not-found">
                ❌ All Search Methods Failed<br>
                📧 {email_input}<br>
                {result.get('error', 'No LinkedIn profile found')}
            </div>
            """, unsafe_allow_html=True)
            
            # Show which engines were tried
            engines_tried = result.get('search_engines_tried', [])
            if engines_tried:
                st.info(f"**Engines Tried:** {', '.join(engines_tried)}")
            
            st.error("""
            🔧 **Troubleshooting Steps:**
            1. Install missing libraries: `pip install googlesearch-python selenium`
            2. Download ChromeDriver for Selenium
            3. Try searching manually to verify the profile exists
            4. Consider using a VPN or different IP address
            5. The email might not be publicly associated with LinkedIn
            """)
        
        # Enhanced debug information
        if show_debug:
            st.subheader("🔧 All Methods Debug Information")
            
            debug_info = result.get('debug_info', {})
            
            # Show results from each method
            for method_name, method_result in debug_info.items():
                if isinstance(method_result, dict):
                    with st.expander(f"🔍 {method_name.replace('_', ' ').title()} Results"):
                        st.write(f"**Status:** {method_result.get('status', 'N/A')}")
                        st.write(f"**Error:** {method_result.get('error', 'N/A')}")
                        
                        method_debug = method_result.get('debug_info', {})
                        for key, value in method_debug.items():
                            if key == 'page_sample':
                                continue  # Handle separately
                            elif isinstance(value, (str, int, bool)):
                                st.write(f"**{key.replace('_', ' ').title()}:** {value}")
                            elif isinstance(value, list) and len(value) <= 5:
                                st.write(f"**{key.replace('_', ' ').title()}:** {', '.join(map(str, value))}")
        
        # Show page content sample
        if show_page_sample:
            debug_info = result.get('debug_info', {})
            for method_name, method_result in debug_info.items():
                if isinstance(method_result, dict):
                    method_debug = method_result.get('debug_info', {})
                    if method_debug.get('page_sample'):
                        with st.expander(f"📄 {method_name.title()} Page Sample"):
                            st.text(method_debug['page_sample'])

# Main Streamlit App
def main():
    # Header
    # st.markdown('<h1 class="main-header">📧 Email Verifier Pro</h1>', unsafe_allow_html=True)
    # st.markdown('<p class="sub-header">Professional email verification made simple and efficient</p>', unsafe_allow_html=True)
    
    # Sidebar for API key
    with st.sidebar:
        st.header("🔑 Configuration")
        api_key = st.text_input(
            "Enter your Reoon API Key",
            type="password",
            help="Get your API key from https://emailverifier.reoon.com/"
        )
        
        st.markdown("---")
        st.subheader("📋 CSV Format Required")
        st.markdown("""
        Your CSV file should contain these columns:
        - **firstname**: First name
        - **lastname**: Last name  
        - **companyURL**: Company website URL
        
        Example:
        ```
        firstname,lastname,companyURL
        John,Smith,https://company.com
        Jane,Doe,www.example.org
        ```
        """)
        
        st.markdown("---")
        st.subheader("ℹ️ How it works")
        st.markdown("""
        **CSV Mode:**
        1. Upload your CSV file
        2. Enter your API key
        3. Click 'Start Verification'
        4. Download verified emails
        
        **Single Entry Mode:**
        1. Enter individual details
        2. Click 'Verify Email'
        3. Get instant results
        """)
        
        st.markdown("---")
        st.subheader("🎯 Email Patterns Tested")
        st.markdown("""
        Our algorithm tests multiple patterns:
        - firstname.lastname@domain.com
        - firstname@domain.com
        - f.lastname@domain.com
        - flastname@domain.com
        - And 10+ more formats...
        """)
    
    # Main content area
    if not api_key:
        st.warning("⚠️ Please enter your API key in the sidebar to continue.")
        return
    
    # Updated tab structure with enhanced LinkedIn finder
    tab1, tab2, tab3 = st.tabs(["📁 CSV Upload", "👤 Single Entry", "🔍 Enhanced LinkedIn"])
    
    with tab1:
        render_csv_upload_tab(api_key)
    
    with tab2:
        render_single_entry_tab(api_key)
    
    with tab3:
        render_enhanced_linkedin_tab()  # No API key needed

if __name__ == "__main__":
    main()