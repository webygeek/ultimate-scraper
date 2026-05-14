"""
Base Agent - Foundation for all specialized agents.
"""
import json
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum
from loguru import logger


class MessageType(Enum):
    """Types of messages between agents."""
    TASK = "task"
    RESULT = "result"
    ERROR = "error"
    QUERY = "query"
    RESPONSE = "response"
    HELP_REQUEST = "help_request"
    HELP_RESPONSE = "help_response"
    LEARN = "learn"
    SHARE_SKILL = "share_skill"


class Priority(Enum):
    """Message priority levels."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class AgentMessage:
    """Message passed between agents."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: MessageType = MessageType.TASK
    sender: str = ""
    recipient: str = ""
    content: Dict[str, Any] = field(default_factory=dict)
    priority: Priority = Priority.NORMAL
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    reply_to: str = ""
    ttl: int = 10  # Time to live (hops)

    def to_json(self) -> str:
        return json.dumps({
            "id": self.id,
            "type": self.type.value,
            "sender": self.sender,
            "recipient": self.recipient,
            "content": self.content,
            "priority": self.priority.value,
            "timestamp": self.timestamp,
            "reply_to": self.reply_to,
            "ttl": self.ttl,
        })

    @classmethod
    def from_json(cls, data: str) -> "AgentMessage":
        d = json.loads(data)
        return cls(
            id=d["id"],
            type=MessageType(d["type"]),
            sender=d["sender"],
            recipient=d["recipient"],
            content=d["content"],
            priority=Priority(d["priority"]),
            timestamp=d["timestamp"],
            reply_to=d.get("reply_to", ""),
            ttl=d.get("ttl", 10),
        )


@dataclass
class Task:
    """Task assigned to an agent."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    task_type: str = ""
    url: str = ""
    selectors: Dict[str, str] = field(default_factory=dict)
    context: Dict[str, Any] = field(default_factory=dict)
    priority: Priority = Priority.NORMAL
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    max_attempts: int = 5
    timeout: int = 300  # seconds

    def to_message(self, recipient: str = "") -> AgentMessage:
        return AgentMessage(
            type=MessageType.TASK,
            recipient=recipient,
            content={
                "task_id": self.id,
                "task_type": self.task_type,
                "url": self.url,
                "selectors": self.selectors,
                "context": self.context,
                "max_attempts": self.max_attempts,
                "timeout": self.timeout,
            },
            priority=self.priority,
        )


@dataclass
class AgentResult:
    """Result from an agent's work."""
    success: bool
    task_id: str
    agent_id: str
    data: List[Dict[str, Any]] = field(default_factory=list)
    error: Optional[str] = None
    skills_learned: List[Dict] = field(default_factory=list)
    techniques_used: List[str] = field(default_factory=list)
    duration_ms: int = 0
    attempts: int = 0

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "task_id": self.task_id,
            "agent_id": self.agent_id,
            "data_count": len(self.data),
            "error": self.error,
            "skills_learned": len(self.skills_learned),
            "techniques_used": self.techniques_used,
            "duration_ms": self.duration_ms,
            "attempts": self.attempts,
        }


class BaseAgent(ABC):
    """
    Base class for all agents.
    Each agent specializes in a specific type of scraping task.
    """

    def __init__(self, agent_id: str, config: Dict[str, Any]):
        self.agent_id = agent_id
        self.config = config
        self.name = self.__class__.__name__
        self.running = False
        self.message_queue: List[AgentMessage] = []
        self.skills_shared: List[str] = []  # IDs of skills shared with others
        self.tasks_completed = 0
        self.tasks_failed = 0
        self.total_data_scraped = 0

    @abstractmethod
    def can_handle(self, task: Task) -> bool:
        """Check if this agent can handle the task."""
        pass

    @abstractmethod
    async def execute_task(self, task: Task) -> AgentResult:
        """Execute the task and return result."""
        pass

    @abstractmethod
    def get_specialization(self) -> str:
        """Return what this agent specializes in."""
        pass

    def handle_message(self, message: AgentMessage) -> Optional[AgentMessage]:
        """Handle incoming message."""
        if message.type == MessageType.TASK:
            return self._handle_task(message)
        elif message.type == MessageType.QUERY:
            return self._handle_query(message)
        elif message.type == MessageType.HELP_REQUEST:
            return self._handle_help_request(message)
        elif message.type == MessageType.SHARE_SKILL:
            return self._handle_skill_share(message)
        return None

    def _handle_task(self, message: AgentMessage) -> Optional[AgentMessage]:
        """Handle task message."""
        content = message.content
        task = Task(
            id=content.get("task_id", ""),
            task_type=content.get("task_type", ""),
            url=content.get("url", ""),
            selectors=content.get("selectors", {}),
            context=content.get("context", {}),
            max_attempts=content.get("max_attempts", 5),
        )

        try:
            result = self.execute_task(task)
            return AgentMessage(
                type=MessageType.RESULT,
                recipient=message.sender,
                reply_to=message.id,
                content={"result": result.to_dict()},
                priority=Priority.HIGH,
            )
        except Exception as e:
            return AgentMessage(
                type=MessageType.ERROR,
                recipient=message.sender,
                reply_to=message.id,
                content={"error": str(e), "task_id": task.id},
            )

    def _handle_query(self, message: AgentMessage) -> AgentMessage:
        """Handle query message."""
        query = message.content.get("query", "")
        response = self._process_query(query)
        return AgentMessage(
            type=MessageType.RESPONSE,
            recipient=message.sender,
            reply_to=message.id,
            content={"query": query, "response": response},
        )

    def _handle_help_request(self, message: AgentMessage) -> Optional[AgentMessage]:
        """Handle request for help."""
        problem = message.content.get("problem", {})
        if self.can_help_with(problem):
            help_data = self.provide_help(problem)
            return AgentMessage(
                type=MessageType.HELP_RESPONSE,
                recipient=message.sender,
                reply_to=message.id,
                content={"help": help_data},
                priority=Priority.HIGH,
            )
        return None

    def _handle_skill_share(self, message: AgentMessage) -> None:
        """Handle incoming skill share."""
        skill = message.content.get("skill", {})
        self._learn_from_others(skill)

    def _process_query(self, query: str) -> str:
        """Process a query about this agent's capabilities."""
        return f"{self.name} specializes in: {self.get_specialization()}"

    def can_help_with(self, problem: Dict[str, Any]) -> bool:
        """Check if this agent can help with a problem."""
        return False

    def provide_help(self, problem: Dict[str, Any]) -> Dict[str, Any]:
        """Provide help with a problem."""
        return {}

    def _learn_from_others(self, skill: Dict[str, Any]) -> None:
        """Learn a skill shared by another agent."""
        logger.info(f"{self.name} learning shared skill: {skill.get('name', 'unknown')}")
        # Implementation in subclass

    def share_skills(self) -> List[Dict[str, Any]]:
        """Share this agent's best skills with others."""
        return []

    def send_message(self, coordinator: "AgentCoordinator", message: AgentMessage) -> None:
        """Send message through coordinator."""
        coordinator.route_message(message)

    def request_help(self, coordinator: "AgentCoordinator", problem: Dict[str, Any]) -> Optional[Dict]:
        """Request help from other agents."""
        message = AgentMessage(
            type=MessageType.HELP_REQUEST,
            content={"problem": problem},
            priority=Priority.HIGH,
        )
        responses = coordinator.broadcast_and_wait(self.agent_id, message, timeout=30)
        if responses:
            return responses[0].content.get("help", {})
        return None

    def share_skill(self, coordinator: "AgentCoordinator", skill: Dict[str, Any]) -> None:
        """Share a learned skill with other agents."""
        message = AgentMessage(
            type=MessageType.SHARE_SKILL,
            content={"skill": skill},
        )
        self.send_message(coordinator, message)

    def get_stats(self) -> Dict[str, Any]:
        """Get agent statistics."""
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "specialization": self.get_specialization(),
            "tasks_completed": self.tasks_completed,
            "tasks_failed": self.tasks_failed,
            "total_data_scraped": self.total_data_scraped,
            "skills_shared": len(self.skills_shared),
        }


class AgentPool:
    """
    Pool of agents for parallel processing.
    """

    def __init__(self):
        self.agents: Dict[str, BaseAgent] = {}
        self.idle_agents: List[str] = []
        self.busy_agents: List[str] = []

    def register(self, agent: BaseAgent) -> None:
        """Register an agent."""
        self.agents[agent.agent_id] = agent
        self.idle_agents.append(agent.agent_id)

    def get_agent(self, task: Task) -> Optional[BaseAgent]:
        """Get best agent for a task."""
        for agent_id in self.idle_agents:
            agent = self.agents.get(agent_id)
            if agent and agent.can_handle(task):
                self.idle_agents.remove(agent_id)
                self.busy_agents.append(agent_id)
                return agent
        return None

    def release_agent(self, agent_id: str) -> None:
        """Release agent back to pool."""
        if agent_id in self.busy_agents:
            self.busy_agents.remove(agent_id)
        if agent_id not in self.idle_agents:
            self.idle_agents.append(agent_id)

    def get_stats(self) -> Dict[str, Any]:
        """Get pool statistics."""
        return {
            "total_agents": len(self.agents),
            "idle_agents": len(self.idle_agents),
            "busy_agents": len(self.busy_agents),
            "agents": [a.get_stats() for a in self.agents.values()],
        }
