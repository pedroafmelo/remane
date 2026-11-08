"""Cadastro simulado (plano da C6, D7; RE-11): casa o nome lido do arquivo com `data/demo/` para trazer salário e cargo.

**Integração simulada.** Os JSON de `data/demo/` são sintéticos; o casamento é a única "integração" e está declarada.
A identidade é da A2 (`resolve_identities`): os `Employee` saem com o **id do rascunho**, não o do cadastro.

- Pessoa: `name_slug` igual ao do cadastro. Nada de parecença (a grafia parecida é cartão da A2, não adivinhação).
- Loja: slug do nome igual ao do cadastro, ou id igual.
- Salário-hora: cadastro > `wage` lido do arquivo > `default_wage` (confirmação do gestor) > valor de
  referência (mediana dos salários do cadastro, rotulada como referência sintética em `assumptions`).
- `sex` nunca é copiado (RN-13; decisão 2 da C6): fica `None`.

`load_cadastro` é a borda (lê JSON); `enrich` é pura.
"""

from __future__ import annotations

import re
import statistics
from dataclasses import dataclass, field
from datetime import time
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from pathlib import Path

from pydantic import TypeAdapter

from escalista.domain.schedule import Employee, Store
from escalista.rules.identity import PersonDraft, StoreDraft, name_slug

NOT_INFORMED_JOB = "Não informado"
_CENT = Decimal("0.01")
_MONEY = re.compile(r"[^\d,.\-]")


@dataclass(frozen=True)
class Cadastro:
    """Pessoas e lojas do cadastro simulado (sintético)."""

    people: list[Employee]
    stores: list[Store]


@dataclass(frozen=True)
class EnrichResult:
    """`store_hours` só tem as lojas casadas com o cadastro: as demais ficam com o horário inferido pela A3."""

    employees: list[Employee]
    stores: list[Store] | None
    store_hours: dict[str, tuple[time, time]]
    matched_people: int
    matched_stores: int
    assumptions: list[str] = field(default_factory=list)
    reference_wage: Decimal | None = None  # preenchido só quando o valor de referência foi usado


def load_cadastro(directory: Path) -> Cadastro:
    """Lê `pessoas.json` e `lojas.json` de `directory` (normalmente `data/demo/`)."""
    people = TypeAdapter(list[Employee]).validate_json((directory / "pessoas.json").read_bytes())
    stores = TypeAdapter(list[Store]).validate_json((directory / "lojas.json").read_bytes())
    return Cadastro(people=people, stores=stores)


def reference_wage(cadastro: Cadastro) -> Decimal:
    """Mediana dos salários-hora do cadastro, em centavos. Constante calculada, não dado real."""
    wages = [e.hourly_wage for e in cadastro.people]
    if not wages:
        raise ValueError("cadastro sem pessoas: não há valor de referência")
    return Decimal(statistics.median(wages)).quantize(_CENT, rounding=ROUND_HALF_UP)


def parse_wage(text: str | None) -> Decimal | None:
    """Salário-hora lido do arquivo ("12,40", "R$ 12.40", "1.234,50"). Vazio, ilegível ou não positivo → `None`."""
    if text is None:
        return None
    cleaned = _MONEY.sub("", text.strip())
    if not cleaned:
        return None
    if "," in cleaned:  # vírgula decimal; o ponto, se houver, é milhar
        cleaned = cleaned.replace(".", "").replace(",", ".")
    try:
        value = Decimal(cleaned)
    except InvalidOperation:
        return None
    return value.quantize(_CENT, rounding=ROUND_HALF_UP) if value > 0 and value.is_finite() else None


def _brl(value: Decimal) -> str:
    whole, frac = f"{value.quantize(_CENT, rounding=ROUND_HALF_UP):.2f}".split(".")
    return f"R$ {whole},{frac}"


def _plural(n: int, one: str, many: str) -> str:
    return f"{n} {one if n == 1 else many}"


def enrich(
    people: list[PersonDraft],
    stores: list[StoreDraft],
    *,
    cadastro: Cadastro | None,
    default_wage: Decimal | None,
    default_contract_hours: int,
) -> EnrichResult:
    """Completa as pessoas do rascunho com salário, cargo e carga do cadastro (ou do que o gestor confirmou)."""
    by_slug: dict[str, Employee] = {}
    if cadastro is not None:
        for e in cadastro.people:
            by_slug.setdefault(name_slug(e.name), e)
    fallback = (
        default_wage
        if default_wage is not None
        else (reference_wage(cadastro) if cadastro is not None and cadastro.people else None)
    )
    if fallback is None:
        raise ValueError("sem salário-hora: informe `default_wage` ou passe um cadastro")

    employees: list[Employee] = []
    matched = from_file = from_default = 0
    for p in people:
        hit = by_slug.get(name_slug(p.name))
        if hit is not None:
            matched += 1
            wage, job, hours, profile = hit.hourly_wage, hit.job, hit.contract_hours, hit.profile
        else:
            file_wage = parse_wage(p.wage)
            if file_wage is not None:
                from_file += 1
            else:
                from_default += 1
            wage, job, hours, profile = file_wage or fallback, NOT_INFORMED_JOB, default_contract_hours, "padrao"
        employees.append(
            Employee(
                id=p.id,
                name=p.name,
                store_id=p.store_id,
                job=job,
                hourly_wage=wage,
                contract_hours=hours,
                sex=None,
                profile=profile,
            )
        )

    store_hours: dict[str, tuple[time, time]] = {}
    matched_stores: list[Store] = []
    if cadastro is not None:
        by_id = {s.id: s for s in cadastro.stores}
        by_name = {name_slug(s.name): s for s in cadastro.stores}
        for sd in stores:
            hit_store = by_name.get(name_slug(sd.name)) or by_id.get(sd.id)
            if hit_store is not None:
                store_hours[sd.id] = (hit_store.opens, hit_store.closes)
                matched_stores.append(Store(id=sd.id, name=sd.name, opens=hit_store.opens, closes=hit_store.closes))

    assumptions: list[str] = []
    if matched:
        assumptions.append(
            f"Salário e cargo de {_plural(matched, 'pessoa', 'pessoas')} "
            "vieram do cadastro simulado (integração simulada, dados sintéticos)."
        )
    if from_file:
        assumptions.append(f"Salário-hora de {_plural(from_file, 'pessoa', 'pessoas')} veio do arquivo enviado.")
    used_reference = from_default > 0 and default_wage is None
    if from_default:
        label = " (valor de referência sintético: mediana do cadastro simulado)" if used_reference else ""
        assumptions.append(
            f"Salário-hora de referência {_brl(fallback)}{label} usado para "
            f"{_plural(from_default, 'pessoa', 'pessoas')} sem cadastro: informe o real na confirmação."
        )
    if matched_stores:
        assumptions.append(
            f"Horário de funcionamento de {_plural(len(matched_stores), 'loja', 'lojas')} "
            "veio do cadastro simulado (integração simulada, dados sintéticos)."
        )
    return EnrichResult(
        employees=employees,
        stores=matched_stores or None,
        store_hours=store_hours,
        matched_people=matched,
        matched_stores=len(matched_stores),
        assumptions=assumptions,
        reference_wage=fallback if used_reference else None,
    )
