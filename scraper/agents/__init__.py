"""Multi-Agent system for distributed scraping."""
from .coordinator import AgentCoordinator
from .base_agent import BaseAgent, AgentMessage
from .serp_agent import SERPAgent
from .browser_agent import BrowserAgent
from .captcha_agent import CaptchaAgent
from .generic_agent import GenericAgent

__all__ = [
    "AgentCoordinator",
    "BaseAgent",
    "AgentMessage",
    "SERPAgent",
    "BrowserAgent",
    "CaptchaAgent",
    "GenericAgent",
]
