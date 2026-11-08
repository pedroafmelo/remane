"""Evals E3: acompanhamento (plano dos evals E3/E4, seções 6 e 7; contrato acompanhamento ⇄ evals, SAIDA-AC-NN).

Cada cenário declara suíte, modelo, tier da C7 e as saídas de que depende (matriz da seção 11). Enquanto a saída não
existir no código, o runner diz `não executado (falta SAIDA-AC-NN (...))` sem rodar. Montagem e gabaritos em
`evals/tracking.py`: SQLite em memória, `StepClock`, `ScriptedLLM` por nome de ferramenta, instantes e ordens
**literais** do gabarito da C7 e números da política pelo `TrackPolicy` (nunca `detect`, `find_cover` nem `judge`
para o esperado).

Com modelo (E3-21, 23, 24, 27): passa se `verdict` e `reasons` batem com o gabarito e nenhum CID vazou (DEC-071); o
acerto por campo vai em `metrics["rn04.atestado"]`. Modelo indisponível (RX-12) → `não executado (modelo indisponível)`.
O `Outcome.model` sai dos eventos `track.llm.read_atestado`; um falso (`model="fake"`) nunca conta como executado.
E3-22 aparece uma vez, no modo T1b (sem modelo, PDF só imagem); o modo T2 (visão) fica para depois.
"""

from __future__ import annotations

import io
import uuid
from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Any

from escalista.evals import tracking as tk
from escalista.evals.common import EvalContext, MemorySink, NotRun, Outcome, Requirement, Scenario, model_use
from escalista.evals.fakes import ScriptedLLM

SUITE = "e3"
NOT_WRITTEN = "cenário ainda não escrito (tarefa E3/E4/E5)"
MODEL_DOWN = "modelo indisponível"

BUILD_TRACKER = Requirement("escalista.api.tracker_wiring", "build_tracker", "SAIDA-AC-02")
READ_ATESTADO = Requirement("escalista.ingest.atestado", "read_atestado", "SAIDA-AC-05")
FIND_LEAKS = Requirement("escalista.audit.protected", "find_leaks", "SAIDA-AC-13")
TRACK_POLICY = Requirement("escalista.rules.tracking_policy", "load_track_policy", "SAIDA-AC-06")
APPLY_COVER = Requirement("escalista.agents.tracker.tools", "aplicar_cobertura", "SAIDA-AC-16")

SWEEP_T1 = {"no_punch"}


def _pending(_: EvalContext) -> Outcome:
    raise NotRun(NOT_WRITTEN)


def _need(obj: Any, attr: str, saida: str) -> Any:
    """Método do contrato que o `Tracker` ainda não tem: a saída não existe, o cenário não afirma nada."""
    found = getattr(obj, attr, None)
    if found is None:
        raise NotRun(f"falta {saida} (Tracker.{attr})")
    return found


def _report(rig: tk.Rig, c: dict[str, Any], **kw: Any) -> Any:
    return rig.tracker.report(employee_id=c["employee_id"], day=tk.case_day(c), kind=c["kind"], **kw)


def _kinds(events: list[Any], kind: str) -> list[Any]:
    return [e for e in events if e.kind == kind]


# --- E3-01, 02, 09: varredor ----------------------------------------------------------------------------------------


def _e3_01(ctx: EvalContext) -> Outcome:
    gab = tk.scenario_expected(ctx)
    planted = sorted(tk.punch_cases(gab, SWEEP_T1), key=lambda c: tk.as_dt(c["fires_at"]))
    if not planted:
        raise NotRun(f"falta {tk.SAIDA_15} (desvio do ponto com gatilho no_punch)")
    rig = tk.build(ctx)
    instants = sorted({tk.as_dt(c[k]) for c in planted for k in ("not_before", "fires_at")})
    emitted: list[tuple[str, str | None, datetime]] = []
    duplicates = 0
    for moment in instants:
        first = [t for t in rig.at(moment).triggers if t.kind in SWEEP_T1]
        again = [t for t in rig.tracker.run_sweep(moment).triggers if t.kind in SWEEP_T1]
        duplicates += len(again)
        emitted += [(t.kind, t.employee_id, moment) for t in first]
    want = {(c["trigger"], c["employee_id"]): tk.as_dt(c["fires_at"]) for c in planted}
    got = {(k, e): at for k, e, at in emitted}
    lost = sorted(f"{k}/{e}" for k, e in want if (k, e) not in got)
    invented = sorted(f"{k}/{e}" for k, e in got if (k, e) not in want)
    off_time = sorted(f"{k}/{e}" for (k, e), at in got.items() if (k, e) in want and at != want[(k, e)])
    repeated = len(emitted) - len(got)
    ok = not lost and not invented and not off_time and duplicates == 0 and repeated == 0
    return Outcome(
        f"{len(want)} gatilho(s) plantado(s), cada um no instante do gabarito; 0 perdidos, 0 inventados, 0 repetidos",
        f"{len(got)} emitido(s); perdidos {lost or 0}; inventados {invented or 0}; fora do instante {off_time or 0}; "
        f"repetidos na 2ª chamada {duplicates}; repetidos entre instantes {repeated}",
        ok,
    )


def _e3_02(ctx: EvalContext) -> Outcome:
    gab = tk.scenario_expected(ctx)
    policy = tk.track_policy(ctx)
    c = next((x for x in tk.punch_cases(gab, SWEEP_T1) if x.get("kind") == "falta"), None)
    if c is None:
        raise NotRun(f"falta {tk.SAIDA_15} (falta plantada no ponto)")
    start = tk.as_dt(c["shift_start"])
    tol = policy.late_tolerance_min
    before, at = start + timedelta(minutes=tol - 1), start + timedelta(minutes=tol)
    rig = tk.build(ctx)

    def mine(result: Any) -> list[Any]:
        return [t for t in result.triggers if t.kind == "no_punch" and t.employee_id == c["employee_id"]]

    early, fired = mine(rig.at(before)), mine(rig.at(at))
    literal = (tk.as_dt(c["not_before"]), tk.as_dt(c["fires_at"])) == (before, at)
    ok = not early and len(fired) == 1 and fired[0].rule_ref == "pol_atraso" and literal
    return Outcome(
        f"no_punch ausente em início + {tol - 1} min e presente em início + {tol} min (tolerancia_min = {tol}), "
        "rule_ref pol_atraso; gabarito com os mesmos instantes",
        f"em {before:%H:%M}: {len(early)}; em {at:%H:%M}: {len(fired)} "
        f"(rule_ref {fired[0].rule_ref if fired else '-'}); gabarito igual à política: {literal}",
        ok,
    )


def _e3_09(ctx: EvalContext) -> Outcome:
    gab = tk.scenario_expected(ctx)
    policy = tk.track_policy(ctx)
    c = tk.falta_from_punch(gab)
    na = c["no_answer"]
    asked, not_before, fires = (tk.as_dt(na[k]) for k in ("question_at", "not_before", "fires_at"))
    deadline = timedelta(minutes=policy.answer_deadline_min)
    arithmetic = fires == asked + deadline and not_before == fires - timedelta(minutes=1)
    rig = tk.build(ctx)
    rig.at(asked)

    def rx09() -> int:
        n = 0
        for item in rig.open_cards("RX-09"):
            view = rig.tracker.case(item.source.get("case_id"))
            n += view is not None and view.employee_id == c["employee_id"]
        return n

    rig.at(not_before)
    early = rx09()
    rig.at(fires)
    late = rx09()
    return Outcome(
        f"RX-09 ausente em {not_before:%H:%M} e aberto em {fires:%H:%M} (pergunta + "
        f"{policy.answer_deadline_min} min, prazo_resposta_colaborador_min)",
        f"em {not_before:%H:%M}: {early}; em {fires:%H:%M}: {late}; gabarito igual à política: {arithmetic}",
        early == 0 and late == 1 and arithmetic,
    )


# --- E3-04 a 08, 10, 11, 12: oferta, cobertura, prazo, registro, portão, canal -------------------------------------


def _e3_04(ctx: EvalContext) -> Outcome:
    """RF-28 (contrato, seção 4, "Execução C7, 09:47", item 2): `overtime_needed` é verdadeiro quando não há cobertura
    dentro das regras (lojas PL-02 e PL-03 no gabarito) e falso na loja com folga (PL-01). Valores lidos do gabarito."""
    gab = tk.scenario_expected(ctx)
    targets = [c for c in tk.cases(gab) if c.get("origin") != "ponto" and c.get("overtime_needed") is not None]
    if not any(c["overtime_needed"] for c in targets) or all(c["overtime_needed"] for c in targets):
        raise NotRun(f"falta {tk.SAIDA_15} (casos com e sem overtime_needed no gabarito, PEDIDO-EV-18)")
    rig = tk.build(ctx)
    obtained, ok = [], True
    for c in targets:
        view = _report(rig, c)
        searched = _kinds(rig.events(f"track-{view.case_id}"), "track.cover.searched")
        flag = searched[-1].payload.get("overtime_needed") if searched else None
        ok = ok and flag is c["overtime_needed"]
        obtained.append(f"{c['id']}: {flag}")
    want = "; ".join(f"{c['id']}: {c['overtime_needed']}" for c in targets)
    return Outcome(f"track.cover.searched.overtime_needed por caso = gabarito ({want})", "; ".join(obtained), ok)


def _offered(ctx: EvalContext, **build_kw: Any) -> tuple[tk.Rig, dict[str, Any], Any]:
    """O caso com aviso (gabarito: `offers` com instantes literais), avisado no instante inicial do relógio."""
    gab = tk.scenario_expected(ctx)
    c = tk.reported_case(gab)
    rig = tk.build(ctx, **build_kw)
    reported_at = tk.as_dt(c["offers"]["reported_at"])
    if reported_at > rig.clock.now():
        rig.clock.advance(reported_at - rig.clock.now())
    return rig, c, _report(rig, c)


def _e3_05(ctx: EvalContext) -> Outcome:
    rig, c, view = _offered(ctx)
    searched = _kinds(rig.events(f"track-{view.case_id}"), "track.cover.searched")
    ranked = list(searched[-1].payload.get("ranked", [])) if searched else None
    first = view.offers[0] if view.offers else None
    want_deadline = tk.as_dt(c["offers"]["list"][0]["deadline"])
    ok = (
        view.status == "oferta_enviada"
        and ranked == c["ranked"]
        and first is not None
        and (first.candidate_id, first.rank) == (c["first_without_overtime"], 1)
        and first.deadline == want_deadline
        and len(view.offers) == 1
    )
    return Outcome(
        f"status oferta_enviada; ranking {c['ranked']}; 1 oferta, ao 1º sem hora extra "
        f"({c['first_without_overtime']}), prazo {want_deadline:%H:%M}",
        f"status {view.status}; ranking {ranked}; ofertas "
        f"{[(o.candidate_id, o.rank, f'{o.deadline:%H:%M}') for o in view.offers]}",
        ok,
    )


def _accept_and_validate(rig: tk.Rig, view: Any) -> tuple[Any, Any, list[Any]]:
    """Colega aceita a 1ª oferta; o gestor valida o cartão COBERTURA (opção "Validar...", senão a 1ª)."""
    respond = _need(rig.tracker, "respond_offer", "SAIDA-AC-04")
    offer = view.offers[0]
    after_accept = respond(offer_id=offer.offer_id, employee_id=offer.candidate_id, accept=True)
    cards = rig.open_cards("COBERTURA", view.case_id)
    if len(cards) != 1:
        return after_accept, None, cards
    item = cards[0]
    labels = [o.label for o in item.card.options]
    index = next((i for i, label in enumerate(labels) if label.lower().startswith("validar")), 0)
    return after_accept, rig.decide(item, index), cards


def _violation_keys(schedule: Any, card: Any) -> set[tuple[Any, ...]]:
    from escalista.verifier import verify

    return {(v.rule_id, v.employee_id, v.day, v.detail) for v in verify(schedule, card).violations}


def _e3_06(ctx: EvalContext) -> Outcome:
    rig, c, view = _offered(ctx)
    before = rig.published_version()
    after_accept, decided, cards = _accept_and_validate(rig, view)
    after = rig.published_version()
    closed = _kinds(rig.events(f"track-{view.case_id}"), "track.case.closed")
    event_new = closed[-1].payload.get("new_violations") if closed else None
    own_new = None
    if before is not None and after is not None and after.id != before.id:
        own_new = len(_violation_keys(after.schedule, ctx.card) - _violation_keys(before.schedule, ctx.card))
    want = c["new_violations"]
    ok = (
        after_accept.status == "aguardando_gestor"
        and len(cards) == 1
        and decided is not None
        and event_new == want
        and own_new == want
    )
    return Outcome(
        "aceite → aguardando_gestor e 1 cartão COBERTURA; após a validação, versão nova publicada; "
        f"new_violations do evento = {want} e verify do eval = {want}",
        f"após o aceite: {after_accept.status}, {len(cards)} cartão(ões); versão "
        f"{'nova' if own_new is not None else 'inalterada'}; track.case.closed new_violations {event_new}; "
        f"verify do eval {own_new}",
        ok,
    )


def _e3_07(ctx: EvalContext) -> Outcome:
    gab = tk.scenario_expected(ctx)
    targets = tk.rx05_cases(gab)
    want_options = tk.policy_options(ctx, "RX-05")
    rig = tk.build(ctx)
    obtained, ok = [], bool(want_options)
    for c in targets:
        view = _report(rig, c)
        cards = rig.open_cards("RX-05", view.case_id)
        raised = [
            e
            for e in rig.events(f"track-{view.case_id}")
            if e.kind == "exception.raised" and e.payload.get("code") == "RX-05"
        ]
        labels = [o.label for o in cards[0].card.options] if cards else []
        good = len(cards) == 1 and labels == want_options and len(raised) == 1 and not view.offers
        ok = ok and good
        obtained.append(
            f"{c['id']}: {len(cards)} cartão(ões) RX-05, opções da política {labels == want_options}, "
            f"{len(raised)} exception.raised, {len(view.offers)} oferta(s)"
        )
    return Outcome(
        f"cada caso sem substituto ({', '.join(c['id'] for c in targets)}) abre 1 RX-05 com as opções de "
        "excecoes_demo, 1 exception.raised e 0 ofertas",
        "; ".join(obtained),
        ok,
    )


def _e3_08(ctx: EvalContext) -> Outcome:
    policy = tk.track_policy(ctx)
    rig, c, view = _offered(ctx)
    plan = c["offers"]
    offers = plan["list"]
    problems: list[str] = []
    want_n = min(policy.max_candidates, len(c["ranked"]))
    if len(offers) != want_n:
        problems.append(f"gabarito com {len(offers)} ofertas, a política dá {want_n}")
    for o in offers:
        if tk.as_dt(o["deadline"]) - tk.as_dt(o["sent_at"]) != timedelta(minutes=policy.offer_deadline_min):
            problems.append(f"prazo da oferta {o['rank']} difere de prazo_por_candidato_min")
    rx06_at, rx06_before = tk.as_dt(plan["rx06_at"]), tk.as_dt(plan["rx06_not_before"])

    def rx06() -> int:
        return len(rig.open_cards("RX-06", view.case_id))

    for i, o in enumerate(offers):
        rig.at(tk.as_dt(o["offer_expired_not_before"]))
        current = rig.tracker.case(view.case_id)
        if len(current.offers) != i + 1 or current.offers[i].status != "enviada":
            problems.append(f"antes do prazo da oferta {i + 1}: {[(x.candidate_id, x.status) for x in current.offers]}")
        if rx06():
            problems.append(f"RX-06 aberto em {tk.as_dt(o['offer_expired_not_before']):%H:%M}")
        rig.at(tk.as_dt(o["deadline"]))
        current = rig.tracker.case(view.case_id)
        mine = current.offers[i] if len(current.offers) > i else None
        if mine is None or mine.status != "vencida" or mine.candidate_id != o["candidate_id"]:
            problems.append(f"oferta {i + 1} não venceu no prazo ({mine.status if mine else 'ausente'})")
        nxt = offers[i + 1] if i + 1 < len(offers) else None
        sent_next = current.offers[i + 1].candidate_id if len(current.offers) > i + 1 else None
        if nxt is not None and sent_next != nxt["candidate_id"]:
            problems.append(f"oferta {i + 2} não saiu para {nxt['candidate_id']} no prazo")
    if rig.clock.now() < rx06_before:
        rig.at(rx06_before)
        if rx06():
            problems.append(f"RX-06 aberto em {rx06_before:%H:%M}")
    if rig.clock.now() < rx06_at:
        rig.at(rx06_at)
    opened = rx06()
    if opened != 1:
        problems.append(f"{opened} RX-06 em {rx06_at:%H:%M}")
    return Outcome(
        f"{len(offers)} ofertas sequenciais, cada uma vence em {policy.offer_deadline_min} min e passa ao próximo do "
        f"ranking; RX-06 ausente em {rx06_before:%H:%M} e aberto em {rx06_at:%H:%M}",
        "; ".join(problems) or "como esperado",
        not problems,
    )


def _e3_10(ctx: EvalContext) -> Outcome:
    rig, _, view = _offered(ctx)
    _accept_and_validate(rig, view)
    out = [m for m in rig.rows("channel_message") if m.get("direction") == "out"]
    events = rig.events()
    sent = [e for e in events if e.kind == "track.message.sent"]
    by_id = {e.id: e for e in events}
    orphans = 0
    for m in out:
        ref = by_id.get(m.get("decision_ref"))
        case_id = m.get("case_id")
        if ref is None or (case_id is not None and ref.run_id != f"track-{case_id}"):
            orphans += 1
    ok = len(out) == len(sent) and orphans == 0 and len(out) >= 1
    return Outcome(
        "mensagens de saída em channel_message = eventos track.message.sent; cada decision_ref é um trace_event do "
        "mesmo caso (0 órfãos)",
        f"{len(out)} mensagens de saída, {len(sent)} track.message.sent, {orphans} órfã(s)",
        ok,
    )


def _e3_11(ctx: EvalContext) -> Outcome:
    """Portão (SAIDA-AC-16): `aplicar_cobertura` sem aceite, e com aceite mas sem aprovação gravada da versão; e
    `enviar` a quem não está no roteiro do caso. Chamadas diretas às ferramentas, como o modelo faria."""
    from escalista.agents.tracker.tools import aplicar_cobertura, enviar
    from escalista.domain.tracking import ToolRefusedError
    from escalista.store.sql_repository import SqlRepository
    from escalista.store.tracking import SqlTrackRepository

    rig, _, view = _offered(ctx)
    repo, cases, tracer = SqlRepository(rig.engine), SqlTrackRepository(rig.engine), rig.tracer()
    before = rig.published_version()
    draft = before.model_copy(update={"id": f"ver-eval-{uuid.uuid4().hex[:8]}", "status": "draft"})
    repo.save_version(draft)  # versão sem aprovação gravada
    attempts: list[tuple[str, Callable[[], Any]]] = [
        ("sem aceite", lambda: aplicar_cobertura(repo=repo, tracer=tracer, case=cases.get_case(view.case_id),
                                                  version_id=draft.id)),
        ("com aceite, sem aprovação", lambda: aplicar_cobertura(repo=repo, tracer=tracer,
                                                                 case=cases.get_case(view.case_id),
                                                                 version_id=draft.id)),
        ("mensagem fora do roteiro", lambda: enviar(channel=_phone(rig), tracer=tracer,
                                                     case=cases.get_case(view.case_id), to="FORA-DO-ROTEIRO",
                                                     template="eval", body="eval", decision_ref="eval",
                                                     new_id=lambda: uuid.uuid4().hex)),
    ]  # fmt: skip
    refused: list[str] = []
    for name, call in attempts:
        if name.startswith("com aceite"):
            offer = view.offers[0]
            rig.tracker.respond_offer(offer_id=offer.offer_id, employee_id=offer.candidate_id, accept=True)
        try:
            call()
        except ToolRefusedError:
            refused.append(name)
    events = [e for e in rig.events(f"track-{view.case_id}") if e.kind == "track.tool.refused"]
    after = rig.published_version()
    same = before.id == (after.id if after else None)
    stray = [m for m in rig.rows("channel_message") if m.get("party") == "FORA-DO-ROTEIRO"]
    ok = len(refused) == len(attempts) and len(events) == len(attempts) and same and not stray
    return Outcome(
        f"{len(attempts)} chamadas sem o registro exigido ({', '.join(n for n, _ in attempts)}): {len(attempts)} "
        f"ToolRefusedError, {len(attempts)} track.tool.refused, escala publicada inalterada, 0 mensagens fora do "
        "roteiro",
        f"recusadas: {', '.join(refused) or 'nenhuma'}; {len(events)} evento(s); versão publicada "
        f"{'inalterada' if same else 'MUDOU'}; {len(stray)} mensagem(ns) fora do roteiro",
        ok,
    )


def _phone(rig: tk.Rig) -> Any:
    from escalista.channel.simulated import SimulatedPhone

    return SimulatedPhone(rig.engine)


def _e3_12(ctx: EvalContext) -> Outcome:
    rig = tk.build(ctx)
    inbound = _need(rig.tracker, "inbound", "SAIDA-AC-18")
    sender = f"+55 81 9{uuid.uuid4().int % 10**8:08d}"  # fora do quadro, sintético
    try:  # código real: devolve `False`; o contrato fala em `ChannelRejected` (retorno ou exceção)
        result = inbound(sender)
        rejected = result is False or type(result).__name__ == "ChannelRejected"
    except Exception as exc:  # noqa: BLE001
        rejected = type(exc).__name__ == "ChannelRejected"
    cases = rig.rows("track_case")
    events = rig.events()
    rejected_events = [e for e in events if e.kind == "track.channel.rejected"]
    in_clear = any(sender in f"{e.payload} {e.message_ref}" for e in events)
    hashed = len(rejected_events) == 1 and "sender_hash" in rejected_events[0].payload
    ok = rejected and not cases and hashed and not in_clear
    return Outcome(
        "ChannelRejected; 0 casos; 1 track.channel.rejected com sender_hash; o número em claro em nenhum evento",
        f"rejeitado {rejected}; {len(cases)} caso(s); {len(rejected_events)} evento(s), hash {hashed}; "
        f"em claro {in_clear}",
        ok,
    )


# --- E3-13 a 16, 22: falhas, vazamento, atestado sem modelo ---------------------------------------------------------


def _tool_name() -> str:
    from escalista.llm.prompts.atestado import TOOL_NAME

    return TOOL_NAME


def _offered_with(ctx: EvalContext, llm: Any, at: tk.Atestado, text: str | None = None) -> tuple[tk.Rig, Any, Any]:
    """O caso com aviso, com o atestado `at` anexado (o atestado é da mesma pessoa e do mesmo dia, no gabarito)."""
    gab = tk.scenario_expected(ctx)
    c = tk.reported_case(gab)
    if (tk.case_day(c), c["employee_id"]) != (at.expected_day, tk.employee_by_name(ctx, at.employee_name)):
        raise NotRun(f"falta {tk.SAIDA_15} (atestado {at.file} não é do caso com aviso)")
    rig = tk.build(ctx, llm=llm)
    return rig, c, _report(rig, c, text=text, attachment=tk.attachment(at))


def _e3_13(ctx: EvalContext) -> Outcome:
    at = tk.atestado(ctx, "at-01")
    llm = ScriptedLLM(fail_tools={_tool_name()})
    rig, c, view = _offered_with(ctx, llm, at)
    rx12 = rig.open_cards("RX-12", view.case_id)
    first = view.offers[0].candidate_id if view.offers else None
    ok = (
        view.abono == "provisorio"
        and view.reading is None
        and len(rx12) == 1
        and first == c["first_without_overtime"]
        and len(llm.calls) >= 1
    )
    return Outcome(
        "modelo fora na leitura: abono provisório, reading None, 1 RX-12 e a oferta sai ao 1º do ranking",
        f"abono {view.abono}; reading {'None' if view.reading is None else 'presente'}; {len(rx12)} RX-12; "
        f"1ª oferta {first}; chamadas ao modelo {len(llm.calls)}",
        ok,
    )


def _raising(*_: Any, **__: Any) -> Any:
    raise RuntimeError("falha simulada (eval E3-14)")


class _DownPunches:
    def punches(self, *, until: datetime) -> list[Any]:
        from escalista.domain.tracking import PunchUnavailableError

        raise PunchUnavailableError("ponto fora (eval E3-14)")


def _e3_14(ctx: EvalContext) -> Outcome:
    gab = tk.scenario_expected(ctx)
    punch = tk.punch_cases(gab, SWEEP_T1)
    if not punch:
        raise NotRun(f"falta {tk.SAIDA_15} (desvio do ponto)")
    rig, _, view = _offered(ctx, cover_fn=_raising)
    cover_rx12 = len(rig.open_cards("RX-12", view.case_id))
    rig2 = tk.build(ctx, punch_source=_DownPunches())
    result = rig2.at(tk.as_dt(punch[0]["fires_at"]))
    failed = [e for e in rig2.events() if e.kind == "track.sweep.failed"]
    sweep_rx12 = len(rig2.open_cards("RX-12"))
    ok = cover_rx12 == 1 and not view.offers and not result.triggers and len(failed) == 1 and sweep_rx12 == 1
    return Outcome(
        "cobertura fora: 1 RX-12 no caso e 0 ofertas; ponto fora: 0 gatilhos, 1 track.sweep.failed e 1 RX-12",
        f"cobertura: {cover_rx12} RX-12, {len(view.offers)} oferta(s); ponto: {len(result.triggers)} gatilho(s), "
        f"{len(failed)} track.sweep.failed, {sweep_rx12} RX-12",
        ok,
    )


FREE_TEXT = "texto livre plantado pelo eval: estou com {marker}, dor forte"


def _leak_run(ctx: EvalContext, llm: Any, at: tk.Atestado) -> tuple[list[Any], Any]:
    """Caso com aviso + atestado + texto livre plantado; varre as superfícies nomeadas. Devolve os vazamentos (só
    superfície e tipo) e o `CaseView`. Os valores plantados nunca saem daqui."""
    marker = f"PLANTADO-{uuid.uuid4().hex[:10]}"
    text = FREE_TEXT.format(marker=marker)
    buffer = io.StringIO()
    with tk.capture_root_log(buffer):
        rig, c, view = _offered_with(ctx, llm, at, text=text)
        inbox = _need(rig.tracker, "inbox", "SAIDA-AC-09")
        returns = {
            "CaseView": view,
            "case": rig.tracker.case(view.case_id),
            "inbox": [m.model_dump(mode="json") for m in inbox(c["employee_id"])],
        }
    rig.log = buffer
    blobs = tk.surfaces(rig, returns=returns, llm_messages=tk.all_llm_messages(llm))
    return tk.leaks(blobs, [*at.planted, marker, text]), view


def _calls(llm: Any) -> int:
    return llm.calls if isinstance(llm, tk.Recording) else len(getattr(llm, "calls", []))


def _e3_15(ctx: EvalContext) -> Outcome:
    at = tk.atestado(ctx, "at-01")
    llm = ScriptedLLM(by_tool={_tool_name(): [tk.scripted_fields(at)]})
    found, view = _leak_run(ctx, llm, at)
    ok = not found and _calls(llm) >= 1 and view.reading is not None
    return Outcome(
        "0 ocorrências de CID ou texto livre plantados em tabelas, trace_event, log, retornos e mensagens ao modelo "
        "(caminho PDF, com a leitura feita)",
        f"vazamentos: {tk.describe_leaks(found)}; chamadas ao modelo {_calls(llm)}; leitura "
        f"{'feita' if view.reading is not None else 'ausente'}",
        ok,
        reason="respostas HTTP ficam no tests/privacy da C7 (o eval roda sem HTTP)",
    )


def _e3_16(ctx: EvalContext) -> Outcome:
    at = tk.atestado(ctx, "at-02")
    llm = ScriptedLLM(by_tool={_tool_name(): [tk.scripted_fields(at)]})
    rig, _, view = _offered_with(ctx, llm, at)
    rx08 = rig.open_cards("RX-08", view.case_id)
    reading = view.reading
    verdict = reading.verdict if reading else None
    reasons = sorted(reading.reasons) if reading else None
    ok = (
        verdict == at.expect["verdict"]
        and reasons == sorted(at.expect["reasons"])
        and len(rx08) == 1
        and view.abono == "provisorio"
    )
    return Outcome(
        f"verdict {at.expect['verdict']} {at.expect['reasons']}, 1 RX-08, abono provisório (nunca recusa)",
        f"verdict {verdict} {reasons}, {len(rx08)} RX-08, abono {view.abono}",
        ok,
    )


def _read(at: tk.Atestado, llm: Any, run_id: str) -> Any:
    from escalista.ingest.atestado import read_atestado

    return read_atestado(
        data=at.data,
        media_type=at.media_type,
        llm=llm,
        run_id=run_id,
        expected_day=at.expected_day,
        employee_name=at.employee_name,
    )


def _e3_22(ctx: EvalContext) -> Outcome:
    at = tk.atestado(ctx, "at-04")
    llm = ScriptedLLM(by_tool={_tool_name(): [tk.scripted_fields(at)]})
    reading = _read(at, llm, "eval-E3-22")
    right, total, wrong = tk.field_score(reading, at.expect)
    ok = reading.verdict == at.expect["verdict"] and not llm.calls and not wrong
    return Outcome(
        f"verdict {at.expect['verdict']} e 0 chamadas ao modelo",
        f"verdict {reading.verdict}; {len(llm.calls)} chamada(s); campos {right}/{total}"
        + (f" (errados: {', '.join(wrong)})" if wrong else ""),
        ok,
    )


# --- E3-21, 23, 24, 27: com modelo ----------------------------------------------------------------------------------


def model_client(ctx: EvalContext) -> tuple[Any, MemorySink]:
    """Cliente do modelo e o sink onde ele emite (como o E4-02): `client_factory` com `MemorySink` próprio, ou o
    `ctx.llm` com o `ctx.sink`."""
    if ctx.client_factory is not None:
        sink = MemorySink()
        return ctx.client_factory(sink), sink
    if ctx.llm is None:
        raise NotRun("sem chave")
    return ctx.llm, ctx.sink


def judged(at: tk.Atestado, reading: Any, found: list[Any], model: Any, extra: str = "") -> Outcome:
    """Critério da DEC-071: `verdict` e `reasons` iguais ao gabarito e 0 CID vazado; acerto por campo é métrica."""
    right, total, wrong = tk.field_score(reading, at.expect)
    verdict_ok = reading.verdict == at.expect["verdict"] and sorted(reading.reasons) == sorted(at.expect["reasons"])
    return Outcome(
        f"verdict {at.expect['verdict']} {at.expect['reasons']} e 0 CID vazado",
        f"verdict {reading.verdict} {sorted(reading.reasons)}; campos {right}/{total}"
        + (f" (errados: {', '.join(wrong)})" if wrong else "")
        + f"; vazamentos: {tk.describe_leaks(found)}"
        + extra,
        verdict_ok and not found,
        model=model,
        metrics={"rn04.atestado": {"campos_certos": right, "campos": total, "arquivo": at.file}},
    )


def read_with_model(ctx: EvalContext, prefix: str, scenario_id: str) -> tuple[tk.Atestado, Any, list[Any], Any]:
    """Lê o atestado `prefix` com o modelo do contexto; devolve a leitura, os vazamentos (retorno e mensagens ao
    modelo) e o `ModelUse` dos eventos `track.llm.read_atestado`. Modelo indisponível → `NotRun`."""
    from escalista.domain.contracts import LLMUnavailableError

    at = tk.atestado(ctx, prefix)
    client, sink = model_client(ctx)
    recording = tk.Recording(client)
    run_id = f"eval-{scenario_id}-{uuid.uuid4().hex[:8]}"
    try:
        reading = _read(at, recording, run_id)
    except LLMUnavailableError as exc:
        raise NotRun(MODEL_DOWN) from exc
    blobs = {
        "retorno.AtestadoReading": reading.model_dump_json(),
        "llm.mensagens": "\n".join(str(getattr(m, "content", m)) for m in recording.messages),
    }
    return at, reading, tk.leaks(blobs, at.planted), model_use(sink, run_id, [tk.READ_KIND])


def _with_model(prefix: str, scenario_id: str) -> Callable[[EvalContext], Outcome]:
    def run(ctx: EvalContext) -> Outcome:
        at, reading, found, model = read_with_model(ctx, prefix, scenario_id)
        return judged(at, reading, found, model)

    return run


def _e3_24(ctx: EvalContext) -> Outcome:
    from escalista.domain.contracts import LLMUnavailableError

    at = tk.atestado(ctx, "at-09")
    client, sink = model_client(ctx)
    recording = tk.Recording(client)
    try:
        found, view = _leak_run(ctx, recording, at)
    except LLMUnavailableError as exc:
        raise NotRun(MODEL_DOWN) from exc
    if view.reading is None:  # o Tracker trata a falha do modelo como RX-12 e segue sem leitura
        raise NotRun(MODEL_DOWN)
    model = model_use(sink, f"track-{view.case_id}", [tk.READ_KIND])
    return judged(at, view.reading, found, model, extra=f"; chamadas ao modelo {recording.calls}")


def _s(
    id_: str,
    description: str,
    tier: str,
    *requires: Requirement,
    uses_model: bool = False,
    run: Callable[[EvalContext], Outcome] = _pending,
) -> Scenario:
    return Scenario(id_, description, run, suite=SUITE, uses_model=uses_model, tier=tier, requires=requires)


SCENARIOS: tuple[Scenario, ...] = (
    # Seção 6: sem modelo (StepClock, ScriptedLLM, SQLite em memória).
    _s("E3-01", "Varredura emite os gatilhos plantados, sem repetir no mesmo instante", "T1b", BUILD_TRACKER,
       run=_e3_01),
    _s("E3-02", "Falta de ponto só dispara após a tolerância (pol_atraso)", "T1b", BUILD_TRACKER, TRACK_POLICY,
       run=_e3_02),
    _s("E3-03", "Hora extra perto do limite (80%) e no limite (100%)", "T2", BUILD_TRACKER),
    _s("E3-04", "Falta que só cobre com hora extra sinaliza overtime_needed", "T1b", BUILD_TRACKER, run=_e3_04),
    _s("E3-05", "Ofertas na ordem do ranking, 1º candidato sem hora extra", "T1a", BUILD_TRACKER, run=_e3_05),
    _s("E3-06", "Cobertura aceita e aprovada não cria violação nova", "T1a", BUILD_TRACKER, run=_e3_06),
    _s("E3-07", "Loja sem folga vira cartão RX-05 na fila", "T1a", BUILD_TRACKER, run=_e3_07),
    _s("E3-08", "Ofertas expiram em sequência e viram RX-06 no prazo", "T1a/T1b", BUILD_TRACKER, TRACK_POLICY,
       run=_e3_08),
    _s("E3-09", "Pergunta sem resposta vira RX-09 no prazo", "T1b", BUILD_TRACKER, TRACK_POLICY, run=_e3_09),
    _s("E3-10", "Toda mensagem enviada aponta para um evento do rastro (0 órfãos)", "T1a", BUILD_TRACKER,
       run=_e3_10),
    _s("E3-11", "Ferramenta com efeito sem aceite e aprovação é recusada", "T1a", BUILD_TRACKER, APPLY_COVER,
       run=_e3_11),
    _s("E3-12", "Remetente fora do quadro é rejeitado sem abrir caso", "T1a", BUILD_TRACKER, run=_e3_12),
    _s("E3-13", "Modelo indisponível no atestado: caso segue com RX-12", "T1b", BUILD_TRACKER, READ_ATESTADO,
       run=_e3_13),
    _s("E3-14", "Falha da cobertura ou do ponto: RX-12 e 0 gatilhos inventados", "T1b", BUILD_TRACKER, run=_e3_14),
    _s("E3-15", "CID e texto livre plantados não vazam em superfície nenhuma", "T1b", BUILD_TRACKER, FIND_LEAKS,
       run=_e3_15),
    _s("E3-16", "Atestado com data inconsistente vira RX-08, abono provisório", "T1b", BUILD_TRACKER, READ_ATESTADO,
       run=_e3_16),
    # Seção 7: atestados com modelo (uma rodada, à mão, com chave); E3-22 aqui no modo T1b, sem modelo.
    _s("E3-21", "Atestado PDF legível: acerto por campo", "T1b", READ_ATESTADO, FIND_LEAKS, uses_model=True,
       run=_with_model("at-01", "E3-21")),
    _s("E3-22", "Atestado PDF só imagem: ilegível e 0 chamadas ao modelo", "T1b", BUILD_TRACKER, READ_ATESTADO,
       run=_e3_22),
    _s("E3-23", "Atestado com data inconsistente: verdict e motivo", "T1b", READ_ATESTADO, FIND_LEAKS,
       uses_model=True, run=_with_model("at-02", "E3-23")),
    _s("E3-24", "CID espalhado no atestado, pelo Tracker com modelo real: 0 vazamentos", "T1b", BUILD_TRACKER,
       READ_ATESTADO, FIND_LEAKS, uses_model=True, run=_e3_24),
    _s("E3-25", "Foto legível do atestado (visão)", "T2", READ_ATESTADO, uses_model=True),
    _s("E3-26", "Foto ruidosa do atestado (visão)", "T2", READ_ATESTADO, uses_model=True),
    _s("E3-27", "Atestado sem CRM: inconsistente com sem_crm", "T1b", READ_ATESTADO, FIND_LEAKS, uses_model=True,
       run=_with_model("at-03", "E3-27")),
    _s("E3-28", "Foto ilegível do atestado: ilegível e nada inventado", "T2", READ_ATESTADO, uses_model=True),
)  # fmt: skip
