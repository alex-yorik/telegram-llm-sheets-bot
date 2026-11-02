"""Тесты модели Lead."""

from models import Lead


def test_valid_lead():
    """Валидная заявка со всеми полями."""
    lead = Lead(
        name="John Smith",
        phone="+1 555 123 4567",
        service="English lesson",
        date="next Tuesday",
        time="17:00",
    )
    assert lead.name == "John Smith"
    assert lead.has_data() is True


def test_lead_all_none():
    """Заявка без данных."""
    lead = Lead()
    assert lead.has_data() is False


def test_lead_empty_strings():
    """Пустые строки не считаются данными."""
    lead = Lead(name="", phone="", service="")
    assert lead.has_data() is False


def test_lead_whitespace_only():
    """Строки из пробелов не считаются данными."""
    lead = Lead(name="   ", phone="\t")
    assert lead.has_data() is False


def test_lead_extra_fields_ignored():
    """Лишние поля игнорируются Pydantic."""
    lead = Lead(name="John", extra_field="should be ignored")
    assert lead.name == "John"
    assert not hasattr(lead, "extra_field")


def test_lead_partial_data():
    """Достаточно одного заполненного поля."""
    lead = Lead(name="John", phone="+1234567890")
    assert lead.has_data() is True
    assert lead.service is None
    assert lead.date is None
