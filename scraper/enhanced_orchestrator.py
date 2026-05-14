"""
Ultimate Self-Evolving Scraper
Combines Multi-Agent, LLM-Powered, and Visual Learning systems.
"""
import asyncio
import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from loguru import logger

from .skills import SkillDatabase, ProblemAnalyzer, Problem
from .agents import (
    AgentCoordinator,
    SERPAgent, BrowserAgent, CaptchaAgent, GenericAgent,
    BaseAgent, Task, AgentResult
)
from .ai_solution_generator import LLMSolutionGenerator, Solution
from .visual import VisualLearner, Demonstration


@dataclass
class UltimateScrapeResult:
    """Complete result from ultimate scraper."""
    success: bool
    data: List[Dict]
    method: str
    techniques_used: List[str]
    agent_used: str
    skill_id: Optional[int]
    llm_solution: Optional[Solution]
    workflow_used: Optional[str]
    duration_ms: int
    attempts: int
    learned_skill_id: Optional[int]
    error: Optional[str] = None


class UltimateSelfEvolvingScraper:
    """
    Ultimate self-evolving scraper with all intelligence systems.
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config

        # Initialize all systems
        self.skill_db = SkillDatabase()
        self.problem_analyzer = ProblemAnalyzer()
        self.llm_generator = LLMSolutionGenerator(config)
        self.visual_learner = VisualLearner()

        # Initialize multi-agent system
        self.coordinator = AgentCoordinator(config)
        self._register_agents()

        # Settings
        self.max_attempts = 10
        self.enable_llm = True
        self.enable_visual = True
        self.enable_agents = True

    def _register_agents(self):
        """Register all specialized agents."""
        self.coordinator.register_agent(SERPAgent("serp_agent", self.config))
        self.coordinator.register_agent(BrowserAgent("browser_agent", self.config))
        self.coordinator.register_agent(CaptchaAgent("captcha_agent", self.config))
        self.coordinator.register_agent(GenericAgent("generic_agent", self.config))

    async def scrape(
        self,
        url: str,
        selectors: Dict[str, str] = None,
        task_type: str = "generic",
    ) -> UltimateScrapeResult:
        """
        Scrape with full intelligence.

        Strategy:
        1. Check for learned workflow (visual learning)
        2. Check for matching skill
        3. Use specialized agent
        4. Generate LLM solution for novel problems
        5. Learn from result
        """
        start_time = time.time()
        techniques_used = []
        agents_used = []
        skill_id = None
        llm_solution = None
        workflow_used = None

        logger.info(f"Ultimate scrape starting: {url}")

        # Step 1: Check visual learning workflows
        if self.enable_visual:
            workflow = self.visual_learner.find_workflow(url)
            if workflow:
                logger.info(f"Found learned workflow: {workflow.name}")
                workflow_used = workflow.name
                techniques_used.append("visual_learned")
                # Could replay workflow here

        # Step 2: Check for matching skills
        problem_context = {"url": url}
        skills = self.skill_db.find_skills(site_pattern=url, min_confidence=0.3, limit=5)
        if skills:
            best_skill = skills[0]
            skill_id = best_skill.id
            logger.info(f"Found skill: {best_skill.name}")
            techniques_used.append(f"skill:{best_skill.solution_type}")

        # Step 3: Analyze problem (check for blocks)
        html = ""
        try:
            from .modules.anti_detection import RequestSession
            session = RequestSession(self.config)
            response = session.get(url)
            html = response.text
        except Exception as e:
            logger.debug(f"Initial request failed: {e}")

        problem = self.problem_analyzer.analyze_response(
            url=url,
            html=html,
            status_code=0,
            error_message="",
        )

        if problem:
            logger.info(f"Detected problem: {problem.problem_type}")

            # Step 4: Try LLM for novel problems
            if self.enable_llm and skill_id is None:
                llm_solution = await self.llm_generator.generate_solution({
                    "problem_type": problem.problem_type,
                    "url": url,
                    "evidence": problem.evidence,
                    "keywords": problem.keywords,
                })
                logger.info(f"LLM generated solution: {llm_solution.technique}")
                techniques_used.append(f"llm:{llm_solution.technique}")

        # Step 5: Use multi-agent system
        if self.enable_agents:
            task = Task(
                task_type=task_type,
                url=url,
                selectors=selectors or {},
                context={"html": html, "problem": problem.__dict__ if problem else {}},
                max_attempts=5,
            )

            # Use agent team
            agent = self.coordinator.get_best_agent_for(task_type)
            if agent:
                logger.info(f"Using agent: {agent.name}")
                agents_used.append(agent.name)

                result = self.coordinator.submit_task(task)
                if result and result.success:
                    duration = int((time.time() - start_time) * 1000)
                    techniques_used.extend(result.techniques_used)

                    # Step 6: Learn from result
                    if result.success:
                        await self._learn_from_success(
                            url, result, problem, llm_solution
                        )

                    return UltimateScrapeResult(
                        success=True,
                        data=result.data,
                        method="multi_agent",
                        techniques_used=techniques_used,
                        agent_used=agent.name,
                        skill_id=skill_id,
                        llm_solution=llm_solution,
                        workflow_used=workflow_used,
                        duration_ms=duration,
                        attempts=result.attempts,
                        learned_skill_id=None,
                    )

        # Fallback: Try direct scraping
        data = await self._direct_scrape(url, selectors, html)

        duration = int((time.time() - start_time) * 1000)

        return UltimateScrapeResult(
            success=len(data) > 0,
            data=data,
            method="direct",
            techniques_used=techniques_used,
            agent_used="direct",
            skill_id=skill_id,
            llm_solution=llm_solution,
            workflow_used=workflow_used,
            duration_ms=duration,
            attempts=1,
            learned_skill_id=None,
            error=None if data else "All methods failed",
        )

    async def _direct_scrape(
        self,
        url: str,
        selectors: Dict[str, str],
        html: str,
    ) -> List[Dict]:
        """Direct scraping as fallback."""
        from bs4 import BeautifulSoup

        if not html:
            try:
                from .modules.anti_detection import RequestSession
                session = RequestSession(self.config)
                response = session.get(url)
                html = response.text
            except Exception as e:
                logger.error(f"Direct scrape failed: {e}")
                return []

        soup = BeautifulSoup(html, "lxml")

        if not selectors:
            selectors = self._auto_detect_selectors(soup)

        results = []
        containers = self._find_containers(soup)

        for container in containers:
            item = {}
            for field_name, selector in selectors.items():
                elem = container.select_one(selector)
                if elem:
                    if field_name == "url":
                        item[field_name] = elem.get("href", "")
                    elif field_name == "image":
                        item[field_name] = elem.get("src", "")
                    else:
                        item[field_name] = elem.get_text(strip=True)
            if item:
                results.append(item)

        return results

    def _auto_detect_selectors(self, soup) -> Dict[str, str]:
        """Auto-detect selectors."""
        selectors = {}
        if soup.select_one("h1, h2"):
            selectors["title"] = "h1, h2"
        if soup.select_one("a[href]"):
            selectors["url"] = "a[href]"
        if soup.select_one("img"):
            selectors["image"] = "img"
        return selectors

    def _find_containers(self, soup) -> List:
        """Find data containers."""
        patterns = [
            "[class*='item']", "[class*='card']", "[class*='product']",
            "[class*='listing']", "[class*='result']", "article",
        ]
        for pattern in patterns:
            containers = soup.select(pattern)
            if len(containers) > 1:
                return containers
        return [soup]

    async def _learn_from_success(
        self,
        url: str,
        result: AgentResult,
        problem: Optional[Problem],
        llm_solution: Optional[Solution],
    ):
        """Learn from successful scrape."""
        # Learn skill
        if problem and llm_solution:
            from .skills import SkillGenerator
            generator = SkillGenerator(self.skill_db)

            new_skill = generator.generate_skill_from_solution(
                problem=problem,
                solution={
                    "method": llm_solution.technique,
                    "changes": llm_solution.config,
                    "applied_techniques": result.techniques_used,
                },
                url=url,
                success=True,
            )

            if new_skill:
                skill_id = self.skill_db.add_skill(new_skill)
                logger.info(f"Learned new skill: {new_skill.name} (ID: {skill_id})")

        # Share with agents
        self.coordinator.share_best_skills()

        # Update LLM generator
        if llm_solution:
            self.llm_generator.learn_from_result(
                {"url": url, "problem_type": problem.problem_type if problem else "unknown"},
                llm_solution,
                success=True
            )

    def record_demonstration(
        self,
        url: str,
        name: str,
        description: str = "",
        actions: List[Dict] = None,
    ):
        """Record a visual demonstration."""
        from .visual import Action

        self.visual_learner.start_recording(url, name, description)

        if actions:
            for action in actions:
                self.visual_learner.record_action(
                    action_type=action.get("type", "click"),
                    selector=action.get("selector", ""),
                    value=action.get("value", ""),
                )

        self.visual_learner.stop_recording(tags=[url])

    def get_all_stats(self) -> Dict[str, Any]:
        """Get comprehensive statistics from all systems."""
        return {
            "skills": self.skill_db.get_statistics(),
            "llm": self.llm_generator.get_capabilities(),
            "agents": self.coordinator.get_statistics(),
            "visual": {
                "demonstrations": len(self.visual_learner.demonstrations),
                "workflows": len(self.visual_learner.workflows),
            },
        }

    def export_all_knowledge(self, filepath: str):
        """Export all learned knowledge."""
        import json

        data = {
            "skills": [],
            "visual_workflows": [w.to_dict() for w in self.visual_learner.workflows.values()],
            "exported_at": time.time(),
        }

        # Export skills
        self.skill_db.export_skills(filepath.replace(".json", "_skills.json"))

        # Export visual learnings
        with open(filepath.replace(".json", "_visual.json"), "w") as f:
            json.dump(data["visual_workflows"], f, indent=2)

        logger.info(f"Exported knowledge to {filepath}")

    def import_all_knowledge(self, skills_file: str, visual_file: str = None):
        """Import learned knowledge."""
        if skills_file:
            count = self.skill_db.import_skills(skills_file)
            logger.info(f"Imported {count} skills")

        if visual_file:
            import json
            with open(visual_file) as f:
                workflows = json.load(f)
            logger.info(f"Imported {len(workflows)} visual workflows")


# Sync wrapper for easier usage
class Scraper:
    """Synchronous wrapper for UltimateSelfEvolvingScraper."""

    def __init__(self, config: Dict[str, Any] = None):
        if config is None:
            import yaml
            try:
                with open("config.yaml") as f:
                    config = yaml.safe_load(f)
            except:
                config = {}

        self._async = UltimateSelfEvolvingScraper(config)

    def scrape(
        self,
        url: str,
        selectors: Dict[str, str] = None,
        task_type: str = "generic",
    ) -> UltimateScrapeResult:
        """Synchronous scrape."""
        return asyncio.run(self._async.scrape(url, selectors, task_type))

    def record_demonstration(
        self,
        url: str,
        name: str,
        description: str = "",
        actions: List[Dict] = None,
    ):
        """Record a demonstration."""
        self._async.record_demonstration(url, name, description, actions)

    def get_stats(self) -> Dict[str, Any]:
        """Get all statistics."""
        return self._async.get_all_stats()
