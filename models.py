"""Pydantic data models."""

from pydantic import BaseModel


class Lead(BaseModel):
    """Lead data extracted from text."""

    name: str | None = None
    phone: str | None = None
    service: str | None = None
    date: str | None = None
    time: str | None = None

    def has_data(self) -> bool:
        """Returns True if at least one field contains non-whitespace data."""
        values = (self.name, self.phone, self.service, self.date, self.time)
        return any(value and value.strip() for value in values)
