"""
Twitter/X Scraper - Specialized scraper for Twitter/X.
"""
import json
import re
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from loguru import logger


@dataclass
class Tweet:
    """A tweet."""
    id: str
    text: str
    author: str
    author_handle: str
    created_at: str
    likes: int
    retweets: int
    replies: int
    url: str
    is_retweet: bool
    is_reply: bool
    media: List[str]


class TwitterScraper:
    """
    Specialized scraper for Twitter/X.
    Handles Twitter's heavy JavaScript rendering and anti-bot measures.
    """

    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.rate_limit_delay = 2

    async def scrape_profile(self, username: str) -> Dict:
        """
        Scrape a Twitter profile.

        Args:
            username: Twitter handle (without @)

        Returns:
            Profile data
        """
        url = f"https://x.com/{username}"
        return await self._scrape(url, "profile")

    async def scrape_tweet(self, tweet_id: str) -> Dict:
        """
        Scrape a single tweet.

        Args:
            tweet_id: Tweet ID

        Returns:
            Tweet data
        """
        url = f"https://x.com/i/status/{tweet_id}"
        return await self._scrape(url, "tweet")

    async def scrape_search(self, query: str, max_results: int = 20) -> List[Dict]:
        """
        Scrape Twitter search results.

        Args:
            query: Search query
            max_results: Maximum results

        Returns:
            List of tweets
        """
        # Twitter search URL
        encoded_query = query.replace(" ", "%20")
        url = f"https://x.com/search?q={encoded_query}&f=live"

        tweets = []
        page = 1
        while len(tweets) < max_results:
            page_url = f"{url}&page={page}"
            result = await self._scrape(page_url, "search")

            if result and result.get("tweets"):
                tweets.extend(result["tweets"][:max_results - len(tweets)])
            else:
                break

            page += 1
            time.sleep(self.rate_limit_delay)

        return tweets[:max_results]

    async def scrape_trending(self) -> List[Dict]:
        """
        Scrape trending topics.

        Returns:
            List of trending topics
        """
        url = "https://x.com/explore/tabs/trending"
        result = await self._scrape(url, "trending")

        return result.get("trending", [])

    async def _scrape(self, url: str, scrape_type: str) -> Dict:
        """Internal scrape method."""
        try:
            from playwright.sync_api import sync_playwright

            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    viewport={"width": 1280, "height": 720},
                )
                page = context.new_page()

                # Twitter blocks - try to bypass
                page.set_extra_http_headers({
                    "Accept-Language": "en-US,en;q=0.9",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                })

                page.goto(url, wait_until="networkidle", timeout=30000)

                # Wait for content
                time.sleep(3)

                # Get page HTML
                html = page.content()

                # Extract data based on type
                if scrape_type == "profile":
                    return self._parse_profile(html, username=url.split("/")[-1])
                elif scrape_type == "tweet":
                    return self._parse_tweet(html)
                elif scrape_type == "search":
                    return {"tweets": self._parse_tweets(html)}
                elif scrape_type == "trending":
                    return {"trending": self._parse_trending(html)}

                browser.close()

        except Exception as e:
            logger.error(f"Twitter scrape failed: {e}")

        return {}

    def _parse_profile(self, html: str, username: str) -> Dict:
        """Parse profile HTML."""
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "lxml")
        profile = {
            "username": username,
            "name": "",
            "bio": "",
            "followers": 0,
            "following": 0,
            "tweets": 0,
            "verified": False,
            "joined": "",
        }

        # Try to extract from page data
        script_tags = soup.find_all("script")
        for script in script_tags:
            text = script.string or ""
            if "User" in text and "following" in text:
                # Try to extract JSON
                match = re.search(r'"followersCount":(\d+)', text)
                if match:
                    profile["followers"] = int(match.group(1))

                match = re.search(r'"followingCount":(\d+)', text)
                if match:
                    profile["following"] = int(match.group(1))

        return profile

    def _parse_tweet(self, html: str) -> Dict:
        """Parse tweet HTML."""
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "lxml")
        tweet = {
            "id": "",
            "text": "",
            "author": "",
            "created_at": "",
            "likes": 0,
            "retweets": 0,
            "replies": 0,
        }

        # Find tweet container
        article = soup.find("article")
        if article:
            # Text
            text_elem = article.find("div", attrs={"data-testid": "tweetText"})
            if text_elem:
                tweet["text"] = text_elem.get_text(strip=True)

            # Metrics
            for span in article.find_all("span"):
                text = span.get_text(strip=True)
                if text.endswith("likes"):
                    try:
                        tweet["likes"] = int(text.split()[0].replace(",", ""))
                    except:
                        pass
                elif text.endswith("reposts"):
                    try:
                        tweet["retweets"] = int(text.split()[0].replace(",", ""))
                    except:
                        pass

        return tweet

    def _parse_tweets(self, html: str) -> List[Dict]:
        """Parse tweet list."""
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "lxml")
        tweets = []

        # Find tweet containers
        articles = soup.find_all("article")

        for article in articles:
            tweet = self._parse_tweet(str(article))
            if tweet.get("text"):
                tweets.append(tweet)

        return tweets

    def _parse_trending(self, html: str) -> List[Dict]:
        """Parse trending topics."""
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "lxml")
        trending = []

        # Find trending items
        for a in soup.find_all("a", href=re.compile(r"/hashtag/")):
            href = a.get("href", "")
            text = a.get_text(strip=True)

            if text and len(text) < 100:
                trending.append({
                    "hashtag": text,
                    "url": f"https://x.com{href}",
                })

        return trending[:10]
