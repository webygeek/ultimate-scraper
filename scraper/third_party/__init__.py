"""
Third-Party Web Scraping Services Reference

This module contains information about external web scraping services.
Use this as a reference for choosing the right service for your needs.

Quick Usage:
    from scraper.third_party import SCRAPING_SERVICES, get_free_services

    # Get all services
    for service in SCRAPING_SERVICES:
        print(f"{service['name']}: {service['website']}")

    # Get free services
    for service in get_free_services():
        print(f"FREE: {service['name']}")

    # Feature gap analysis
    from scraper.third_party import analyze_gaps, FEATURES_WE_CAN_BUILD
"""
from .scraping_services import (
    SCRAPING_SERVICES,
    get_services_by_tier,
    get_services_by_feature,
    get_free_services,
    get_services_by_use_case,
    compare_services,
    get_recommendation,
    QUICK_REFERENCE,
)

from .feature_gap_analysis import (
    OUR_FEATURES,
    PAID_SERVICE_FEATURES,
    FEATURES_WE_CAN_BUILD,
    FEATURES_REQUIRING_PAID,
    FEATURE_IMPLEMENTATION_ORDER,
    analyze_gaps,
    get_feature_plan,
)

__all__ = [
    # Scraping services
    "SCRAPING_SERVICES",
    "get_services_by_tier",
    "get_services_by_feature",
    "get_free_services",
    "get_services_by_use_case",
    "compare_services",
    "get_recommendation",
    "QUICK_REFERENCE",
    # Feature gap analysis
    "OUR_FEATURES",
    "PAID_SERVICE_FEATURES",
    "FEATURES_WE_CAN_BUILD",
    "FEATURES_REQUIRING_PAID",
    "FEATURE_IMPLEMENTATION_ORDER",
    "analyze_gaps",
    "get_feature_plan",
]
