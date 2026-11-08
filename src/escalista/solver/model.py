"""Modelo CP-SAT da escala semanal (plano da C5, A2; RF-05, RX-02). Sem I/O: entra `SolveRequest`, sai `SolveResult`.

Modelo, por loja (as lojas são independentes, porque a pessoa só trabalha na própria loja; resolver loja a loja
é exato e mais rápido que um modelo único):
- **Variáveis:** `x[pessoa, dia, turno]` booleana para cada turno do catálogo (`catalog.py`); no máximo 1 turno por
  pessoa e dia. Nomes estáveis: `x_<pessoa>_d<dia>_<HHMM>+<min>`.
- **Restrições duras (4 primitivas do cartão):** horas na semana ≤ `jornada_semanal_max`; horas no dia ≤
  `jornada_diaria_max` (o catálogo já respeita, e a restrição explícita fica de garantia); entre turnos de dias
  consecutivos, descanso ≥ `interjornada_min`; dias sem turno ≥ `repouso_semanal`. O solver **não escala hora extra**.
- **Cobertura com penalidade** (não é restrição dura): `falta[faixa] ≥ pedidas − cobertas`. Objetivo, em inteiros
  (centavos × minutos): Σ turno × minutos × salário-hora em centavos + `PENALTY_WAGE_HOURS` × 60 × maior salário em
  centavos × Σ falta. Uma faixa a menos sem gente vale mais que 100 horas de salário: cobrir vem antes de economizar.
- **Semântica de hora (a de `cost.py`):** o turno conta no dia de início; a pessoa cobre a faixa se o turno cobre a
  faixa inteira.
- **Quebra de simetria:** pessoas da mesma loja com o mesmo salário-hora são intercambiáveis; o modelo ordena as
  horas da semana delas pelo id (válido: trocar as semanas de duas pessoas iguais não muda custo nem regras).
- **Determinismo:** `seed` → `random_seed`; entrada em ordem canônica; `input_hash` = sha256 do JSON canônico de
  (cartão, lojas, pessoas, demanda, semana, seed). Com 1 thread, a mesma entrada dá a mesma escala; com várias, o
  aceite é a escala gravada e reverificada (DEC-020).
- **Status:** todas as lojas com ótimo provado → `optimal`; alguma parada no limite de tempo com solução →
  `feasible`; alguma loja sem solução no tempo → `timeout`; modelo inviável → `infeasible`.
- **RX-02:** se sobrar faixa descoberta, a escala parcial é devolvida com um `ExceptionCard` ao gestor com o cálculo
  de contratação por loja (ver `_rx02`).

C6 (A5), `SolveRequest.spec` e regras por pessoa:
- **Restrições duras por pessoa vêm do cartão**, não da spec: as regras `indisponibilidade` {employee_id, day, start?,
  end?} e `jornada_semanal_max_pessoa` {employee_id, hours} que `rules.spec.card_with_spec` acrescenta (camada
  `execucao`). Assim o solver obedece exatamente o que o verificador confere; valem com ou sem spec. Indisponível zera
  os turnos da pessoa que cruzam o intervalo (o dia inteiro sem `start`/`end`; o turno da véspera que vira a noite
  também conta); o teto por pessoa limita os minutos da semana. Só restringem: nada do cartão é afrouxado.
- **`spec=None` = C5**: mesmo objetivo e mesmo `input_hash` (a spec só entra no hash quando existe; o hint, só quando
  `stability_weight` > 0, porque aí ele muda o objetivo).
- **Pesos, na escala do custo (centavos × minutos).** Unidade = 1 hora do salário-hora **médio** da loja
  (60 × média em centavos). `shortfall_weight` substitui `PENALTY_WAGE_HOURS` (e segue sobre o **maior** salário, como
  na C5: a spec padrão, 100, dá o mesmo objetivo). `preference_weight` × unidade por preferência violada:
  `folga_preferida` violada = turno que **começa** no dia (semântica de `cost.py`); `janela_preferida` violada = cada
  dia com turno que começa fora da janela (manhã: início < 12:00; tarde: 12:00 a 17:59; noite: ≥ 18:00).
  `stability_weight` × unidade por turno escolhido que não é o do hint (mesma pessoa, dia, início e fim; só com hint);
  hint fora do catálogo vale o turno mais próximo do catálogo (menor |Δinício| + |Δfim|; empate, o primeiro na ordem
  do catálogo). Turno do hint que sai não é penalizado (sair só economiza; a cobertura já cuida da demanda). Com os
  padrões, 5 de preferência = 5 horas de salário médio: pesa contra a troca de pessoa de custo parecido, mas não contra
  uma faixa descoberta (100 horas do maior salário).
- **Quebra de simetria** só entre pessoas sem nada próprio (regra por pessoa, preferência ou turno no hint com
  estabilidade): com isso, elas deixam de ser intercambiáveis.
- `ModelStats.preferences_met` / `preferences_total`: preferências da spec atendidas na escala devolvida.
"""

from __future__ import annotations

import hashlib
import json
import math
import time as wallclock
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal

from ortools.sat.python import cp_model

from escalista.domain.contracts import ExceptionCard, ExceptionOption, Role
from escalista.domain.results import SolveRequest, SolveResult
from escalista.domain.rules import RuleCard
from escalista.domain.schedule import DemandSlot, Employee, Schedule, Shift, Store
from escalista.domain.spec import PreferredDayOffConstraint, PreferredWindowConstraint, SolveSpec
from escalista.solver.catalog import CatalogShift, build_catalog

DAYS = 7
DAY_MIN = 24 * 60
SLOT_MIN = 30
PENALTY_WAGE_HOURS = 100
RX02_CODE = "RX-02"
UNAVAILABLE_KIND = "indisponibilidade"
PERSON_WEEKLY_KIND = "jornada_semanal_max_pessoa"
# Janela pelo início do turno, em minutos desde a meia-noite: [início, fim).
WINDOWS = {"manha": (0, 12 * 60), "tarde": (12 * 60, 18 * 60), "noite": (18 * 60, DAY_MIN)}


@dataclass(frozen=True)
class Limits:
    """As 4 primitivas do cartão, em minutos e dias."""

    weekly_min: int
    daily_min: int
    rest_gap_min: int
    rest_days: int

    @classmethod
    def from_card(cls, card: RuleCard) -> Limits:
        def param(kind: str, key: str) -> float:
            for rule in card.rules:
                if rule.kind == kind and key in rule.params:
                    return float(rule.params[key])
            raise ValueError(f"o cartão não tem a primitiva {kind} ({key}); o solver não decide sem ela")

        return cls(
            weekly_min=round(param("jornada_semanal_max", "hours") * 60),
            daily_min=round(param("jornada_diaria_max", "hours") * 60),
            rest_gap_min=round(param("interjornada_min", "hours") * 60),
            rest_days=round(param("repouso_semanal", "days")),
        )

    @property
    def per_person_week_min(self) -> int:
        """Horas que uma pessoa pode dar na semana: mín(limite semanal, dias de trabalho × limite diário)."""
        return min(self.weekly_min, max(DAYS - self.rest_days, 0) * self.daily_min)


@dataclass
class StoreOutcome:
    status: str
    shifts: list[Shift] = field(default_factory=list)


@dataclass
class ModelStats:
    """Tamanho do modelo e status por loja, para o benchmark."""

    num_vars: int = 0
    num_constraints: int = 0
    catalog_size: dict[str, int] = field(default_factory=dict)
    store_status: dict[str, str] = field(default_factory=dict)
    solver_wall_s: dict[str, float] = field(default_factory=dict)  # só o CP-SAT, sem montar o modelo
    preferences_met: int = 0  # preferências suaves da spec atendidas na escala devolvida
    preferences_total: int = 0


@dataclass(frozen=True)
class PersonRules:
    """Regras `execucao` do cartão por pessoa: intervalos indisponíveis (minutos absolutos na semana) e teto semanal."""

    blocked: dict[str, list[tuple[int, int]]] = field(default_factory=dict)
    weekly_cap_min: dict[str, int] = field(default_factory=dict)

    @classmethod
    def from_card(cls, card: RuleCard, week_start: date) -> PersonRules:
        blocked: dict[str, list[tuple[int, int]]] = defaultdict(list)
        caps: dict[str, int] = {}
        for rule in card.rules:
            p = rule.params
            if rule.kind == UNAVAILABLE_KIND:
                base = (date.fromisoformat(str(p["day"])) - week_start).days * DAY_MIN
                start = _hhmm_min(p.get("start"), 0)
                end = _hhmm_min(p.get("end"), DAY_MIN)
                blocked[str(p["employee_id"])].append((base + start, base + end))
            elif rule.kind == PERSON_WEEKLY_KIND:
                eid = str(p["employee_id"])
                cap = round(float(p["hours"]) * 60)
                caps[eid] = min(cap, caps.get(eid, cap))
        return cls(blocked=dict(blocked), weekly_cap_min=caps)

    def is_blocked(self, eid: str, day: int, k: CatalogShift) -> bool:
        start, end = day * DAY_MIN + k.start_min, day * DAY_MIN + k.end_min
        return any(start < b_end and end > b_start for b_start, b_end in self.blocked.get(eid, ()))

    def has(self, eid: str) -> bool:
        return eid in self.blocked or eid in self.weekly_cap_min


def _hhmm_min(value: object, default: int) -> int:
    if value is None or value == "":
        return default
    h, m = str(value).split(":")[:2]
    return int(h) * 60 + int(m)


# Entrada canônica e hash ----------------------------------------------------------------------------------------


def canonical_input(req: SolveRequest) -> dict:
    """A entrada que define a escala, em ordem canônica (a ordem das listas não muda a entrada).

    Sem spec, as chaves são as da C5 (os hashes gravados não mudam). Com spec, entra a spec; e o hint, só quando
    `stability_weight` > 0 (aí ele muda o objetivo; sem peso, é só ponto de partida do CP-SAT).
    """
    out = {
        "card": req.card.model_dump(mode="json"),
        "stores": [s.model_dump(mode="json") for s in sorted(req.stores, key=lambda s: s.id)],
        "employees": [e.model_dump(mode="json") for e in sorted(req.employees, key=lambda e: e.id)],
        "demand": [d.model_dump(mode="json") for d in sorted(req.demand, key=lambda d: (d.store_id, d.day, d.start))],
        "week_start": req.week_start.isoformat(),
        "seed": req.seed,
    }
    if req.spec is not None:
        out["spec"] = req.spec.model_dump(mode="json")
        if req.spec.stability_weight > 0 and req.hint is not None:
            out["hint"] = [
                sh.model_dump(mode="json")
                for sh in sorted(req.hint.shifts, key=lambda s: (s.employee_id, s.start, s.end, s.store_id))
            ]
    return out


def input_hash(req: SolveRequest) -> str:
    raw = json.dumps(canonical_input(req), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


# Solver ---------------------------------------------------------------------------------------------------------


def _cents(value: Decimal) -> int:
    return int((value * 100).to_integral_value(rounding=ROUND_HALF_UP))


def _slot_abs_min(slot: DemandSlot, week_start: date) -> int:
    return (slot.day - week_start).days * DAY_MIN + slot.start.hour * 60 + slot.start.minute


def _solve_store(
    store: Store,
    employees: list[Employee],
    slots: list[DemandSlot],
    limits: Limits,
    req: SolveRequest,
    time_limit_s: float,
    hint: list[Shift],
    stats: ModelStats,
    person: PersonRules,
) -> StoreOutcome:
    catalog = build_catalog(store.opens, store.closes, limits.daily_min)
    stats.catalog_size[store.id] = len(catalog)
    model = cp_model.CpModel()
    x: dict[tuple[str, int, CatalogShift], cp_model.IntVar] = {}
    for e in employees:
        for d in range(DAYS):
            for k in catalog:
                x[e.id, d, k] = model.new_bool_var(f"x_{e.id}_d{d}_{k.label}")

    for (eid, d, k), var in x.items():
        if person.is_blocked(eid, d, k):
            model.add(var == 0)

    week_minutes: dict[str, cp_model.LinearExpr] = {}
    for e in employees:
        works = []
        for d in range(DAYS):
            day_vars = [x[e.id, d, k] for k in catalog]
            model.add_at_most_one(day_vars)
            model.add(sum(k.duration_min * x[e.id, d, k] for k in catalog) <= limits.daily_min)
            works.append(sum(day_vars))
        model.add(sum(works) <= DAYS - limits.rest_days)
        week_minutes[e.id] = sum(k.duration_min * x[e.id, d, k] for d in range(DAYS) for k in catalog)
        model.add(week_minutes[e.id] <= limits.weekly_min)
        if e.id in person.weekly_cap_min:
            model.add(week_minutes[e.id] <= person.weekly_cap_min[e.id])
        # Interjornada: turno do dia d que termina em `end` conflita com o do dia d+1 que começa antes de
        # end + descanso − 24h. Para cada fim possível, "termina em ≥ end" + "começa cedo demais" ≤ 1.
        for d in range(DAYS - 1):
            for end in sorted({k.end_min for k in catalog}):
                late = [x[e.id, d, k] for k in catalog if k.end_min >= end]
                early = [x[e.id, d + 1, k] for k in catalog if k.start_min + DAY_MIN - end < limits.rest_gap_min]
                if late and early:
                    model.add(sum(late) + sum(early) <= 1)

    spec = req.spec
    prefs = _preferences(spec, employees, req.week_start)
    stability_on = spec is not None and spec.stability_weight > 0 and req.hint is not None
    stable = _stability_targets(hint, catalog, req.week_start) if stability_on else {}
    # Quem tem algo próprio deixa de ser intercambiável: fica fora da quebra de simetria.
    own = {e.id for e in employees if person.has(e.id)} | {eid for eid, _, _ in prefs} | {eid for eid, _ in stable}

    by_wage: dict[Decimal, list[str]] = defaultdict(list)
    for e in employees:
        if e.id not in own:
            by_wage[e.hourly_wage].append(e.id)
    for ids in by_wage.values():
        for a, b in zip(ids, ids[1:], strict=False):
            model.add(week_minutes[a] >= week_minutes[b])

    max_wage = max((_cents(e.hourly_wage) for e in employees), default=0)
    shortfall_weight = spec.shortfall_weight if spec is not None else PENALTY_WAGE_HOURS
    penalty = shortfall_weight * 60 * max(max_wage, 1)
    shortfalls = []
    for slot in slots:
        t = _slot_abs_min(slot, req.week_start)
        day = t // DAY_MIN
        covering = [
            x[e.id, d, k]
            for e in employees
            for d in (day - 1, day)  # turno do dia anterior que vira a noite também cobre
            if 0 <= d < DAYS
            for k in catalog
            if d * DAY_MIN + k.start_min <= t and d * DAY_MIN + k.end_min >= t + SLOT_MIN
        ]
        short = model.new_int_var(0, max(slot.required, 0), f"falta_{slot.day.isoformat()}_{slot.start:%H%M}")
        model.add(sum(covering) + short >= slot.required)
        shortfalls.append(short)

    wage = {e.id: _cents(e.hourly_wage) for e in employees}
    coef = {key: wage[key[0]] * key[2].duration_min for key in x}
    if spec is not None and employees:
        # Unidade dos pesos suaves: 1 hora do salário-hora médio da loja, em centavos × minutos.
        unit = 60 * max(round(sum(wage.values()) / len(wage)), 1)
        for key in x:
            eid, d, k = key
            violations = sum(1 for p_eid, p_day, p_win in prefs if p_eid == eid and _violates(d, k, p_day, p_win))
            if violations:
                coef[key] += spec.preference_weight * unit * violations
            if stability_on and stable.get((eid, d)) != k:
                coef[key] += spec.stability_weight * unit
    model.minimize(sum(c * x[key] for key, c in coef.items()) + penalty * sum(shortfalls))

    index = {(eid, d, k.start_min, k.duration_min): var for (eid, d, k), var in x.items()}
    for sh in hint:
        d = (sh.start.date() - req.week_start).days
        key = (
            sh.employee_id,
            d,
            sh.start.hour * 60 + sh.start.minute,
            int((sh.end - sh.start).total_seconds() // 60),
        )
        if key in index:
            model.add_hint(index[key], 1)

    stats.num_vars += len(model.proto.variables)
    stats.num_constraints += len(model.proto.constraints)
    out = StoreOutcome(status="timeout")

    solver = cp_model.CpSolver()
    solver.parameters.random_seed = req.seed % (2**31)
    solver.parameters.num_workers = max(1, req.num_workers)
    solver.parameters.max_time_in_seconds = max(time_limit_s, 0.05)
    # Medido no benchmark: o presolve do CP-SAT enfraquece o limite inferior deste modelo (o LP do modelo cheio já
    # é justo), e sem ele o ótimo da instância 60 × 7 é provado em menos tempo, com 1 thread e com 8.
    solver.parameters.cp_model_presolve = False
    code = solver.solve(model)
    stats.solver_wall_s[store.id] = round(solver.wall_time, 3)
    out.status = {
        cp_model.OPTIMAL: "optimal",
        cp_model.FEASIBLE: "feasible",
        cp_model.INFEASIBLE: "infeasible",
        cp_model.MODEL_INVALID: "infeasible",
    }.get(code, "timeout")
    stats.store_status[store.id] = out.status
    if code in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        chosen = [(eid, d, k) for (eid, d, k), var in x.items() if solver.boolean_value(var)]
        stats.preferences_total += len(prefs)
        stats.preferences_met += sum(
            1
            for p_eid, p_day, p_win in prefs
            if not any(eid == p_eid and _violates(d, k, p_day, p_win) for eid, d, k in chosen)
        )
        for eid, d, k in chosen:
            start = datetime.combine(req.week_start + timedelta(days=d), datetime.min.time()) + timedelta(
                minutes=k.start_min
            )
            out.shifts.append(
                Shift(employee_id=eid, store_id=store.id, start=start, end=start + timedelta(minutes=k.duration_min))
            )
    return out


def _preferences(spec: SolveSpec | None, employees: list[Employee], week_start: date) -> list[tuple[str, int, str]]:
    """Preferências da spec para as pessoas da loja: `(pessoa, dia da folga ou -1, janela ou "")`."""
    if spec is None:
        return []
    ids = {e.id for e in employees}
    out: list[tuple[str, int, str]] = []
    for item in spec.constraints:
        if item.employee_id not in ids:
            continue
        if isinstance(item, PreferredDayOffConstraint):
            day = (item.day - week_start).days
            if 0 <= day < DAYS:
                out.append((item.employee_id, day, ""))
        elif isinstance(item, PreferredWindowConstraint):
            out.append((item.employee_id, -1, item.window))
    return out


def _violates(day: int, k: CatalogShift, pref_day: int, window: str) -> bool:
    """O turno `k` no dia `day` viola a preferência? Folga: o turno começa no dia. Janela: começa fora dela."""
    if window:
        lo, hi = WINDOWS[window]
        return not lo <= k.start_min % DAY_MIN < hi
    return day == pref_day


def _stability_targets(
    hint: list[Shift], catalog: list[CatalogShift], week_start: date
) -> dict[tuple[str, int], CatalogShift]:
    """Turno do catálogo que repete o hint, por (pessoa, dia); fora do catálogo, o mais próximo (|Δinício| + |Δfim|)."""
    out: dict[tuple[str, int], CatalogShift] = {}
    for sh in sorted(hint, key=lambda s: (s.employee_id, s.start)):
        day = (sh.start.date() - week_start).days
        if not 0 <= day < DAYS or not catalog:
            continue
        start = sh.start.hour * 60 + sh.start.minute
        end = start + int((sh.end - sh.start).total_seconds() // 60)
        out.setdefault(
            (sh.employee_id, day), min(catalog, key=lambda k: abs(k.start_min - start) + abs(k.end_min - end))
        )
    return out


def _combine_status(statuses: list[str]) -> str:
    if "infeasible" in statuses:
        return "infeasible"
    if "timeout" in statuses:
        return "timeout"
    if "feasible" in statuses:
        return "feasible"
    return "optimal"


def _shortfalls(shifts: list[Shift], demand: list[DemandSlot]) -> list[DemandSlot]:
    """Faixas com falta; `required` de cada uma é **quanto faltou** (pedidas − cobertas)."""
    by_store: dict[str, list[Shift]] = defaultdict(list)
    for sh in shifts:
        by_store[sh.store_id].append(sh)
    out = []
    for slot in demand:
        start = datetime.combine(slot.day, slot.start)
        end = start + timedelta(minutes=SLOT_MIN)
        people = {sh.employee_id for sh in by_store[slot.store_id] if sh.start <= start and sh.end >= end}
        if len(people) < slot.required:
            out.append(slot.model_copy(update={"required": slot.required - len(people)}))
    return out


def solve(req: SolveRequest, stats: ModelStats | None = None) -> SolveResult:
    """Resolve a semana. As lojas dividem o `time_limit_s`: cada uma recebe o tempo que sobra ÷ lojas que faltam."""
    t0 = wallclock.perf_counter()
    stats = stats if stats is not None else ModelStats()
    limits = Limits.from_card(req.card)
    digest = input_hash(req)
    stores = sorted(req.stores, key=lambda s: s.id)
    employees = sorted(req.employees, key=lambda e: e.id)
    demand = sorted(req.demand, key=lambda d: (d.store_id, d.day, d.start))
    hint = req.hint.shifts if req.hint is not None else []
    person = PersonRules.from_card(req.card, req.week_start)

    deadline = t0 + req.time_limit_s
    statuses: list[str] = []
    shifts: list[Shift] = []
    for i, store in enumerate(stores):
        budget = max(deadline - wallclock.perf_counter(), 0.0) / (len(stores) - i)
        outcome = _solve_store(
            store,
            [e for e in employees if e.store_id == store.id],
            [d for d in demand if d.store_id == store.id],
            limits,
            req,
            budget,
            [h for h in hint if h.store_id == store.id],
            stats,
            person,
        )
        statuses.append(outcome.status)
        shifts += outcome.shifts

    status = _combine_status(statuses)
    shifts.sort(key=lambda s: (s.employee_id, s.start))
    schedule = None if status == "infeasible" else Schedule(week_start=req.week_start, shifts=shifts)
    uncovered = _shortfalls(shifts, demand)
    exception = _rx02(uncovered, stores, limits, status) if uncovered and schedule is not None else None
    return SolveResult(
        status=status,
        schedule=schedule,
        uncovered=uncovered,
        wall_ms=int((wallclock.perf_counter() - t0) * 1000),
        seed=req.seed,
        input_hash=digest,
        exception=exception,
    )


# RX-02 ----------------------------------------------------------------------------------------------------------


def _br(value: float, digits: int = 1) -> str:
    return f"{value:.{digits}f}".replace(".", ",")


def _rx02(uncovered: list[DemandSlot], stores: list[Store], limits: Limits, status: str) -> ExceptionCard:
    """Demanda acima da capacidade: cálculo de contratação por loja, ao gestor.

    Por loja: pessoa-horas faltando ÷ horas que uma pessoa pode dar na semana (mín. entre o limite semanal e
    dias de trabalho × limite diário) → pessoas a contratar, arredondado para cima. É um **piso**: a falta se
    concentra em picos, e uma pessoa cobre no máximo um turno contínuo por dia.

    Decide o **gestor** (DEC-044): contratar mexe em quadro e orçamento, e a alternativa de curto prazo (hora
    extra) só sai com a autorização prévia dele pela política fictícia `hora_extra_autorizacao_previa`. É ele
    também quem vê a escala parcial e pode aceitá-la para a semana.
    """
    names = {s.id: s.name for s in stores}
    per_person_h = limits.per_person_week_min / 60
    missing: dict[str, float] = defaultdict(float)
    slots: dict[str, int] = defaultdict(int)
    for u in uncovered:
        missing[u.store_id] += u.required * SLOT_MIN / 60
        slots[u.store_id] += 1

    evidence = []
    total_hires = 0
    for store_id in sorted(missing):
        hours = missing[store_id]
        if per_person_h > 0:
            ratio = hours / per_person_h
            hires = math.ceil(round(ratio, 6))
            total_hires += hires
            calc = f"÷ {_br(per_person_h)} h por pessoa na semana = {_br(ratio, 2)} → contratar {hires}"
        else:
            calc = "sem horas disponíveis por pessoa com as regras do cartão; contratação não calculável"
        evidence.append(
            f"{store_id} ({names.get(store_id, store_id)}): faltam {_br(hours)} pessoa-horas em {slots[store_id]} "
            f"faixas de 30 min {calc}"
        )
    evidence.append(
        f"Horas por pessoa na semana = mín({_br(limits.weekly_min / 60)} h semanais, "
        f"{DAYS - limits.rest_days} dias × {_br(limits.daily_min / 60)} h por dia) = {_br(per_person_h)} h"
    )
    evidence.append("Conta mínima: a falta se concentra em picos, e cada pessoa cobre no máximo um turno por dia.")
    if status != "optimal":
        evidence.append(f"O solver parou com status '{status}': parte da falta pode ser do limite de tempo.")
    total_h = sum(missing.values())
    return ExceptionCard(
        code=RX02_CODE,
        title="Demanda acima da capacidade da equipe",
        reason=(
            f"Mesmo com as regras respeitadas, faltam {_br(total_h)} pessoa-horas na semana em "
            f"{len(missing)} loja(s). A escala parcial foi gerada sem hora extra."
        ),
        decider=Role.GESTOR,
        evidence=evidence,
        options=[
            ExceptionOption(
                label=f"Contratar no mínimo {total_hires} pessoa(s)",
                effect="Cobre a falta nas próximas semanas; não resolve a semana atual.",
            ),
            ExceptionOption(
                label="Autorizar hora extra nas faixas descobertas",
                effect="Cobre a semana atual com custo de hora extra; exige autorização prévia do gestor.",
            ),
            ExceptionOption(
                label="Aceitar a escala parcial",
                effect="As faixas listadas ficam sem a equipe pedida nesta semana.",
            ),
        ],
        recommendation=f"Aprovar a escala parcial desta semana e abrir a contratação de {total_hires} pessoa(s).",
        if_no_answer="A escala parcial segue para aprovação do gestor com as faixas descobertas marcadas.",
    )
