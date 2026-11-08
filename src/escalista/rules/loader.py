"""Carregador das camadas de regras (`lei/`, `convencao/`, `politica/`): YAML → `Rule` (plano da C5, A1).

`parse_layer` é pura (texto entra, regras saem). `load_rule_card` é a casca fina que lê `data/regras/` e chama a fusão.

Formato normalizado de `kind` e `params` (o que solver, verificador e custo leem):

| `kind`                 | campo pelo `id`  | campo pelo alvo | `params`          | "mais restritivo"       |
|------------------------|------------------|-----------------|-------------------|-------------------------|
| `jornada_semanal_max`  | `horas`          | `horas`         | `{"hours": 42}`   | menor                   |
| `jornada_diaria_max`   | `horas`          | `horas`         | `{"hours": 8}`    | menor                   |
| `interjornada_min`     | `horas`          | `horas`         | `{"hours": 11}`   | maior                   |
| `repouso_semanal`      | `dias`           | `dias`          | `{"days": 2}`     | maior (dias por semana) |
| `adicional_hora_extra` | `percentual_min` | `percentual`    | `{"percent": 60}` | maior (mais protetivo)  |

Uma regra vira primitiva de dois jeitos:

- **pelo `id`**: o `id` é o nome da primitiva (como em `lei/`); o campo é o da coluna "pelo `id`" e é obrigatório;
- **pelo alvo**: `restringe: <primitiva>` (formato da convenção e da política fictícias de Pedro Veloso); o `id` da
  regra é mantido e o campo é o da coluna "pelo alvo" (ou o "pelo `id`"). Sem um desses campos, a regra fica `info`:
  o carregador não inventa valor. Quem decide qual valor vale entre as camadas é a fusão (`merge.py`).

`amplia: <primitiva>` **não** vira primitiva: fica `info`. A fusão trataria a ampliação como camada "mais frouxa" e
abriria um RX-01 espúrio, embora a EC 141 (art. 7º) a permita. Por isso a ampliação diária da convenção fictícia
(`cct_jornada_diaria_ampliada`, 9h a partir de 16/12/2026) ainda não alimenta o motor; a fatia não precisa dela
(5 × 8h = 40h < 42h).

Os valores saem como vieram do YAML (`int` ou `float`). Qualquer outra regra (inclusive `restringe` para algo fora das
5 primitivas, e todo `amplia`), e toda entrada de `excecoes:`, vira `kind="info"`, mantendo o status; seus `params`
são os campos restantes do YAML, crus (sem `id`, `fonte`, `status`, `nota`, `acao`, `verificacao` e vigência).
`acao` (`escalar` ou `verificar_convencao`) vai para `Rule.action`. Campos extras de uma primitiva (por exemplo
`percentual_domingo_feriado`) não entram em `params`: só o valor da primitiva alimenta solver, verificador e custo.

Vigência: `vigencia` (ou `de`) é `valid_from`; `ate` é `valid_to`. Uma regra com `valores: [{de, ate, <campo>}, ...]`
vira uma `Rule` por período, com o mesmo `id`; um período sem `ate` termina na véspera do `de` seguinte.
"""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
from typing import Any

import yaml

from escalista.domain.rules import Rule, RuleCard, RuleLayer, RuleStatus
from escalista.rules.merge import PRIMITIVES, build_card

# Campo do YAML que dá o valor de cada primitiva; a chave em `params` e o sentido ficam em `merge.PRIMITIVES`.
YAML_FIELDS: dict[str, str] = {
    "jornada_semanal_max": "horas",
    "jornada_diaria_max": "horas",
    "interjornada_min": "horas",
    "repouso_semanal": "dias",
    "adicional_hora_extra": "percentual_min",
}
# Campo aceito quando a regra aponta para a primitiva por `restringe:` (formato de Pedro Veloso). `amplia:` fica `info`.
TARGET_FIELDS: dict[str, tuple[str, ...]] = {
    "jornada_semanal_max": ("horas",),
    "jornada_diaria_max": ("horas",),
    "interjornada_min": ("horas",),
    "repouso_semanal": ("dias",),
    "adicional_hora_extra": ("percentual", "percentual_min"),
}
TARGET_KEY = "restringe"
INFO = "info"
SECTIONS = ("regras", "excecoes")
ACTIONS = ("escalar", "verificar_convencao")
REQUIRED = ("id", "fonte", "status")
META_FIELDS = frozenset({"id", "fonte", "status", "nota", "acao", "verificacao", "valores", "vigencia", "de", "ate"})


class RuleFileError(ValueError):
    """Arquivo de regras inválido. A mensagem cita o arquivo e o campo."""

    def __init__(self, file_name: str, field: str | None, message: str) -> None:
        self.file_name = file_name
        self.field = field
        where = f"campo '{field}'" if field else "arquivo"
        super().__init__(f"{file_name}: {where}: {message}")


def parse_layer(text: str, layer: RuleLayer, file_name: str) -> list[Rule]:
    """Lê um arquivo YAML de uma camada e devolve suas regras (sem fundir nem filtrar por data). Sem efeito."""
    try:
        doc = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise RuleFileError(file_name, None, f"YAML inválido ({exc.__class__.__name__})") from exc
    if doc is None:
        return []
    if not isinstance(doc, dict):
        raise RuleFileError(file_name, None, "a raiz precisa ser um mapa com 'regras' e 'excecoes'")

    rules: list[Rule] = []
    for section in SECTIONS:
        entries = doc.get(section) or []
        if not isinstance(entries, list):
            raise RuleFileError(file_name, section, "precisa ser uma lista")
        for index, raw in enumerate(entries, start=1):
            where = f"{section}[{index}]"
            if not isinstance(raw, dict):
                raise RuleFileError(file_name, section, f"{where} precisa ser um mapa")
            rules += _parse_entry(raw, layer, file_name, where, is_exception=section == "excecoes")
    return rules


def _parse_entry(
    raw: dict[str, Any], layer: RuleLayer, file_name: str, where: str, *, is_exception: bool
) -> list[Rule]:
    for field in REQUIRED:
        if raw.get(field) in (None, ""):
            raise RuleFileError(file_name, field, f"{where} ({raw.get('id', 'sem id')}) sem '{field}'")
    rule_id = str(raw["id"])
    where = f"{where} ({rule_id})"

    try:
        status = RuleStatus(raw["status"])
    except ValueError as exc:
        allowed = ", ".join(s.value for s in RuleStatus)
        raise RuleFileError(file_name, "status", f"{where}: '{raw['status']}' fora de {allowed}") from exc
    if status is RuleStatus.FICTICIA and layer is RuleLayer.LEI:
        raise RuleFileError(file_name, "status", f"{where}: 'ficticia' só vale em convencao/ e politica/")

    action = raw.get("acao")
    if action is not None and action not in ACTIONS:
        raise RuleFileError(file_name, "acao", f"{where}: '{action}' fora de {', '.join(ACTIONS)}")

    kind, field = _kind_and_field(raw, rule_id, is_exception=is_exception)
    base = {
        "id": rule_id,
        "kind": kind,
        "layer": layer,
        "status": status,
        "source": str(raw["fonte"]),
        "action": action,
        "note": _text(raw.get("nota")),
    }
    rule_from = _date(raw.get("vigencia", raw.get("de")), file_name, "vigencia", where)
    rule_to = _date(raw.get("ate"), file_name, "ate", where)

    periods = raw.get("valores")
    if periods is None:
        params = _params(raw, kind, field, file_name, where)
        return [Rule(**base, params=params, valid_from=rule_from, valid_to=rule_to)]
    if not isinstance(periods, list) or not all(isinstance(p, dict) for p in periods) or not periods:
        raise RuleFileError(file_name, "valores", f"{where}: precisa ser uma lista de mapas com 'de'/'ate'")

    starts = [_date(p.get("de"), file_name, "valores.de", where) for p in periods]
    out: list[Rule] = []
    for i, period in enumerate(periods):
        valid_to = _date(period.get("ate"), file_name, "valores.ate", where)
        if valid_to is None and i + 1 < len(periods) and starts[i + 1] is not None:
            valid_to = starts[i + 1] - timedelta(days=1)
        params = _params({**raw, **period}, kind, field, file_name, where)
        out.append(Rule(**base, params=params, valid_from=starts[i] or rule_from, valid_to=valid_to or rule_to))
    return out


def _kind_and_field(raw: dict[str, Any], rule_id: str, *, is_exception: bool) -> tuple[str, str | None]:
    """`(kind, campo do valor)`: pelo `id` exato, pelo alvo de `restringe` com campo conhecido, ou `info`."""
    if is_exception:
        return INFO, None
    if rule_id in PRIMITIVES:
        return rule_id, YAML_FIELDS[rule_id]
    target = raw.get(TARGET_KEY)
    if not isinstance(target, str) or target not in PRIMITIVES:
        return INFO, None
    sources = [*raw, *(k for p in raw.get("valores") or [] if isinstance(p, dict) for k in p)]
    field = next((f for f in TARGET_FIELDS[target] if f in sources), None)
    return (target, field) if field else (INFO, None)


def _params(raw: dict[str, Any], kind: str, field: str | None, file_name: str, where: str) -> dict[str, Any]:
    if kind == INFO or field is None:
        return {k: v for k, v in raw.items() if k not in META_FIELDS}
    value = raw.get(field)
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise RuleFileError(file_name, field, f"{where}: precisa de um número")
    return {PRIMITIVES[kind].param: value}


def _date(value: Any, file_name: str, field: str, where: str) -> date | None:
    if value is None or isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value))
    except ValueError as exc:
        raise RuleFileError(file_name, field, f"{where}: data inválida '{value}' (use AAAA-MM-DD)") from exc


def _text(value: Any) -> str | None:
    return None if value is None else str(value).strip()


def load_rule_card(base_dir: Path, reference_date: date) -> RuleCard:
    """Lê `lei/`, `convencao/` e `politica/` sob `base_dir` (arquivos `*.yaml`, em ordem alfabética) e funde.

    `lei/` precisa ter ao menos um arquivo; as outras camadas são opcionais.
    """
    rules: list[Rule] = []
    for layer in RuleLayer:
        folder = Path(base_dir) / layer.value
        files = sorted(folder.glob("*.yaml")) if folder.is_dir() else []
        if layer is RuleLayer.LEI and not files:
            raise RuleFileError(f"{layer.value}/", None, "nenhum arquivo .yaml de lei encontrado")
        for file in files:
            rules += parse_layer(file.read_text(encoding="utf-8"), layer, f"{layer.value}/{file.name}")
    return build_card(rules, reference_date)
