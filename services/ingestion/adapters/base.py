"""
Base adapter class.
All source adapters extend this class.
"""


class BaseAdapter:
    """Base class for all source adapters."""

    def __init__(self, source_type: str, source_name: str):
        self.source_type = source_type
        self.source_name = source_name

    async def fetch(self) -> list[dict]:
        """Fetch raw data from the source."""
        raise NotImplementedError

    def transform(self, raw_data: list[dict]) -> list[dict]:
        """Transform raw data into Canonical Weather Events."""
        raise NotImplementedError
