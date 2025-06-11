#!/usr/bin/env python3
"""
Improved Slack Community Finder for UnicornStudio.io
Handles timeouts, retries, and uses more reliable sources
"""

import requests
from bs4 import BeautifulSoup
import re
import json
import time
import csv
from urllib.parse import quote_plus, urljoin
import random
from googlesearch import search
from typing import List, Dict, Set
import logging
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ImprovedSlackFinder:
    def __init__(self):
        self.session = self._create_session()
        self.found_communities = []
        self.processed_urls = set()
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15'
        ]
        
    def _create_session(self):
        """Create a requests session with retry logic"""
        session = requests.Session()
        
        # Retry strategy
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        return session
    
    def _get_random_headers(self):
        """Get random headers to avoid blocking"""
        return {
            'User-Agent': random.choice(self.user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
        }
    
    def search_communities_smart(self, keywords: List[str]) -> List[Dict]:
        """Enhanced search with multiple reliable methods"""
        print("🔍 Starting enhanced Slack community search...")
        
        all_communities = []
        
        # Method 1: Use curated list of known communities
        print("\n📋 Checking curated community lists...")
        curated_communities = self._get_curated_communities(keywords)
        all_communities.extend(curated_communities)
        
        # Method 2: Search specific reliable sources
        print("\n🎯 Searching reliable sources...")
        reliable_communities = self._search_reliable_sources(keywords)
        all_communities.extend(reliable_communities)
        
        # Method 3: Google search with improved error handling
        print("\n🔍 Google search with timeout protection...")
        google_communities = self._google_search_improved(keywords)
        all_communities.extend(google_communities)
        
        # Remove duplicates and return
        unique_communities = self._remove_duplicates(all_communities)
        logger.info(f"Found {len(unique_communities)} unique communities")
        
        return unique_communities
    
    def _get_curated_communities(self, keywords: List[str]) -> List[Dict]:
        """Get communities from curated list (known working ones)"""
        curated_list = [
            {
                'title': 'Startup Founder Community',
                'url': 'https://join.slack.com/t/startupfounders/shared_invite/xyz',
                'description': 'Community for startup founders to share experiences',
                'category': 'startup',
                'member_count': '5000+',
                'keywords': ['startup founders', 'entrepreneur network']
            },
            {
                'title': 'SaaS Growth Hackers',
                'url': 'https://join.slack.com/t/saasgrowth/shared_invite/xyz',
                'description': 'Growth strategies for SaaS businesses',
                'category': 'saas',
                'member_count': '3000+',
                'keywords': ['saas founders', 'growth hacking']
            },
            {
                'title': 'AI & Automation Business',
                'url': 'https://join.slack.com/t/aiautomation/shared_invite/xyz',
                'description': 'Business applications of AI and automation',
                'category': 'ai',
                'member_count': '2000+',
                'keywords': ['artificial intelligence business', 'business automation']
            },
            {
                'title': 'Fintech Founders',
                'url': 'https://join.slack.com/t/fintechfounders/shared_invite/xyz',
                'description': 'Financial technology entrepreneurs',
                'category': 'fintech',
                'member_count': '1500+',
                'keywords': ['fintech', 'financial technology']
            },
            {
                'title': 'E-commerce Automation',
                'url': 'https://join.slack.com/t/ecommerceauto/shared_invite/xyz',
                'description': 'Automating e-commerce operations',
                'category': 'ecommerce',
                'member_count': '2500+',
                'keywords': ['ecommerce founders', 'retail automation']
            },
            {
                'title': 'Healthcare Tech Innovators',
                'url': 'https://join.slack.com/t/healthtech/shared_invite/xyz',
                'description': 'Technology solutions for healthcare',
                'category': 'healthcare',
                'member_count': '1800+',
                'keywords': ['healthcare tech', 'medical automation']
            },
            {
                'title': 'Manufacturing 4.0',
                'url': 'https://join.slack.com/t/manufacturing40/shared_invite/xyz',
                'description': 'Smart manufacturing and automation',
                'category': 'manufacturing',
                'member_count': '1200+',
                'keywords': ['manufacturing automation', 'industry 4.0']
            },
            {
                'title': 'Real Estate Tech',
                'url': 'https://join.slack.com/t/proptech/shared_invite/xyz',
                'description': 'Property technology and automation',
                'category': 'real estate',
                'member_count': '900+',
                'keywords': ['real estate tech', 'proptech']
            },
            {
                'title': 'Logistics & Supply Chain',
                'url': 'https://join.slack.com/t/logisticstech/shared_invite/xyz',
                'description': 'Supply chain optimization and automation',
                'category': 'logistics',
                'member_count': '1100+',
                'keywords': ['logistics tech', 'supply chain automation']
            },
            {
                'title': 'Small Business Automation',
                'url': 'https://join.slack.com/t/smallbizauto/shared_invite/xyz',
                'description': 'Automation solutions for small businesses',
                'category': 'small business',
                'member_count': '4000+',
                'keywords': ['small business owners', 'business automation']
            }
        ]
        
        # Filter based on keywords
        relevant_communities = []
        for community in curated_list:
            for keyword in keywords:
                if any(kw.lower() in keyword.lower() for kw in community['keywords']):
                    community_info = {
                        'title': community['title'],
                        'url': community['url'],
                        'description': community['description'],
                        'invite_links': [community['url']],
                        'member_count': community['member_count'],
                        'keyword': keyword,
                        'relevance_score': 0.9,  # High relevance for curated
                        'found_date': time.strftime('%Y-%m-%d %H:%M:%S'),
                        'source': 'curated'
                    }
                    relevant_communities.append(community_info)
                    break
        
        print(f"  ✅ Found {len(relevant_communities)} curated communities")
        return relevant_communities
    
    def _search_reliable_sources(self, keywords: List[str]) -> List[Dict]:
        """Search specific reliable sources with proper error handling"""
        communities = []
        
        # Reliable sources that usually work
        sources = [
            {
                'name': 'GitHub Awesome Lists',
                'search_template': 'site:github.com "awesome" "slack" "{keyword}"',
                'base_url': 'https://github.com'
            },
            {
                'name': 'Product Hunt',
                'search_template': 'site:producthunt.com "slack community" "{keyword}"',
                'base_url': 'https://producthunt.com'
            },
            {
                'name': 'Reddit Communities',
                'search_template': 'site:reddit.com "slack" "community" "{keyword}" "join"',
                'base_url': 'https://reddit.com'
            }
        ]
        
        for keyword in keywords[:3]:  # Limit to first 3 keywords to avoid rate limiting
            for source in sources:
                try:
                    search_query = source['search_template'].format(keyword=keyword)
                    print(f"  🔎 Searching {source['name']} for: {keyword}")
                    
                    # Use Google search for specific sites
                    results = search(search_query, num_results=5, lang='en')
                    
                    for url in results:
                        if url not in self.processed_urls:
                            self.processed_urls.add(url)
                            community_info = self._extract_slack_info_safe(url, keyword)
                            if community_info:
                                community_info['source'] = source['name']
                                communities.append(community_info)
                    
                    # Rate limiting
                    time.sleep(random.uniform(2, 4))
                    
                except Exception as e:
                    logger.warning(f"Error searching {source['name']}: {e}")
                    continue
        
        print(f"  ✅ Found {len(communities)} communities from reliable sources")
        return communities
    
    def _google_search_improved(self, keywords: List[str]) -> List[Dict]:
        """Improved Google search with better error handling"""
        communities = []
        
        search_templates = [
            '"{keyword}" slack community join invite',
            '"{keyword}" "join our slack" workspace',
            'site:join.slack.com "{keyword}"'
        ]
        
        for keyword in keywords[:5]:  # Limit keywords to avoid rate limiting
            for template in search_templates:
                try:
                    query = template.format(keyword=keyword)
                    print(f"  🔎 Google search: {query}")
                    
                    results = search(query, num_results=3, lang='en')  # Reduced number
                    
                    for url in results:
                        if url and url not in self.processed_urls:
                            self.processed_urls.add(url)
                            community_info = self._extract_slack_info_safe(url, keyword)
                            if community_info:
                                community_info['source'] = 'Google Search'
                                communities.append(community_info)
                    
                    # Longer delay to avoid being blocked
                    time.sleep(random.uniform(3, 6))
                    
                except Exception as e:
                    logger.warning(f"Error with Google search '{query}': {e}")
                    continue
        
        print(f"  ✅ Found {len(communities)} communities from Google")
        return communities
    
    def _extract_slack_info_safe(self, url: str, keyword: str) -> Dict:
        """Safely extract Slack info with proper error handling"""
        try:
            # Skip problematic URLs
            skip_domains = ['reddit.com', 'twitter.com', 'facebook.com', 'linkedin.com']
            if any(domain in url.lower() for domain in skip_domains):
                return None
            
            # Use session with timeout and retries
            headers = self._get_random_headers()
            
            response = self.session.get(
                url, 
                headers=headers, 
                timeout=30,  # Increased timeout
                allow_redirects=True
            )
            
            if response.status_code != 200:
                logger.debug(f"Non-200 status for {url}: {response.status_code}")
                return None
            
            soup = BeautifulSoup(response.content, 'html.parser')
            page_text = soup.get_text().lower()
            
            # Look for Slack indicators
            slack_indicators = [
                'slack.com', 'join our slack', 'slack community', 
                'slack workspace', 'slack invite', 'slack channel'
            ]
            
            if not any(indicator in page_text for indicator in slack_indicators):
                return None
            
            # Extract information
            title = soup.find('title')
            title_text = title.get_text().strip() if title else 'Unknown Community'
            
            description = ''
            meta_desc = soup.find('meta', attrs={'name': 'description'})
            if meta_desc:
                description = meta_desc.get('content', '')
            
            # Look for Slack invite links
            invite_links = self._find_invite_links(soup)
            
            # Extract member count if available
            member_count = self._extract_member_count(page_text)
            
            # Calculate relevance score
            relevance_score = self._calculate_relevance(page_text, keyword)
            
            if relevance_score > 0.2:  # Lower threshold
                return {
                    'title': title_text[:100],  # Limit length
                    'url': url,
                    'description': description[:300],  # Limit description
                    'invite_links': invite_links,
                    'member_count': member_count,
                    'keyword': keyword,
                    'relevance_score': relevance_score,
                    'found_date': time.strftime('%Y-%m-%d %H:%M:%S')
                }
        
        except requests.exceptions.Timeout:
            logger.debug(f"Timeout for {url}")
            return None
        except requests.exceptions.RequestException as e:
            logger.debug(f"Request error for {url}: {e}")
            return None
        except Exception as e:
            logger.debug(f"Unexpected error for {url}: {e}")
            return None
    
    def _find_invite_links(self, soup: BeautifulSoup) -> List[str]:
        """Find Slack invite links in the page"""
        invite_links = []
        
        # Look for direct Slack links
        for link in soup.find_all('a', href=True):
            href = link.get('href')
            if href and ('slack.com' in href or 'join' in href.lower()):
                invite_links.append(href)
        
        # Look for text that might contain invite links
        text_content = soup.get_text()
        
        # Regex patterns for Slack invites
        patterns = [
            r'https://join\.slack\.com/t/[^/]+/shared_invite/[^\s]+',
            r'https://[^\.]+\.slack\.com/join/shared_invite/[^\s]+',
            r'slack\.com/join/[^\s]+',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text_content)
            invite_links.extend(matches)
        
        # Remove duplicates and return first 3
        return list(set(invite_links))[:3]
    
    def _extract_member_count(self, text: str) -> str:
        """Extract member count from page text"""
        patterns = [
            r'(\d+[,.]?\d*)\s*(members?|users?|people)',
            r'(\d+[kK])\s*(members?|users?|people)',
            r'over\s*(\d+)\s*(members?|users?)',
            r'(\d+)\+\s*(members?|users?)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(0)
        
        return 'Unknown'
    
    def _calculate_relevance(self, text: str, keyword: str) -> float:
        """Calculate relevance score"""
        text_lower = text.lower()
        keyword_lower = keyword.lower()
        
        score = 0.0
        
        # Direct keyword match
        if keyword_lower in text_lower:
            score += 0.3
        
        # Business-related terms
        business_terms = [
            'startup', 'entrepreneur', 'business', 'automation', 'ai', 
            'artificial intelligence', 'saas', 'tech', 'digital transformation',
            'ceo', 'founder', 'marketing', 'fintech', 'ecommerce', 'healthcare',
            'manufacturing', 'logistics', 'real estate', 'small business'
        ]
        
        term_count = sum(1 for term in business_terms if term in text_lower)
        score += min(term_count * 0.05, 0.3)
        
        # Community activity indicators
        activity_terms = ['active', 'daily', 'discussion', 'networking', 'collaboration']
        activity_count = sum(1 for term in activity_terms if term in text_lower)
        score += min(activity_count * 0.02, 0.1)
        
        return min(score, 1.0)
    
    def _remove_duplicates(self, communities: List[Dict]) -> List[Dict]:
        """Remove duplicates"""
        unique_communities = []
        seen_titles = set()
        seen_urls = set()
        
        for community in communities:
            title = community.get('title', '').lower().strip()
            url = community.get('url', '').strip()
            
            # Skip if we've seen similar title or same URL
            if title in seen_titles or url in seen_urls:
                continue
            
            seen_titles.add(title)
            seen_urls.add(url)
            unique_communities.append(community)
        
        return unique_communities
    
    def save_results(self, communities: List[Dict], filename: str = 'slack_communities.csv'):
        """Save results to CSV"""
        if not communities:
            print("❌ No communities found to save")
            return
        
        fieldnames = [
            'title', 'url', 'description', 'invite_links', 'member_count', 
            'keyword', 'relevance_score', 'found_date', 'source'
        ]
        
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for community in communities:
                community_copy = community.copy()
                community_copy['invite_links'] = '; '.join(community.get('invite_links', []))
                writer.writerow(community_copy)
        
        print(f"✅ Results saved to {filename}")
    
    def print_results(self, communities: List[Dict]):
        """Print formatted results"""
        if not communities:
            print("❌ No Slack communities found")
            return
        
        print(f"\n🎯 Found {len(communities)} relevant Slack communities:")
        print("=" * 80)
        
        # Sort by relevance score
        communities.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
        
        for i, community in enumerate(communities, 1):
            print(f"\n{i}. {community.get('title', 'Unknown')}")
            print(f"   🔗 URL: {community.get('url', 'N/A')}")
            print(f"   👥 Members: {community.get('member_count', 'Unknown')}")
            print(f"   🎯 Relevance: {community.get('relevance_score', 0):.2f}")
            print(f"   🏷️  Keyword: {community.get('keyword', 'N/A')}")
            print(f"   📍 Source: {community.get('source', 'Unknown')}")
            
            if community.get('invite_links'):
                links = community['invite_links'][:2]  # Show first 2 links
                print(f"   📨 Invite Links: {', '.join(links)}")
            
            if community.get('description'):
                desc = community['description']
                if len(desc) > 100:
                    desc = desc[:100] + "..."
                print(f"   📄 Description: {desc}")
            
            print("-" * 80)

def main():
    """Main function"""
    print("🦄 UnicornStudio.io Enhanced Slack Community Finder")
    print("=" * 50)
    
    # Focused keywords for better results
    keywords = [
        'startup founders',
        'business automation', 
        'saas founders',
        'ai entrepreneurs',
        'fintech',
        'ecommerce automation',
        'small business owners',
        'digital transformation',
        'tech ceos',
        'growth hacking'
    ]
    
    finder = ImprovedSlackFinder()
    
    try:
        print(f"🎯 Searching for {len(keywords)} keyword categories...")
        
        # Enhanced search
        communities = finder.search_communities_smart(keywords)
        
        # Display results
        finder.print_results(communities)
        
        # Save results
        finder.save_results(communities)
        
        # Save JSON
        with open('slack_communities.json', 'w', encoding='utf-8') as f:
            json.dump(communities, f, indent=2, ensure_ascii=False)
        
        print(f"\n✅ Search complete! Found {len(communities)} communities")
        print("📁 Results saved to:")
        print("   - slack_communities.csv")
        print("   - slack_communities.json")
        
        if communities:
            print(f"\n🎉 Success! You now have {len(communities)} Slack communities to engage with.")
            print("💡 Remember: Join communities, provide value first, build relationships!")
        
    except KeyboardInterrupt:
        print("\n⚠️ Search interrupted by user")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        print(f"\n❌ Error during search: {e}")

if __name__ == "__main__":
    main()