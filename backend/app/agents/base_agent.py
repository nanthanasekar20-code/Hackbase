from abc import ABC, abstractmethod


class BaseAgent(ABC):
    """Common interface for all HackBase agents."""

    name: str = "base_agent"

    @abstractmethod
    def run(self, *args, **kwargs):
        raise NotImplementedError
