"""Agente na C6 (B4b): nó 2 `formular` (pedido do gestor → `SolveSpec` pelo `formulate` real amarrado ao
`FakeLLMClient`, conferida por `rules.spec`), reserva sem modelo (RX-12 em `notices`), cartão estendido no solver, no
verificador e na justificativa, e o laço de no máximo 2 chamadas ao solver (a 2ª sem as preferências suaves).

Roda com o arquivo pequeno do E2 em grade (8 pessoas, 1 loja): o solver leva menos de 1 s por chamada.
"""

from __future__ import annotations

import json
from datetime import date, timedelta

import pytest

from escalista.domain.reading import ConfirmInput
from escalista.domain.spec import SolveSpec
from escalista.rules.spec import default_spec
from tests.agents.test_graph_c6 import FILE_WEEK, GRID, NOW, C6Harness, _read_ok, model_mapping
from tests.fakes import TOOL_JUSTIFY, TOOL_MAPPING, TOOL_SPEC

PERSON = "n-quiteria-horta-sintetico"  # trabalha na quarta no "antes" (08:00 às 15:20)
PERSON_NAME = "Quitéria Horta"
WEDNESDAY = FILE_WEEK + timedelta(days=2)
NOTE = "A Quitéria Horta não pode na quarta, tem consulta médica."
EVIDENCE = "não pode na quarta"
UNAVAILABLE = {"type": "indisponivel", "employee_id": PERSON, "day": WEDNESDAY.isoformat(), "evidence": EVIDENCE}


def spec_args(*constraints: dict, **weights: int) -> dict:
    return {"constraints": list(constraints), **weights}


def confirm_with(h: C6Harness, note: str = NOTE, **kwargs):
    read = _read_ok(h, GRID)
    return read, h.agent.confirm(read.run_id, ConfirmInput(note=note, **kwargs))


def trace_text(h: C6Harness, run_id: str) -> str:
    return json.dumps([e.model_dump(mode="json") for e in h.events(run_id)], ensure_ascii=False)


def solver_runs(h: C6Harness, run_id: str) -> list[dict]:
    return [e.payload for e in h.events(run_id) if e.kind == "solver.run"]


# --- (a) sem pedido ------------------------------------------------------------------------------------------------


def test_without_a_request_the_model_is_not_called_and_the_default_spec_is_used() -> None:
    h = C6Harness(mappings=[model_mapping(GRID)])
    read = _read_ok(h, GRID)

    state = h.agent.confirm(read.run_id)

    assert state.phase == "awaiting_approval", state.exception
    assert state.spec == default_spec() and state.attempts == 1
    assert [c["tool_name"] for c in h.llm.calls] == [TOOL_MAPPING, TOOL_JUSTIFY]  # nenhuma chamada de formulação
    formulate = h.event(read.run_id, "llm.formulate")
    assert formulate.cost_usd == 0 and formulate.payload["cost_basis"] == "sem entrada para o modelo"
    assert formulate.payload["used_model"] is False
    validated = h.event(read.run_id, "spec.validate").payload
    assert validated["fallback"] is True and validated["accepted"] == {} and validated["rejected"] == []
    assert not any(n.code == "RX-12" for n in state.notices)


def test_without_formulate_wired_the_request_is_ignored_silently() -> None:
    """O wiring de hoje (C3) não liga a formulação: especificação padrão, sem aviso e sem chamar o modelo."""
    h = C6Harness(mappings=[model_mapping(GRID)], with_formulate=False)

    read, state = confirm_with(h)

    assert state.phase == "awaiting_approval", state.exception
    assert state.spec == default_spec() and not any(n.code == "RX-12" for n in state.notices)
    assert TOOL_SPEC not in [c["tool_name"] for c in h.llm.calls]
    assert h.event(read.run_id, "llm.formulate").payload["cost_basis"] == "modelo de formulação não configurado"


# --- (b) pedido respeitado --------------------------------------------------------------------------------------------


def test_unavailability_request_is_obeyed_verified_and_citable() -> None:
    h = C6Harness(mappings=[model_mapping(GRID)], specs=[spec_args(UNAVAILABLE)])
    read = _read_ok(h, GRID)
    assert any(s.employee_id == PERSON and s.start.date() == WEDNESDAY for s in read.before.shifts)

    state = h.agent.confirm(read.run_id, ConfirmInput(note=NOTE))

    assert state.phase == "awaiting_approval", state.exception
    [constraint] = state.spec.constraints
    assert constraint.type == "indisponivel" and constraint.employee_id == PERSON and constraint.day == WEDNESDAY
    schedule = h.agent.get_schedule(read.run_id)
    assert schedule.shifts and not any(
        s.employee_id == PERSON and s.start.date() <= WEDNESDAY <= s.end.date() for s in schedule.shifts
    )
    assert state.report.total == 0
    checks = {e.payload["target"]: e.payload for e in h.events(read.run_id) if e.kind == "verifier.check"}
    assert {"id": "exec-indisp-1", "status": "pedido"} in checks["otimizada"]["rules"]  # o verificador confere o pedido
    assert all(r["id"] != "exec-indisp-1" for r in checks["enviada"]["rules"])  # o "antes" responde só ao cartão
    [run] = solver_runs(h, read.run_id)
    assert run["execution_rules"] == ["exec-indisp-1"] and run["attempt"] == 1 and run["relaxed"] == []
    # a justificativa recebe o cartão estendido: a regra do pedido é citável
    justify_call = next(c for c in h.llm.calls if c["tool_name"] == TOOL_JUSTIFY)
    assert "exec-indisp-1" in json.dumps(justify_call["tool_schema"], ensure_ascii=False) + "".join(
        m.content for m in justify_call["messages"]
    )
    validated = h.event(read.run_id, "spec.validate").payload
    assert validated["used_model"] is True and validated["accepted"] == {"indisponivel": 1}
    trace = trace_text(h, read.run_id)
    assert NOTE not in trace and PERSON_NAME not in trace and EVIDENCE not in trace


# --- (c) item que afrouxa o cartão ---------------------------------------------------------------------------------


def test_weekly_hours_above_the_card_are_rejected_and_the_rest_goes_on() -> None:
    loosen = {"type": "max_horas_semana", "employee_id": PERSON, "hours": 50, "evidence": "pode fazer 50 horas"}
    note = f"{NOTE} Ela pode fazer 50 horas nesta semana."
    h = C6Harness(mappings=[model_mapping(GRID)], specs=[spec_args(UNAVAILABLE, loosen)])

    read, state = confirm_with(h, note=note)

    assert state.phase == "awaiting_approval", state.exception
    assert [c.type for c in state.spec.constraints] == ["indisponivel"]
    validated = h.event(read.run_id, "spec.validate").payload
    assert validated["accepted"] == {"indisponivel": 1}
    [rejected] = validated["rejected"]
    assert rejected["type"] == "máximo de horas na semana"
    assert "não pode afrouxar a lei/convenção" in rejected["reason"]
    assert PERSON not in json.dumps(validated)  # o id deriva do nome: fica fora do rastro
    [shown] = [a for a in state.summary.assumptions if a.startswith("Pedido não aplicado")]
    assert PERSON_NAME in shown and "não pode afrouxar" in shown  # o gestor vê o motivo, com o nome
    assert solver_runs(h, read.run_id)[0]["execution_rules"] == ["exec-indisp-1"]  # sem exec-maxh
    assert state.report.total == 0


def test_spec_with_a_card_field_is_refused_by_the_schema_and_falls_back() -> None:
    """Invariante 4: `{"jornada_semanal_max": 48}` não existe na `SolveSpec` (`extra="forbid"`): 3 recusas → padrão."""
    h = C6Harness(mappings=[model_mapping(GRID)], specs=[{"jornada_semanal_max": 48, "constraints": []}] * 3)

    _, state = confirm_with(h, note="Pode usar 48 horas por semana.")

    assert state.phase == "awaiting_approval", state.exception
    assert state.spec == default_spec()
    assert [c["tool_name"] for c in h.llm.calls].count(TOOL_SPEC) == 3
    assert any(n.code == "RX-12" and "otimizei sem ele" in n.title for n in state.notices)


# --- (d) modelo falhando -------------------------------------------------------------------------------------------


def test_model_failure_uses_the_default_spec_with_an_rx12_notice() -> None:
    long_note = NOTE + " " + "x" * 400
    h = C6Harness(mappings=[model_mapping(GRID)], fail_spec=True)

    read, state = confirm_with(h, note=long_note)

    assert state.phase == "awaiting_approval", state.exception
    assert state.spec == default_spec() and state.report.total == 0
    [notice] = [n for n in state.notices if n.code == "RX-12"]
    assert notice.title == "Não consegui interpretar seu pedido; otimizei sem ele"
    [echo] = notice.evidence
    assert echo.startswith("Seu pedido: A Quitéria Horta") and len(echo) == len("Seu pedido: ") + 200
    assert notice.trace_id == next(e.id for e in h.events(read.run_id) if e.kind == "exception.raised")
    validated = h.event(read.run_id, "spec.validate").payload
    assert validated["fallback"] is True and validated["failure"].startswith("o modelo falhou")
    trace = trace_text(h, read.run_id)
    assert NOTE not in trace and PERSON_NAME not in trace
    h.publish(state)  # o aviso não bloqueia


# --- (e) laço do solver ---------------------------------------------------------------------------------------------


def test_preferences_that_hurt_coverage_trigger_a_second_attempt_without_them() -> None:
    """Pesos extremos (preferência 50, falta 10) e todos preferindo a manhã: a 1ª tentativa deixa mais demanda
    descoberta para atender a preferência (medido: 136 contra 116 pessoa-faixas, 5 de 8 preferências); a 2ª, sem as
    preferências, cobre mais de 5% melhor e fica."""
    people = [
        "n-quiteria-horta-sintetico", "n-carla-siqueira-sintetico", "n-ana-nogueira-sintetico",
        "n-silvia-vasconcelos-sintetico", "n-hugo-almeida-sintetico", "n-gabriela-freitas-sintetico",
        "n-fabio-pacheco-sintetico", "n-diego-monteiro-sintetico",
    ]  # fmt: skip
    morning = [{"type": "janela_preferida", "employee_id": p, "window": "manha", "evidence": "preferem a manhã"}
               for p in people]  # fmt: skip
    spec = spec_args(*morning, shortfall_weight=10, preference_weight=50)
    h = C6Harness(mappings=[model_mapping(GRID)], specs=[spec])

    read, state = confirm_with(h, note="Todos preferem a manhã nesta semana.")

    assert state.phase == "awaiting_approval", state.exception
    assert state.attempts == 2
    first, second = solver_runs(h, read.run_id)
    assert (first["attempt"], first["relaxed"]) == (1, [])
    assert (second["attempt"], second["relaxed"]) == (2, ["janela_preferida"])
    assert first["preferences_total"] == 8 and second["preferences_total"] == 0
    assert first["spec"]["constraints"] == {"janela_preferida": 8} and second["spec"]["constraints"] == {}
    assert first["missing_person_slots"] * 100 > second["missing_person_slots"] * 105  # mais de 5% acima
    relax = h.event(read.run_id, "spec.relax").payload
    assert relax["reason"] == "cobertura" and relax["removed"] == ["janela_preferida"]
    assert relax["chosen_attempt"] == 2
    assert state.spec.constraints == [] and state.spec.preference_weight == 50  # a spec aplicada: sem preferências
    assert h.agent.get_schedule(read.run_id) is not None and state.report.total == 0
    kinds = h.kinds(read.run_id)
    assert kinds.index("solver.run") < kinds.index("spec.relax") < kinds.index("verifier.check")


def test_hard_requests_alone_never_trigger_the_second_attempt() -> None:
    """Sem preferência suave não há o que relaxar: 1 chamada ao solver, mesmo com demanda descoberta."""
    h = C6Harness(mappings=[model_mapping(GRID)], specs=[spec_args(UNAVAILABLE)])

    read, state = confirm_with(h)

    assert state.attempts == 1 and len(solver_runs(h, read.run_id)) == 1
    assert solver_runs(h, read.run_id)[0]["missing_person_slots"] > 0  # a grade do E2 já descobre faixas a 100%
    assert "spec.relax" not in h.kinds(read.run_id)


def test_harmless_preference_keeps_the_first_attempt() -> None:
    """Folga preferida com os pesos padrão: a falta é a mesma nas duas tentativas (dentro de 5%) e fica a 1ª."""
    day_off = {"type": "folga_preferida", "employee_id": PERSON, "day": WEDNESDAY.isoformat(),
               "evidence": "prefere folgar na quarta"}  # fmt: skip
    h = C6Harness(mappings=[model_mapping(GRID)], specs=[spec_args(day_off)])

    read, state = confirm_with(h, note="A Quitéria prefere folgar na quarta.")

    assert state.attempts == 2  # houve falta na 1ª: a 2ª roda para comparar
    first, second = solver_runs(h, read.run_id)
    assert first["preferences_total"] == 1 and first["preferences_met"] == 1
    relax = h.event(read.run_id, "spec.relax").payload
    assert relax["chosen_attempt"] == 1
    assert first["missing_person_slots"] * 100 <= second["missing_person_slots"] * 105
    assert [c.type for c in state.spec.constraints] == ["folga_preferida"]


# --- (f) continuidade -----------------------------------------------------------------------------------------------


@pytest.mark.parametrize("with_request", [False, True], ids=["sem-pedido", "pedido-sem-peso"])
def test_next_week_values_stability_and_hints_the_shifted_schedule(with_request: bool) -> None:
    specs = [spec_args(UNAVAILABLE | {"day": (WEDNESDAY + timedelta(weeks=1)).isoformat()})] if with_request else []
    h = C6Harness(mappings=[model_mapping(GRID)], specs=specs)
    h.publish(h.agent.confirm(_read_ok(h, GRID).run_id))
    h.clock.set(NOW + timedelta(days=7))
    nxt = h.agent.start_next_week()
    week = FILE_WEEK + timedelta(weeks=1)

    state = h.agent.confirm(nxt.run_id, ConfirmInput(note=NOTE if with_request else ""))

    assert state.phase == "awaiting_approval", state.exception
    assert state.spec.stability_weight == 10  # o modelo não falou de peso: vale o da continuidade
    if with_request:
        assert [c.type for c in state.spec.constraints] == ["indisponivel"]
    else:
        assert state.spec == default_spec(continuity=True)
    [run] = solver_runs(h, nxt.run_id)
    assert run["spec"]["stability_weight"] == 10 and run["hint_shifts"] == len(nxt.before.shifts) > 0
    assert run["week_start"] == week.isoformat()
    assert all(week <= s.start.date() < week + timedelta(days=7) for s in nxt.before.shifts)  # hint já deslocado
    assert state.report.total == 0


def test_explicit_stability_weight_from_the_model_is_kept_in_next_week() -> None:
    h = C6Harness(mappings=[model_mapping(GRID)], specs=[spec_args(stability_weight=30)])
    h.publish(h.agent.confirm(_read_ok(h, GRID).run_id))
    h.clock.set(NOW + timedelta(days=7))
    nxt = h.agent.start_next_week()

    state = h.agent.confirm(nxt.run_id, ConfirmInput(note="Mexa o mínimo possível na escala."))

    assert state.spec == SolveSpec(stability_weight=30)
    assert date.fromisoformat(solver_runs(h, nxt.run_id)[0]["week_start"]) == FILE_WEEK + timedelta(weeks=1)
