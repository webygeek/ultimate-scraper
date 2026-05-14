"""E-commerce Scrapers module."""
from .amazon_scraper import AmazonScraper
from .ecommerce_base import EcommerceScraper, Product

__all__ = ["AmazonScraper", "EcommerceScraper", "Product"]
