"""Monta e grava os arquivos de `data/demo/` (plano da C5, seção 4, D2). Determinístico por seed."""

from __future__ import annotations

import csv
import io
import json
import random
from pathlib import Path

from pydantic import TypeAdapter

from escalista.domain.schedule import DemandSlot, Employee, Shift, Store
from escalista.synth.demanda import make_demanda
from escalista.synth.escalas import PLANTADAS, escala_atual, escala_base, escala_violacoes
from escalista.synth.rede import SEMANA_INICIO, make_rede

CABECALHO_CSV = ["loja_id", "pessoa_id", "nome", "data", "inicio", "fim"]
MARCA = "# SINTETICO - dados ficticios"
FIM_DA_SEMANA = SEMANA_INICIO.toordinal() + 6


def _csv(linhas: list[list[str]]) -> str:
    """CSV longo (DEC-039): marca, cabeçalho e uma linha por turno."""
    buffer = io.StringIO()
    buffer.write(MARCA + "\n")
    escritor = csv.writer(buffer, lineterminator="\n")
    escritor.writerow(CABECALHO_CSV)
    escritor.writerows(linhas)
    return buffer.getvalue()


def _linha(turno: Shift, nomes: dict[str, str]) -> list[str]:
    return [
        turno.store_id,
        turno.employee_id,
        nomes[turno.employee_id],
        turno.start.date().isoformat(),
        turno.start.strftime("%H:%M"),
        turno.end.strftime("%H:%M"),
    ]


def _ordenar(turnos: list[Shift]) -> list[Shift]:
    return sorted(turnos, key=lambda t: (t.store_id, t.employee_id, t.start))


def _json(itens: list, tipo) -> str:  # noqa: ANN001 - TypeAdapter de contratos pydantic
    return TypeAdapter(tipo).dump_json(itens, indent=2).decode("utf-8") + "\n"


def _defeitos(turnos: list[Shift], nomes: dict[str, str]) -> tuple[str, str]:
    """Cinco defeitos de leitura, um de cada tipo. Devolve (CSV, JSON com as linhas físicas plantadas).

    A linha 1 é a marca e a linha 2 o cabeçalho, então a linha física do item `k` da lista é `k + 3`.
    """
    base: list[tuple[list[str], tuple[str, str] | None]] = [(_linha(t, nomes), None) for t in _ordenar(turnos)]

    def primeira(pessoa_id: str) -> int:
        return next(i for i, (campos, _) in enumerate(base) if campos[1] == pessoa_id)

    i = primeira("P010")  # hora em formato inválido
    campos = base[i][0]
    base[i] = ([*campos[:4], "25:70", campos[5]], ("inicio", "hora inválida em inicio: '25:70' (esperado HH:MM)"))

    i = primeira("P011")  # pessoa que não está em pessoas.json
    campos = base[i][0]
    base[i] = (
        [campos[0], "P999", "Pessoa Desconhecida (sintético)", *campos[3:]],
        ("pessoa_id", "pessoa_id 'P999' não existe em pessoas.json"),
    )

    i = primeira("P012")  # sobreposição: a linha inserida logo depois da original, na mesma data
    original = base[i][0]
    linha_original = i + 3
    base.insert(
        i + 1,
        (
            [*original[:4], "10:00", "16:00"],
            ("inicio", f"turno sobreposto ao da linha {linha_original}, mesma pessoa e mesma data"),
        ),
    )

    i = primeira("P013")  # data fora da semana
    campos = base[i][0]
    base[i] = (
        [campos[0], campos[1], campos[2], "2027-01-25", *campos[4:]],
        ("data", "data 2027-01-25 fora da semana de 11/01 a 17/01/2027"),
    )

    i = primeira("P014")  # campo obrigatório vazio
    campos = base[i][0]
    base[i] = ([*campos[:5], ""], ("fim", "campo obrigatório vazio: fim"))

    linhas: list[list[str]] = []
    plantados: list[dict] = []
    for posicao, (campos, defeito) in enumerate(base):
        linhas.append(campos)
        if defeito is not None:
            campo, motivo = defeito
            plantados.append({"line": posicao + 3, "field": campo, "reason": motivo})
    return _csv(linhas), json.dumps(plantados, ensure_ascii=False, indent=2) + "\n"


def gerar(seed: int) -> dict[str, str]:
    """Todos os arquivos de `data/demo/`, como texto, a partir da seed. Não grava nada."""
    rng = random.Random(seed)
    lojas, pessoas = make_rede(rng)
    demanda = make_demanda(rng, lojas)
    base = escala_base(rng, pessoas)
    atual = escala_atual(rng, pessoas)
    violacoes = escala_violacoes(base, pessoas)
    nomes = {p.id: p.name for p in pessoas}

    arquivos = {
        "lojas.json": _json(lojas, list[Store]),
        "pessoas.json": _json(pessoas, list[Employee]),
        "demanda.json": _json(demanda, list[DemandSlot]),
        "escala_atual.csv": _csv([_linha(t, nomes) for t in _ordenar(atual)]),
        "escala_violacoes.csv": _csv([_linha(t, nomes) for t in _ordenar(violacoes)]),
        "violacoes_plantadas.json": json.dumps(
            [
                {"rule_id": regra, "kind": regra, "employee_id": pessoa, "day": dia.isoformat() if dia else None}
                for regra, pessoa, dia in PLANTADAS
            ],
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
    }
    defeito_csv, defeitos_json = _defeitos(sum(base.values(), []), nomes)
    arquivos["escala_defeito.csv"] = defeito_csv
    arquivos["defeitos_plantados.json"] = defeitos_json
    return arquivos


def escrever(arquivos: dict[str, str], out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    for nome, conteudo in arquivos.items():
        (out / nome).write_bytes(conteudo.encode("utf-8"))
