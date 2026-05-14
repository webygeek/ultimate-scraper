"""
Visual Learning System - Learn scraping workflows by demonstration.
Records user actions and replays them automatically.
"""
import json
import time
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from pathlib import Path
from loguru import logger


@dataclass
class Action:
    """A single action in a demonstration."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    action_type: str = ""  # click, type, scroll, wait, select, navigate
    selector: str = ""
    value: str = ""
    timestamp: float = field(default_factory=time.time)
    duration_ms: int = 0
    screenshot_before: str = ""
    screenshot_after: str = ""
    html_snapshot: str = ""
    result: str = ""  # What happened after this action


@dataclass
class Demonstration:
    """A complete demonstration of a scraping workflow."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    url: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    actions: List[Action] = field(default_factory=list)
    total_duration_ms: int = 0
    success_indicators: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)

    def add_action(self, action: Action):
        """Add an action to the demonstration."""
        self.actions.append(action)

    def get_duration(self) -> int:
        """Calculate total duration."""
        if self.actions:
            return int((self.actions[-1].timestamp - self.actions[0].timestamp) * 1000)
        return 0

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "url": self.url,
            "created_at": self.created_at,
            "action_count": len(self.actions),
            "total_duration_ms": self.get_duration(),
            "success_indicators": self.success_indicators,
            "tags": self.tags,
        }


@dataclass
class LearnedWorkflow:
    """A workflow learned from demonstrations."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    url_pattern: str = ""  # URL pattern this applies to
    demonstrations: List[str] = field(default_factory=list)  # Demo IDs
    extracted_actions: List[Dict] = field(default_factory=list)  # Generalized actions
    selectors: Dict[str, str] = field(default_factory=dict)  # CSS selectors learned
    success_rate: float = 0.0
    use_count: int = 0
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_used_at: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "url_pattern": self.url_pattern,
            "action_count": len(self.extracted_actions),
            "selectors": self.selectors,
            "success_rate": self.success_rate,
            "use_count": self.use_count,
        }


class VisualLearner:
    """
    Learn scraping workflows by watching demonstrations.
    Users show the scraper what to do, and it learns to replicate.
    """

    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = Path(__file__).parent.parent.parent / "data" / "visual_learnings.json"

        self.db_path = str(db_path)
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

        self.demonstrations: Dict[str, Demonstration] = {}
        self.workflows: Dict[str, LearnedWorkflow] = {}
        self.current_demo: Optional[Demonstration] = None

        self._load()

    def _load(self):
        """Load data from disk."""
        if Path(self.db_path).exists():
            try:
                with open(self.db_path) as f:
                    data = json.load(f)
                    self.demonstrations = {
                        k: self._dict_to_demo(v) for k, v in data.get("demonstrations", {}).items()
                    }
                    self.workflows = {
                        k: self._dict_to_workflow(v) for k, v in data.get("workflows", {}).items()
                    }
            except Exception as e:
                logger.warning(f"Failed to load visual learnings: {e}")

    def _save(self):
        """Save data to disk."""
        data = {
            "demonstrations": {
                k: self._demo_to_dict(v) for k, v in self.demonstrations.items()
            },
            "workflows": {
                k: self._workflow_to_dict(v) for k, v in self.workflows.items()
            },
        }
        with open(self.db_path, "w") as f:
            json.dump(data, f, indent=2)

    def _dict_to_demo(self, d: dict) -> Demonstration:
        """Convert dict to Demonstration."""
        return Demonstration(
            id=d["id"],
            name=d.get("name", ""),
            description=d.get("description", ""),
            url=d.get("url", ""),
            created_at=d.get("created_at", ""),
            actions=[Action(**a) for a in d.get("actions", [])],
            success_indicators=d.get("success_indicators", []),
            tags=d.get("tags", []),
        )

    def _dict_to_workflow(self, d: dict) -> LearnedWorkflow:
        """Convert dict to LearnedWorkflow."""
        return LearnedWorkflow(
            id=d["id"],
            name=d.get("name", ""),
            url_pattern=d.get("url_pattern", ""),
            demonstrations=d.get("demonstrations", []),
            extracted_actions=d.get("extracted_actions", []),
            selectors=d.get("selectors", {}),
            success_rate=d.get("success_rate", 0.0),
            use_count=d.get("use_count", 0),
            created_at=d.get("created_at", ""),
            last_used_at=d.get("last_used_at", ""),
        )

    def _demo_to_dict(self, demo: Demonstration) -> dict:
        """Convert Demonstration to dict."""
        return {
            "id": demo.id,
            "name": demo.name,
            "description": demo.description,
            "url": demo.url,
            "created_at": demo.created_at,
            "actions": [a.__dict__ for a in demo.actions],
            "success_indicators": demo.success_indicators,
            "tags": demo.tags,
        }

    def _workflow_to_dict(self, wf: LearnedWorkflow) -> dict:
        """Convert LearnedWorkflow to dict."""
        return {
            "id": wf.id,
            "name": wf.name,
            "url_pattern": wf.url_pattern,
            "demonstrations": wf.demonstrations,
            "extracted_actions": wf.extracted_actions,
            "selectors": wf.selectors,
            "success_rate": wf.success_rate,
            "use_count": wf.use_count,
            "created_at": wf.created_at,
            "last_used_at": wf.last_used_at,
        }

    # ============== RECORDING ==============

    def start_recording(self, url: str, name: str = "", description: str = ""):
        """Start recording a new demonstration."""
        self.current_demo = Demonstration(
            name=name or f"Demo {len(self.demonstrations) + 1}",
            description=description,
            url=url,
        )
        logger.info(f"Started recording demonstration: {name}")

    def record_action(
        self,
        action_type: str,
        selector: str = "",
        value: str = "",
        result: str = "",
        html_snapshot: str = "",
    ):
        """Record a single action."""
        if not self.current_demo:
            logger.warning("No active recording")
            return

        action = Action(
            action_type=action_type,
            selector=selector,
            value=value,
            result=result,
            html_snapshot=html_snapshot,
        )
        self.current_demo.add_action(action)

    def stop_recording(self, success_indicators: List[str] = None, tags: List[str] = None):
        """Stop recording and save the demonstration."""
        if not self.current_demo:
            return None

        self.current_demo.success_indicators = success_indicators or []
        self.current_demo.tags = tags or []

        # Save demo
        self.demonstrations[self.current_demo.id] = self.current_demo

        demo_id = self.current_demo.id
        demo = self.current_demo
        self.current_demo = None

        # Learn workflow from demonstration
        self._learn_from_demonstration(demo)

        self._save()
        logger.info(f"Stopped recording. Demo ID: {demo_id}")

        return demo_id

    # ============== LEARNING ==============

    def _learn_from_demonstration(self, demo: Demonstration):
        """Extract workflow patterns from demonstration."""
        # Extract selectors used
        selectors = {}
        action_patterns = []

        for action in demo.actions:
            if action.selector:
                # Try to generalize the selector
                generalized = self._generalize_selector(action.selector)
                action_patterns.append({
                    "type": action.action_type,
                    "selector": generalized,
                    "value": action.value if action.action_type in ["type", "select"] else "",
                })

                # Extract field selectors
                if action.action_type == "click":
                    # Try to infer what field this clicks
                    field_name = self._infer_field_name(action, demo)
                    if field_name and generalized:
                        selectors[field_name] = generalized

        # Create workflow
        from urllib.parse import urlparse
        url_parts = urlparse(demo.url)
        url_pattern = f"{url_parts.scheme}://{url_parts.netloc}/*"

        workflow = LearnedWorkflow(
            name=demo.name,
            url_pattern=url_pattern,
            demonstrations=[demo.id],
            extracted_actions=action_patterns,
            selectors=selectors,
        )

        self.workflows[workflow.id] = workflow
        logger.info(f"Learned workflow: {workflow.name}")

    def _generalize_selector(self, selector: str) -> str:
        """Generalize a CSS selector to be more robust."""
        # Remove dynamic parts
        import re

        # Remove nth-child with numbers
        selector = re.sub(r':nth-child\(\d+\)', '', selector)

        # Replace specific indices with :first-of-type
        selector = re.sub(r':nth-of-type\(\d+\)', ':first-of-type', selector)

        # Keep only stable parts (class names, IDs, tags)
        # This is a simplified version
        return selector

    def _infer_field_name(self, action: Action, demo: Demonstration) -> Optional[str]:
        """Infer what field this action interacts with."""
        selector = action.selector.lower()

        # Try to infer from surrounding context or page structure
        field_mappings = {
            "title": ["h1", "h2", "[class*='title']", "[class*='heading']"],
            "price": ["[class*='price']", "[class*='cost']", "[id*='price']"],
            "description": ["p", "[class*='desc']", "[class*='text']"],
            "image": ["img", "[class*='image']", "[class*='photo']"],
            "link": ["a", "[class*='link']"],
        }

        for field_name, patterns in field_mappings.items():
            if any(p.lower() in selector for p in patterns):
                return field_name

        return None

    # ============== REPLAY ==============

    def find_workflow(self, url: str) -> Optional[LearnedWorkflow]:
        """Find best matching workflow for a URL."""
        from urllib.parse import urlparse

        url_parts = urlparse(url)
        target_netloc = url_parts.netloc

        best_match = None
        best_score = 0

        for workflow in self.workflows.values():
            # Check URL pattern match
            pattern_parts = urlparse(workflow.url_pattern)
            pattern_netloc = pattern_parts.netloc

            if pattern_netloc == target_netloc:
                # Direct match
                score = workflow.success_rate * 100 + workflow.use_count
                if score > best_score:
                    best_score = score
                    best_match = workflow

        return best_match

    async def replay_workflow(
        self,
        workflow: LearnedWorkflow,
        url: str,
        browser: Any,
    ) -> List[Dict[str, Any]]:
        """Replay a learned workflow on a URL."""
        logger.info(f"Replaying workflow: {workflow.name}")

        workflow.use_count += 1
        workflow.last_used_at = datetime.now().isoformat()

        # Navigate to URL
        browser.goto(url)
        time.sleep(1)

        results = []

        # Execute each action
        for action_def in workflow.extracted_actions:
            action_type = action_def.get("type", "")
            selector = action_def.get("selector", "")
            value = action_def.get("value", "")

            try:
                if action_type == "navigate":
                    browser.goto(value)

                elif action_type == "click":
                    elem = browser.wait_for_selector(selector, timeout=5000)
                    if elem:
                        elem.click()

                elif action_type == "type":
                    elem = browser.wait_for_selector(selector, timeout=5000)
                    if elem:
                        elem.fill(value)

                elif action_type == "wait":
                    time.sleep(float(selector) / 1000 if selector.isdigit() else 2)

                elif action_type == "scroll":
                    browser.evaluate(f"window.scrollBy(0, {selector or 500})")

                time.sleep(0.5)

            except Exception as e:
                logger.debug(f"Action failed: {e}")
                continue

        # Extract data using learned selectors
        for field_name, selector in workflow.selectors.items():
            try:
                elem = browser.query_selector(selector)
                if elem:
                    value = elem.inner_text() or elem.get_attribute("src") or ""
                    results.append({field_name: value})
            except Exception:
                continue

        self._save()
        return results

    # ============== MANAGEMENT ==============

    def list_demonstrations(self) -> List[dict]:
        """List all demonstrations."""
        return [d.to_dict() for d in self.demonstrations.values()]

    def list_workflows(self) -> List[dict]:
        """List all learned workflows."""
        return [w.to_dict() for w in self.workflows.values()]

    def delete_demonstration(self, demo_id: str):
        """Delete a demonstration."""
        if demo_id in self.demonstrations:
            del self.demonstrations[demo_id]
            self._save()

    def delete_workflow(self, workflow_id: str):
        """Delete a workflow."""
        if workflow_id in self.workflows:
            del self.workflows[workflow_id]
            self._save()

    def improve_workflow(self, workflow_id: str, demonstration_id: str):
        """Improve a workflow with a new demonstration."""
        if workflow_id not in self.workflows:
            return

        if demonstration_id not in self.demonstrations:
            return

        workflow = self.workflows[workflow_id]
        demo = self.demonstrations[demonstration_id]

        # Add demonstration to workflow
        workflow.demonstrations.append(demo_id)

        # Re-learn from all demonstrations
        self._relarn_workflow(workflow)

        self._save()

    def _relarn_workflow(self, workflow: LearnedWorkflow):
        """Re-learn a workflow from all its demonstrations."""
        all_selectors = {}
        all_actions = []

        for demo_id in workflow.demonstrations:
            if demo_id in self.demonstrations:
                demo = self.demonstrations[demo_id]
                for action in demo.actions:
                    if action.selector:
                        generalized = self._generalize_selector(action.selector)
                        all_actions.append({
                            "type": action.action_type,
                            "selector": generalized,
                        })
                    field_name = self._infer_field_name(action, demo)
                    if field_name and action.selector:
                        all_selectors[field_name] = self._generalize_selector(action.selector)

        workflow.selectors = all_selectors
        workflow.extracted_actions = all_actions


# ============== COMMAND-LINE RECORDING ==============

def record_demo_cli(learner: VisualLearner, url: str, name: str):
    """Start CLI-based recording."""
    print(f"Starting demonstration recording for: {url}")
    print("Actions will be recorded. Type 'stop' to finish.")
    print()

    learner.start_recording(url, name=name)

    action_types = ["click", "type", "scroll", "wait", "select"]

    while True:
        print("\nRecorded actions so far:", len(learner.current_demo.actions))
        print("Actions:", [a.action_type for a in learner.current_demo.actions])

        action = input("\nAction type (click/type/scroll/wait/stop): ").strip().lower()

        if action == "stop":
            tags = input("Tags (comma-separated): ").strip()
            learner.stop_recording(
                tags=[t.strip() for t in tags.split(",")] if tags else [],
                success_indicators=["has_results"],
            )
            print("Recording stopped.")
            break

        if action not in action_types:
            print(f"Unknown action. Use: {', '.join(action_types)}")
            continue

        selector = input("CSS selector: ").strip()
        value = ""
        if action == "type":
            value = input("Value to type: ").strip()

        learner.record_action(action, selector, value)
        print(f"Recorded: {action} on {selector}")
