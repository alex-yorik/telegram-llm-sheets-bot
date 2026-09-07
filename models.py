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
        """Возвращает True если хотя бы одно поле заполнено."""
        return any(
            [
                self.name,
                self.phone,
                self.service,
                self.date,
                self.time,
            ]
        )
