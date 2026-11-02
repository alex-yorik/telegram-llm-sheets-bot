"""Pydantic-модели данных."""

from pydantic import BaseModel


class Lead(BaseModel):
    """Извлечённые из текста данные заявки."""

    name: str | None = None
    phone: str | None = None
    service: str | None = None
    date: str | None = None
    time: str | None = None

    def has_data(self) -> bool:
        """Возвращает True если хотя бы одно поле содержит непробельные данные."""
        values = (self.name, self.phone, self.service, self.date, self.time)
        return any(value and value.strip() for value in values)
