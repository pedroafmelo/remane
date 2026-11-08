"""Carregador do quadro de demonstração (borda): lojas, pessoas e demanda sintéticas de `data/demo/`."""

from __future__ import annotations

from pathlib import Path

from pydantic import TypeAdapter

from escalista.domain.schedule import DemandSlot, Employee, Store


def load_demo_network(directory: Path) -> tuple[list[Store], list[Employee], list[DemandSlot]]:
    """Lê `lojas.json`, `pessoas.json` e `demanda.json`. `Employee.sex` fica no núcleo (RN-13)."""
    stores = TypeAdapter(list[Store]).validate_json((directory / "lojas.json").read_bytes())
    employees = TypeAdapter(list[Employee]).validate_json((directory / "pessoas.json").read_bytes())
    demand = TypeAdapter(list[DemandSlot]).validate_json((directory / "demanda.json").read_bytes())
    return stores, employees, demand
