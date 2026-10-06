"""Define agent-to-agent service contracts."""

from abc import ABC, abstractmethod

from cmd.api.integrations.a2a.entity import A2AMessage


class IService(ABC):
    @abstractmethod
    def send(
        self,
        message: A2AMessage,
        aeko_messenger_factory,
        aeko_session_factory,
    ) -> str:
        """Deliver an agent message and return the approved reply text."""
        pass
