"""Checador de fronteiras entre pacotes (arquitetura.md, seção 2.1), só com a stdlib (`ast`).

Regras, por lista do que é *permitido* (qualquer biblioteca nova no núcleo reprova):
- Núcleo (`domain`, `rules`, `solver`, `verifier`): só stdlib sem efeito, `pydantic`, `escalista.domain`
  e o próprio pacote.
  Exceções: `solver` pode importar `ortools`; `rules` pode importar `yaml`.
- `verifier` não importa `solver` nem `ortools` (RF-02).
- `domain` não importa outros pacotes do projeto.
- `agents` usa núcleo e portas, nunca as bordas concretas.
"""

from __future__ import annotations

import ast
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = "escalista"
CORE_PACKAGES = ("domain", "rules", "solver", "verifier")
AGENTS_PKG = "agents"
CONCRETE_BORDERS = frozenset({"api", "llm", "channel", "clock", "audit", "ingest", "synth", "evals", "store"})
EFFECTFUL_STDLIB = frozenset({"socket", "ssl", "http", "urllib", "sqlite3", "subprocess", "smtplib"})
THIRD_PARTY_ALLOWED: dict[str, frozenset[str]] = {
    "domain": frozenset({"pydantic"}),
    "rules": frozenset({"pydantic", "yaml"}),
    "solver": frozenset({"pydantic", "ortools"}),
    "verifier": frozenset({"pydantic"}),
}
DYNAMIC_IMPORTERS = frozenset({"import_module", "__import__"})


@dataclass(frozen=True)
class Violation:
    path: Path
    line: int
    imported: str
    rule: str


def _resolve_relative(module: str, is_package: bool, level: int, name: str | None) -> str:
    """Resolve `from <.>* name import ...` para o nome absoluto."""
    parts = module.split(".")
    base = parts if is_package else parts[:-1]
    if level > 1:
        base = base[: len(base) - (level - 1)]
    return ".".join([*base, *([name] if name else [])])


def _imports(module: str, tree: ast.AST, is_package: bool) -> list[tuple[int, str | None]]:
    """Lista (linha, módulo absoluto). `None` marca import dinâmico que não dá para resolver."""
    found: list[tuple[int, str | None]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found += [(node.lineno, alias.name) for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            base = _resolve_relative(module, is_package, node.level, node.module) if node.level else node.module or ""
            if base == ROOT:  # `from escalista import solver` importa o pacote `escalista.solver`
                found += [(node.lineno, f"{base}.{a.name}") for a in node.names]
            else:
                found.append((node.lineno, base))
        elif isinstance(node, ast.Call):
            func = node.func
            fname = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", None)
            if fname in DYNAMIC_IMPORTERS:
                arg = node.args[0] if node.args else None
                literal = arg.value if isinstance(arg, ast.Constant) and isinstance(arg.value, str) else None
                found.append((node.lineno, literal))
    return found


def _top(name: str) -> str:
    return name.split(".")[0]


def _violated_rule(pkg: str, imported: str | None) -> str | None:
    """Devolve a regra violada pelo import (ou `None`). `imported=None` é import dinâmico sem literal."""
    if imported is None:
        return "import dinâmico não verificável no núcleo" if pkg in CORE_PACKAGES else None
    root = _top(imported)
    target = imported.split(".")[1] if root == ROOT and "." in imported else None
    if pkg == AGENTS_PKG:
        return "agents não importa borda concreta; use as portas de domain" if target in CONCRETE_BORDERS else None
    if root == ROOT:
        if target is None or target in {"domain", pkg}:
            return None
        if (pkg, target) == ("verifier", "solver"):
            return "RF-02: verifier não importa solver"
        return f"núcleo ({pkg}) só importa domain e o próprio pacote"
    if root in sys.stdlib_module_names:
        return f"stdlib com efeito ({root}) fora do núcleo puro" if root in EFFECTFUL_STDLIB else None
    if root in THIRD_PARTY_ALLOWED[pkg]:
        return None
    if (pkg, root) == ("verifier", "ortools"):
        return "RF-02: verifier não importa OR-Tools"
    return f"biblioteca não permitida no núcleo ({pkg})"


def check_source(module: str, source: str, *, is_package: bool = False) -> list[Violation]:
    """Confere um arquivo. `module` é o nome pontilhado (ex.: `escalista.verifier.check`)."""
    parts = module.split(".")
    pkg = parts[1] if len(parts) > 1 and parts[0] == ROOT else None
    path = Path(*parts)
    if pkg not in (*CORE_PACKAGES, AGENTS_PKG):
        return []
    out: list[Violation] = []
    for line, imported in _imports(module, ast.parse(source), is_package):
        rule = _violated_rule(pkg, imported)
        if rule is not None:
            out.append(Violation(path, line, imported or "<dinâmico>", rule))
    return out


def check_tree(package_root: Path) -> list[Violation]:
    """Confere `src/escalista`. Falha também se um pacote do núcleo faltar ou estiver vazio (falso negativo)."""
    violations: list[Violation] = []
    for name in (*CORE_PACKAGES, AGENTS_PKG):
        files = sorted((package_root / name).rglob("*.py")) if (package_root / name).is_dir() else []
        if not files:
            violations.append(
                Violation(package_root / name, 0, name, "pacote ausente ou vazio: a varredura não testaria nada")
            )
            continue
        for file in files:
            rel = file.relative_to(package_root.parent).with_suffix("")
            is_package = rel.name == "__init__"
            module = ".".join(rel.parent.parts if is_package else rel.parts)
            for v in check_source(module, file.read_text(encoding="utf-8"), is_package=is_package):
                violations.append(Violation(file, v.line, v.imported, v.rule))
    return violations
