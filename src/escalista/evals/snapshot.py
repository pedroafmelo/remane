"""Retrato do relatório `all` para o link público (E6): `data/evals/evals-latest.json`.

`var/` não vai à imagem; o retrato é commitado e a rota `GET /api/evals` o lê. Antes de gravar, o relatório é conferido
contra os valores plantados nos atestados sintéticos (`planted_cid` dos `*.esperado.json`): se algum aparecer, nada é
gravado. O vazamento é dito pelo **caminho JSON** onde está, nunca pelo valor.

Se `escalista.audit.protected.find_leaks` existir (C7), ele decide; senão vale a busca local (texto contido, sem
diferenciar maiúsculas). Sem arquivos de gabarito não há o que conferir: `planted_checked == 0` e o retrato diz isso em
`privacidade`.
"""

from __future__ import annotations

import importlib
import json
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SNAPSHOT_NAME = "evals-latest.json"
PLANTED_DIR = Path("demo") / "acompanhamento" / "atestados"
NO_PLANTED_NOTE = "sem valores plantados disponíveis"
KEY_PLACEHOLDER = "<chave>"


@dataclass(frozen=True)
class LeakCheck:
    leaks: list[str]  # caminhos JSON, nunca valores
    planted_checked: int  # quantos valores plantados foram procurados
    source: str = "busca local"


class SnapshotLeakError(RuntimeError):
    def __init__(self, leaks: list[str]):
        super().__init__(f"o relatório carrega valor plantado em: {', '.join(leaks)}")
        self.leaks = leaks


def planted_values(data_dir: Path) -> list[str]:
    """Valores `planted_cid` (texto ou lista, em qualquer nível) dos gabaritos de atestado; vazio sem a pasta."""
    values: list[str] = []
    for path in sorted((data_dir / PLANTED_DIR).glob("*.esperado.json")):
        try:
            body = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        values.extend(_find_key(body, "planted_cid"))
    return list(dict.fromkeys(v for v in values if v))


def _find_key(node: Any, key: str) -> Iterator[str]:
    if isinstance(node, dict):
        for k, v in node.items():
            if k == key:
                items = v if isinstance(v, list) else [v]
                yield from (str(i) for i in items if isinstance(i, str | int | float))
            else:
                yield from _find_key(v, key)
    elif isinstance(node, list):
        for item in node:
            yield from _find_key(item, key)


def _leak_paths(node: Any, hit: Callable[[str], bool], path: str = "") -> Iterator[str]:
    """Caminhos das folhas e chaves em que `hit` acusa valor plantado. Uma chave que acusa vira `<chave>` no caminho."""
    if isinstance(node, dict):
        for k, v in node.items():
            bad_key = hit(str(k))
            joined = f"{path}.{KEY_PLACEHOLDER if bad_key else k}"
            if bad_key:
                yield joined.lstrip(".")
            yield from _leak_paths(v, hit, joined)
    elif isinstance(node, list):
        for i, item in enumerate(node):
            yield from _leak_paths(item, hit, f"{path}[{i}]")
    elif node is not None and hit(str(node)):
        yield path.lstrip(".")


def _external_find_leaks() -> Callable[..., Any] | None:
    try:
        return getattr(importlib.import_module("escalista.audit.protected"), "find_leaks", None)
    except ImportError:
        return None


def check_no_leaks(report: dict[str, Any], data_dir: Path) -> LeakCheck:
    planted = planted_values(data_dir)
    if not planted:
        return LeakCheck(leaks=[], planted_checked=0)
    external = _external_find_leaks()
    state = {"source": "busca local"}

    def hit(text: str) -> bool:
        if external is not None:
            try:
                found = bool(external(text, planted))
                state["source"] = "escalista.audit.protected.find_leaks"
                return found
            except TypeError:  # assinatura diferente da esperada: a busca local segue valendo
                pass
        lowered = text.lower()
        return any(p.lower() in lowered for p in planted)

    leaks = list(dict.fromkeys(_leak_paths(report, hit)))
    return LeakCheck(leaks=leaks, planted_checked=len(planted), source=state["source"])


def write_snapshot(report: dict[str, Any], out_dir: Path, data_dir: Path) -> LeakCheck:
    """Grava `out_dir/evals-latest.json`, ou levanta `SnapshotLeakError` sem gravar nada."""
    check = check_no_leaks(report, data_dir)
    if check.leaks:
        raise SnapshotLeakError(check.leaks)
    note = (
        f"conferido contra {check.planted_checked} valor(es) plantado(s): nenhum no relatório"
        if check.planted_checked
        else NO_PLANTED_NOTE
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    body = {**report, "privacidade": note}
    (out_dir / SNAPSHOT_NAME).write_text(json.dumps(body, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return check
