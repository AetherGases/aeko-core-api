"""Run one memory-generation pass over recently active sessions.

This is the only worker module that imports the SDK. Configuration is captured
after loading the environment; the worker connects to MongoDB and Redis,
configures the SDK, registers metric sinks, and exits after one pass.
"""

import os

from dotenv import load_dotenv
from pymongo import MongoClient
from redis import Redis

from aeko import Aeko, AekoMessage, AekoMessenger, AekoUser
from aeko_metrics.database.repository import Repository as AekoMetricsRepository
from aeko_metrics.entity import AgentMetric, Metric as AekoMetric
from aeko_metrics.service import Service as AekoMetricsService
from cmd.memory_generator_worker.constants import (
    CONVERSATION_MEMORY_FIELD,
    REDIS_SCAN_COUNT,
    SESSION_INACTIVITY_MINUTES,
)
from internal.shared import Module, operation, set_aeko_metrics_sink
from internal.shared.event_tracking import (
    current_metric_id_external_company,
    current_metric_id_external_user,
)
from session.cache.repository import Repository as CacheRepository
from session.database.repository import Repository as SessionRepository
from session.memory_service import Service as MemoryService
from user.database.repository import Repository as UserRepository
from user.service import Service as UserService

load_dotenv()


def _int_or_none(value: str | None) -> int | None:
    return int(value) if value else None


def _float_or_none(value: str | None) -> float | None:
    return float(value) if value else None


def build_aeko_metrics_sink(database):
    """Build a callback that stores SDK run metrics and agent invocations in call order."""

    service = AekoMetricsService(AekoMetricsRepository(database))

    def sink(metrics) -> None:
        """Persist the supplied tracking data through the configured metric service."""
        service.add_metric(
            AekoMetric(
                id_request=metrics.id_request,
                latency=metrics.latency,
                error_description=metrics.error_description,
                flow=metrics.flow,
                used_agents=[
                    AgentMetric(
                        name=agent.name,
                        input_tokens=agent.input_tokens,
                        output_tokens=agent.output_tokens,
                        llm=agent.llm,
                        used_tools=list(agent.used_tools),
                    )
                    for agent in metrics.used_agents
                ],
                id_external_user=current_metric_id_external_user(),
                id_external_company=current_metric_id_external_company(),
            )
        )

    return sink


def build_summary_generator() -> AekoMessenger:
    """Create a messenger used only for conversation summarization."""
    return AekoMessenger(AekoUser(id="", id_external_user=0, role="", usecase=""), [])


def _domain_messages_to_aeko(messages):
    """Convert domain messages to the SDK message representation."""
    return [
        AekoMessage(
            input=message.input,
            output=message.output,
            submitted_at=message.submitted_at,
        )
        for message in messages
    ]


class _SummaryGenerator:
    """Adapt domain messages before delegating to the SDK summarizer."""

    def __init__(self, messenger: AekoMessenger):
        self.messenger = messenger

    def generate_summary(self, messages, *, id_request: str):
        """Summarize the supplied domain messages through the SDK."""
        return self.messenger.generate_summary(
            _domain_messages_to_aeko(messages),
            id_request=id_request,
        )


def main() -> None:
    """Connect to dependencies, run one memory-generation pass, and release resources."""
    mongo_client = MongoClient(os.getenv("MONGO_URI"))
    db = mongo_client[os.getenv("DB_NAME")]
    redis_client = Redis.from_url(os.getenv("REDIS_URI"))

    set_aeko_metrics_sink(build_aeko_metrics_sink(db))

    Aeko.config(
        os.getenv("GEMINI_API_KEY"),
        fast_model=os.getenv("AEKO_FAST_MODEL"),
        slow_model=os.getenv("AEKO_SLOW_MODEL"),
        max_tokens=_int_or_none(os.getenv("AEKO_MAX_TOKENS")),
        report_max_tokens=_int_or_none(os.getenv("AEKO_REPORT_MAX_TOKENS")),
        temperature=_float_or_none(os.getenv("AEKO_TEMPERATURE")),
        top_p=_float_or_none(os.getenv("AEKO_TOP_P")),
        top_k=_int_or_none(os.getenv("AEKO_TOP_K")),
    )

    try:
        with operation(Module.DATABASE, "mongo.ping"):
            db.command("ping")
    except Exception as exc:
        raise RuntimeError(f"Failed to connect to MongoDB: {exc}") from exc

    try:
        with operation(Module.DATABASE, "redis.ping"):
            redis_client.ping()
    except Exception as exc:
        raise RuntimeError(f"Failed to connect to Redis: {exc}") from exc

    service = MemoryService(
        SessionRepository(db),
        CacheRepository(redis_client, scan_count=REDIS_SCAN_COUNT),
        UserService(UserRepository(db)),
        _SummaryGenerator(build_summary_generator()),
        inactivity_minutes=SESSION_INACTIVITY_MINUTES,
        memory_field=CONVERSATION_MEMORY_FIELD,
    )

    try:
        service.run()
    finally:
        set_aeko_metrics_sink(None)
        redis_client.close()
        mongo_client.close()


if __name__ == "__main__":
    main()
