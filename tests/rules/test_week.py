"""Semana de referência e vigência por semana (plano da C6, A3; seção 8)."""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

import pytest

from escalista.domain.schedule import Schedule, Shift
from escalista.rules.loader import load_rule_card, load_rule_card_for_week
from escalista.rules.week import monday_of, next_week_start, shift_schedule

DATA = Path(__file__).resolve().parents[2] / "data" / "regras"


def _value(card, kind: str, key: str):
    return next(r.params[key] for r in card.rules if r.kind == kind)


# --- datas ---------------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("day", "monday"),
    [
        (date(2027, 1, 11), date(2027, 1, 11)),  # segunda
        (date(2027, 1, 13), date(2027, 1, 11)),  # quarta
        (date(2027, 1, 17), date(2027, 1, 11)),  # domingo
        (date(2027, 1, 18), date(2027, 1, 18)),
        (date(2027, 1, 1), date(2026, 12, 28)),  # vira o ano
    ],
)
def test_monday_of(day, monday):
    assert monday_of(day) == monday


def test_next_week_start():
    assert next_week_start(date(2027, 1, 11)) == date(2027, 1, 18)
    assert next_week_start(date(2026, 12, 28)) == date(2027, 1, 4)


# --- deslocamento ---------------------------------------------------------------------------------------------


def _schedule() -> Schedule:
    return Schedule(
        week_start=date(2026, 11, 9),
        shifts=[
            Shift(employee_id="P1", store_id="L1", start=datetime(2026, 11, 9, 8), end=datetime(2026, 11, 9, 16)),
            Shift(employee_id="P2", store_id="L1", start=datetime(2026, 11, 15, 22), end=datetime(2026, 11, 16, 2)),
        ],
    )


def test_shift_schedule_moves_week_and_shifts_in_whole_weeks():
    before = _schedule()
    after = shift_schedule(before, 9)  # 09/11/2026 (44h) → 11/01/2027 (42h)
    assert after.week_start == date(2027, 1, 11)
    assert [(s.start, s.end) for s in after.shifts] == [
        (datetime(2027, 1, 11, 8), datetime(2027, 1, 11, 16)),
        (datetime(2027, 1, 17, 22), datetime(2027, 1, 18, 2)),  # mesmo dia da semana, vira a noite igual
    ]
    assert [(s.employee_id, s.store_id) for s in after.shifts] == [("P1", "L1"), ("P2", "L1")]
    assert all(s.start.weekday() == b.start.weekday() for s, b in zip(after.shifts, before.shifts, strict=True))


def test_shift_schedule_is_pure_and_reversible():
    before = _schedule()
    snapshot = before.model_dump()
    assert shift_schedule(shift_schedule(before, 3), -3) == before
    assert shift_schedule(before, 0) == before
    assert before.model_dump() == snapshot


# --- cartão por semana ----------------------------------------------------------------------------------------


def test_week_with_the_42h_change_applies_42h_on_the_whole_week_with_warning():
    card = load_rule_card_for_week(DATA, date(2026, 12, 14))  # 44h até terça 15, 42h de quarta 16
    assert card.reference_date == date(2026, 12, 14)
    assert _value(card, "jornada_semanal_max", "hours") == 42
    assert "jornada_semanal_max" in card.provisional
    # o repouso de 2 dias também começa na quarta 16: vale a semana toda, provisório
    assert _value(card, "repouso_semanal", "days") == 2
    assert "repouso_semanal" in card.provisional
    assert len([r for r in card.rules if r.kind == "jornada_semanal_max"]) == 1


def test_week_before_the_change_keeps_44h():
    card = load_rule_card_for_week(DATA, date(2026, 12, 7))
    assert _value(card, "jornada_semanal_max", "hours") == 44
    assert "jornada_semanal_max" not in card.provisional
    assert card == load_rule_card(DATA, date(2026, 12, 7))


def test_week_after_the_change_is_the_card_of_today():
    card = load_rule_card_for_week(DATA, date(2027, 1, 11))
    assert _value(card, "jornada_semanal_max", "hours") == 42
    assert "jornada_semanal_max" not in card.provisional
    assert card == load_rule_card(DATA, date(2027, 1, 11))  # E1 e C5 não mudam


def test_week_with_the_40h_change_from_thursday():
    card = load_rule_card_for_week(DATA, date(2027, 12, 13))  # 40h vale de quinta 16/12/2027
    assert _value(card, "jornada_semanal_max", "hours") == 40
    assert "jornada_semanal_max" in card.provisional


LEI_FIXTURE = """
regras:
  - id: jornada_semanal_max
    valores:
      - {ate: 2026-12-15, horas: 44}
      - {de: 2026-12-16, horas: 42}
    fonte: "art. 6º"
    status: interpretacao
  - id: jornada_diaria_max
    horas: 8
    fonte: "art. 7º, XIII CF"
    status: interpretacao
"""
POLITICA_FIXTURE = """
regras:
  - id: pol_semanal
    restringe: jornada_semanal_max
    horas: 43
    fonte: "política fictícia"
    status: ficticia
"""


def _fixture_dir(tmp_path: Path) -> Path:
    (tmp_path / "lei").mkdir()
    (tmp_path / "politica").mkdir()
    (tmp_path / "lei" / "lei.yaml").write_text(LEI_FIXTURE, encoding="utf-8")
    (tmp_path / "politica" / "pol.yaml").write_text(POLITICA_FIXTURE, encoding="utf-8")
    return tmp_path


def test_week_card_takes_the_strictest_per_primitive_and_keeps_conflicts_of_any_day(tmp_path):
    base = _fixture_dir(tmp_path)
    # seg e ter: lei 44, política 43 → 43 (sem conflito); de qua: lei 42, política 43 é mais frouxa → RX-01
    assert _value(load_rule_card(base, date(2026, 12, 14)), "jornada_semanal_max", "hours") == 43
    assert load_rule_card(base, date(2026, 12, 14)).exceptions == []
    card = load_rule_card_for_week(base, date(2026, 12, 14))
    weekly = [r for r in card.rules if r.kind == "jornada_semanal_max"]
    assert [(r.id, r.params["hours"]) for r in weekly] == [("jornada_semanal_max", 42)]
    assert card.provisional == ["jornada_semanal_max"]
    assert [e.code for e in card.exceptions] == ["RX-01"]
    assert _value(card, "jornada_diaria_max", "hours") == 8  # não mudou na semana: nada provisório


def test_week_card_rejects_non_monday():
    with pytest.raises(ValueError, match="segunda"):
        load_rule_card_for_week(DATA, date(2026, 12, 15))
