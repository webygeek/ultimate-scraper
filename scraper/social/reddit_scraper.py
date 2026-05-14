"""
Reddit Scraper - Specialized scraper for Reddit.
"""
import json
import time
import re
from typing import Dict, List, Optional
from dataclasses import dataclass
from loguru import logger


@dataclass
class RedditPost:
    """A Reddit post."""
    id: str
    subreddit: str
    title: str
    author: str
    created_utc: str
    score: int
    num_comments: int
    url: str
    permalink: str
    is_self: bool
    selftext: str
    link_flair_text: str


class RedditScraper:
    """
    Specialized scraper for Reddit.
    Uses Reddit's old.reddit.com for cleaner HTML.
    """

    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.rate_limit_delay = 1

    async def scrape_subreddit(
        self,
        subreddit: str,
        sort: str = "hot",
        max_posts: int = 25,
    ) -> List[Dict]:
        """
        Scrape a subreddit.

        Args:
            subreddit: Subreddit name (without r/)
            sort: hot, new, top, rising
            max_posts: Maximum posts to scrape

        Returns:
            List of posts
        """
        # Use old.reddit.com for cleaner HTML
        url = f"https://old.reddit.com/r/{subreddit}/{sort}/"

        posts = []
        page = 0

        while len(posts) < max_posts:
            page_url = f"{url}?count={page * 25}&after={page * 25}"
            page_posts = await self._scrape_page(page_url)

            if not page_posts:
                break

            posts.extend(page_posts)
            page += 1

            if len(posts) >= max_posts:
                break

            time.sleep(self.rate_limit_delay)

        return posts[:max_posts]

    async def scrape_post(self, permalink: str) -> Dict:
        """
        Scrape a single post.

        Args:
            permalink: Post permalink (with or without /r/)

        Returns:
            Post data with comments
        """
        if not permalink.startswith("http"):
            permalink = f"https://old.reddit.com{permalink}"

        return await self._scrape_page(permalink, single=True)

    async def scrape_user(self, username: str, max_posts: int = 25) -> Dict:
        """
        Scrape a user's profile.

        Args:
            username: Reddit username
            max_posts: Maximum posts

        Returns:
            User data
        """
        url = f"https://old.reddit.com/u/{username}/"

        posts = []
        page = 0

        while len(posts) < max_posts:
            page_url = f"{url}?count={page * 25}"
            page_posts = await self._scrape_page(page_url)

            if not page_posts:
                break

            posts.extend(page_posts)
            page += 1
            time.sleep(self.rate_limit_delay)

        return {
            "username": username,
            "posts": posts[:max_posts],
        }

    async def scrape_search(
        self,
        query: str,
        max_posts: int = 25,
    ) -> List[Dict]:
        """
        Scrape Reddit search results.

        Args:
            query: Search query
            max_posts: Maximum posts

        Returns:
            Search results
        """
        encoded_query = query.replace(" ", "+")
        url = f"https://old.reddit.com/search/?q={encoded_query}&sort=relevance"

        posts = []
        page = 0

        while len(posts) < max_posts:
            page_url = f"{url}&count={page * 25}"
            page_posts = await self._scrape_page(page_url)

            if not page_posts:
                break

            posts.extend(page_posts)
            page += 1
            time.sleep(self.rate_limit_delay)

        return posts[:max_posts]

    async def _scrape_page(self, url: str, single: bool = False) -> List[Dict]:
        """Internal page scraper."""
        try:
            import requests

            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "text/html,application/xhtml+xml",
            }

            response = requests.get(url, headers=headers, timeout=30)

            if response.status_code != 200:
                return []

            return self._parse_html(response.text, single=single)

        except Exception as e:
            logger.error(f"Reddit scrape failed: {e}")
            return []

    def _parse_html(self, html: str, single: bool = False) -> List[Dict]:
        """Parse Reddit HTML."""
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "lxml")
        posts = []

        # Find post containers
        if single:
            # Single post page
            post_div = soup.find("div", {"class": "thing"})
            if post_div:
                posts.append(self._parse_post(post_div))

            # Comments
            comments = self._parse_comments(soup)
            if posts:
                posts[0]["comments"] = comments

        else:
            # Post listing
            for div in soup.find_all("div", {"class": "thing"}):
                post = self._parse_post(div)
                if post:
                    posts.append(post)

        return posts

    def _parse_post(self, div) -> Dict:
        """Parse a single post div."""
        post = {
            "id": div.get("data-id", ""),
            "subreddit": div.get("data-subreddit", ""),
            "title": "",
            "author": div.get("data-author", ""),
            "score": 0,
            "num_comments": 0,
            "url": "",
            "permalink": "",
            "is_self": False,
            "selftext": "",
            "created_utc": div.get("data-timestamp", ""),
        }

        # Title
        title_elem = div.find("a", {"class": "title"})
        if title_elem:
            post["title"] = title_elem.get_text(strip=True)
            post["url"] = title_elem.get("href", "")

        # Score
        score_elem = div.find("div", {"class": "score"})
        if score_elem:
            try:
                score_text = score_elem.get_text(strip=True)
                if score_text == "•":
                    score_text = div.find("span", {"class": "score"}).get_text(strip=True) if div.find("span", {"class": "score"}) else "0"
                post["score"] = int(score_text.replace(",", ""))
            except:
                pass

        # Comments
        comments_elem = div.find("a", {"class": "comments"})
        if comments_elem:
            try:
                comments_text = comments_elem.get_text(strip=True)
                match = re.search(r'(\d+)', comments_text)
                if match:
                    post["num_comments"] = int(match.group(1))
            except:
                pass

        # Permalink
        if comments_elem:
            post["permalink"] = "https://old.reddit.com" + comments_elem.get("href", "")

        # Self post check
        post["is_self"] = post["url"].startswith("/r/") or not post["url"].startswith("http")

        # Selftext
        if post["is_self"]:
            selftext_elem = div.find("div", {"class": "usertext-body"})
            if selftext_elem:
                post["selftext"] = selftext_elem.get_text(strip=True)

        return post

    def _parse_comments(self, soup) -> List[Dict]:
        """Parse comments from post page."""
        comments = []

        for entry in soup.find_all("div", {"class": "entry"}):
            comment = {
                "author": "",
                "body": "",
                "score": 0,
                "created": "",
            }

            # Author
            author_elem = entry.find("a", {"class": "author"})
            if author_elem:
                comment["author"] = author_elem.get_text(strip=True)

            # Body
            body_elem = entry.find("div", {"class": "md"})
            if body_elem:
                comment["body"] = body_elem.get_text(strip=True)

            # Score
            score_elem = entry.find("span", {"class": "score"})
            if score_elem:
                try:
                    comment["score"] = int(score_elem.get_text(strip=True).replace(",", ""))
                except:
                    pass

            if comment["body"]:
                comments.append(comment)

        return comments[:50]  # Limit comments
