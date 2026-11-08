"""Teste de fronteiras (arquitetura.md, seção 2.1): imports proibidos no núcleo e em agents.

Os metatestes provam que o checador falha quando deve; o último confere o código real em src/.
"""

from pathlib import Path

import pytest

from tests.architecture.boundaries import (
    AGENTS_PKG,
    CORE_PACKAGES,
    check_source,
    check_tree,
    check_wallclock,
    wallclock_calls,
)

SRC = Path(__file__).resolve().parents[2] / "src"


def rules_of(module: str, source: str) -> list[str]:
    return [v.imported for v in check_source(module, source)]


# --- verifier: independência do solver (RF-02) ---------------------------------------------------


@pytest.mark.parametrize(
    "source",
    [
        "import ortools\n",
        "from ortools.sat.python import cp_model\n",
        "from escalista import solver\n",
        "from escalista.solver import build\n",
        "import escalista.solver.model\n",
        "from ..solver import build\n",
        "from .. import solver\n",
        "import importlib\nimportlib.import_module('ortools')\n",
        "__import__('ortools')\n",
    ],
)
def test_verifier_cannot_reach_solver_or_ortools(source):
    violations = check_source("escalista.verifier.check", source)
    assert violations, source
    assert any("RF-02" in v.rule for v in violations)


def test_verifier_importing_ortools_inside_type_checking_still_fails():
    source = "from typing import TYPE_CHECKING\nif TYPE_CHECKING:\n    import ortools\n"
    assert rules_of("escalista.verifier.check", source) == ["ortools"]


# --- solver: ortools só aqui; sem bordas -----------------------------------------------------------


def test_solver_may_import_ortools_pydantic_domain_and_stdlib():
    source = "\n".join(
        [
            "import ortools",
            "from ortools.sat.python import cp_model",
            "import pydantic",
            "import math",
            "from escalista.domain import x",
        ]
    )
    assert check_source("escalista.solver.model", source) == []


@pytest.mark.parametrize("pkg", ["llm", "channel", "api", "agents", "audit"])
def test_solver_cannot_import_borders_or_agents(pkg):
    assert check_source("escalista.solver.model", f"import escalista.{pkg}\n")


# --- domain: não importa outros pacotes do projeto ---------------------------------------------------


def test_domain_cannot_import_other_project_packages():
    assert check_source("escalista.domain.contracts", "import escalista.rules\n")
    assert check_source("escalista.domain.contracts", "from escalista import rules\n")
    assert check_source("escalista.domain.ports", "from ..solver import x\n")


def test_domain_may_use_stdlib_pydantic_and_itself():
    source = "\n".join(
        [
            "from __future__ import annotations",
            "import datetime",
            "from pydantic import BaseModel",
            "from escalista.domain import contracts",
            "from . import contracts as c",
        ]
    )
    assert check_source("escalista.domain.ports", source) == []


# --- biblioteca nova e stdlib com efeito no núcleo ---------------------------------------------------


@pytest.mark.parametrize("core", ["domain", "rules", "solver", "verifier"])
@pytest.mark.parametrize("lib", ["numpy", "pandas", "requests", "httpx", "sqlalchemy", "openai"])
def test_unknown_third_party_in_core_fails(core, lib):
    assert check_source(f"escalista.{core}.m", f"import {lib}\n")


@pytest.mark.parametrize("lib", ["socket", "ssl", "http.client", "urllib.request", "sqlite3", "subprocess", "smtplib"])
def test_effectful_stdlib_in_core_fails(lib):
    assert check_source("escalista.rules.loader", f"import {lib}\n")


def test_rules_may_import_yaml():
    assert check_source("escalista.rules.loader", "import yaml\n") == []
    assert check_source("escalista.verifier.m", "import yaml\n")


def test_non_literal_dynamic_import_in_core_fails():
    assert check_source("escalista.verifier.m", "import importlib\nimportlib.import_module(name)\n")


# --- agents: usa núcleo e portas, nunca bordas concretas ---------------------------------------------


@pytest.mark.parametrize("pkg", ["api", "llm", "channel", "clock", "audit", "ingest", "synth", "evals"])
def test_agents_cannot_import_concrete_borders(pkg):
    assert check_source("escalista.agents.optimizer.graph", f"from escalista.{pkg} import x\n")
    assert check_source("escalista.agents.optimizer.graph", f"from ...{pkg} import x\n")


def test_agents_cannot_import_the_sql_store():
    """`store/` (SQL do `Repository`, frente B) é borda: agents usa a porta, nunca a implementação."""
    assert check_source("escalista.agents.optimizer.graph", "import escalista.store\n")
    assert check_source(
        "escalista.agents.optimizer.graph", "from escalista.store.sql_repository import SqlRepository\n"
    )
    assert check_source("escalista.agents.optimizer.graph", "from escalista import store\n")
    assert check_source("escalista.agents.optimizer.graph", "from ...store import x\n")


def test_agents_may_use_core_ports_and_langgraph():
    source = "\n".join(
        [
            "import langgraph",
            "from escalista.domain.ports import LLMClient",
            "from escalista.solver import solve",
            "from escalista.verifier import verify",
        ]
    )
    assert check_source("escalista.agents.optimizer.graph", source) == []


# --- bordas livres -------------------------------------------------------------------------------------


def test_borders_are_not_restricted_by_this_test():
    assert check_source("escalista.llm.client", "import openai\nimport httpx\n") == []


# --- árvore real e contra falso negativo ------------------------------------------------------------------


def test_tree_with_verifier_importing_ortools_is_rejected(tmp_path):
    pkg = tmp_path / "escalista"
    for name in (*CORE_PACKAGES, AGENTS_PKG):
        (pkg / name).mkdir(parents=True)
        (pkg / name / "__init__.py").write_text("")
    (pkg / "__init__.py").write_text("")
    (pkg / "verifier" / "bad.py").write_text("import ortools\n")
    violations = check_tree(pkg)
    assert [v.path.name for v in violations] == ["bad.py"]


def test_tree_with_missing_or_empty_core_package_is_rejected(tmp_path):
    pkg = tmp_path / "escalista"
    (pkg / "domain").mkdir(parents=True)
    violations = check_tree(pkg)
    assert any("ausente ou vazio" in v.rule for v in violations)


def test_real_source_tree_respects_boundaries():
    violations = check_tree(SRC / "escalista")
    assert violations == [], "\n".join(f"{v.path}:{v.line} importa {v.imported}: {v.rule}" for v in violations)


# --- relógio injetado no acompanhamento (C7) ------------------------------------------------------------------------


def test_wallclock_calls_are_detected():
    source = "from datetime import date, datetime\nx = datetime.now()\ny = date.today()\nz = dt.datetime.now()\n"
    assert wallclock_calls(source) == [2, 3, 4]


def test_clock_port_is_not_a_wallclock_call():
    assert wallclock_calls("now = self._clock.now()\n") == []


def test_tracker_never_reads_the_system_clock():
    violations = check_wallclock(SRC / "escalista")
    assert violations == [], "\n".join(f"{v.path}:{v.line} {v.rule}" for v in violations)


def test_tracker_cannot_import_concrete_borders():
    for border in ("store", "audit", "ingest", "llm", "channel", "clock", "synth", "api"):
        assert check_source("escalista.agents.tracker.flow", f"from escalista.{border} import x\n"), border
