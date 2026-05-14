"""
Agent Coordinator - Routes messages and coordinates agents.
"""
import asyncio
import time
from typing import Dict, List, Optional, Any
from collections import defaultdict
from loguru import logger

from .base_agent import BaseAgent, AgentMessage, MessageType, AgentPool, AgentResult, Task, Priority


class AgentCoordinator:
    """
    Coordinates all agents, routes messages, and manages the multi-agent system.
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.pool = AgentPool()
        self.message_log: List[AgentMessage] = []
        self.shared_skills: Dict[str, List[Dict]] = defaultdict(list)
        self.collaboration_cache: Dict[str, Any] = {}

    def register_agent(self, agent: BaseAgent) -> None:
        """Register an agent with the coordinator."""
        self.pool.register(agent)
        logger.info(f"Registered agent: {agent.agent_id} ({agent.name})")

    def route_message(self, message: AgentMessage) -> None:
        """Route a message to its recipient."""
        message.ttl -= 1

        if message.ttl <= 0:
            logger.warning(f"Message {message.id} TTL expired")
            return

        self.message_log.append(message)

        if message.recipient:
            # Direct message
            agent = self.pool.agents.get(message.recipient)
            if agent:
                response = agent.handle_message(message)
                if response:
                    self.route_message(response)
        else:
            # Broadcast
            for agent in self.pool.agents.values():
                if agent.agent_id != message.sender:
                    response = agent.handle_message(message)
                    if response:
                        self.route_message(response)

    def broadcast_and_wait(
        self,
        sender_id: str,
        message: AgentMessage,
        timeout: int = 30,
    ) -> List[AgentMessage]:
        """Broadcast message and wait for responses."""
        message.sender = sender_id
        responses = []
        start_time = time.time()

        # Route to all agents except sender
        message.ttl = 1  # Don't forward further
        for agent in self.pool.agents.values():
            if agent.agent_id != sender_id:
                response = agent.handle_message(message)
                if response:
                    responses.append(response)

        return responses

    def submit_task(self, task: Task) -> Optional[AgentResult]:
        """Submit a task to the best available agent."""
        agent = self.pool.get_agent(task)

        if not agent:
            logger.warning(f"No agent available for task: {task.task_type}")
            return None

        try:
            result = asyncio.run(agent.execute_task(task))
            self.pool.release_agent(agent.agent_id)
            return result
        except Exception as e:
            logger.error(f"Task execution failed: {e}")
            self.pool.release_agent(agent.agent_id)
            return AgentResult(
                success=False,
                task_id=task.id,
                agent_id=agent.agent_id,
                error=str(e),
            )

    def share_best_skills(self) -> None:
        """Collect and share the best skills across all agents."""
        all_skills = []

        for agent in self.pool.agents.values():
            skills = agent.share_skills()
            all_skills.extend(skills)

        # Share with all agents
        for skill in all_skills:
            for agent in self.pool.agents.values():
                agent._learn_from_others(skill)

        logger.info(f"Shared {len(all_skills)} skills across agents")

    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive system statistics."""
        pool_stats = self.pool.get_stats()

        return {
            "pool": pool_stats,
            "message_log_size": len(self.message_log),
            "shared_skills": {k: len(v) for k, v in self.shared_skills.items()},
            "collaboration_cache_size": len(self.collaboration_cache),
        }

    def get_best_agent_for(self, task_type: str) -> Optional[BaseAgent]:
        """Get the best agent for a task type."""
        best_agent = None
        best_score = 0

        for agent in self.pool.agents.values():
            score = self._score_agent_for_task(agent, task_type)
            if score > best_score:
                best_score = score
                best_agent = agent

        return best_agent

    def _score_agent_for_task(self, agent: BaseAgent, task_type: str) -> float:
        """Score how well an agent fits a task."""
        specialization = agent.get_specialization().lower()
        task_type_lower = task_type.lower()

        score = 0.0

        if task_type_lower in specialization or specialization in task_type_lower:
            score += 1.0

        score += agent.tasks_completed / 100  # Experience bonus

        return score

    def create_agent_team(self, task: Task) -> List[BaseAgent]:
        """Create a team of agents to work on a task."""
        team = []

        # Always add generic agent
        for agent in self.pool.agents.values():
            if "generic" in agent.name.lower():
                team.append(agent)
                break

        # Add specialized agents based on task type
        for agent in self.pool.agents.values():
            if agent.can_handle(task):
                team.append(agent)

        return team[:3]  # Max 3 agents per team

    def learn_from_collective(self, result: AgentResult) -> None:
        """Learn from a collective result across agents."""
        if not result.success or not result.skills_learned:
            return

        # Distribute learned skills
        for skill in result.skills_learned:
            for agent in self.pool.agents.values():
                agent._learn_from_others(skill)

        logger.info(f"Distributed {len(result.skills_learned)} skills to all agents")
