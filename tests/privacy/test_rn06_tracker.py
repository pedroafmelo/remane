"""Teste de vazamento RN-06 do acompanhamento (C7, tarefa D3; SAIDA-AC-13 v1.1 e SAIDA-AC-14).

Roda o roteiro da demo pela API (`TestClient`, SQLite em arquivo temporário, `DEMO_MODE` ligado, modelo falso; nunca
o real) com atestados SINTÉTICOS que trazem CID fictício plantado (`at-09` com `J11` e `J11.1`; `at-01` com `A09`) e
com texto livre plantado no aviso, e procura esses valores em todas as superfícies:

- `db:<tabela>`: todas as colunas de todas as linhas de cada tabela do SQLite (inclusive `trace_event`);
- `db:arquivo`: os bytes crus do arquivo do banco (pega também linha apagada que ficou nas páginas livres);
- `trace:track`: só os eventos `track.*` (`kind` e `payload`), onde o padrão de CID também vale;
- `log` (log do processo em DEBUG na raiz), `stdout` e `stderr`;
- `http:<método> <rota>`: o corpo de cada resposta do roteiro (inclusive a rota de rastro do gestor);
- `llm:read_atestado`: tudo o que foi enviado ao modelo falso (no caminho PDF o CID sai antes do modelo).

Foto do atestado (C7 T2): a imagem vai ao modelo (DEC-020 permite), então ali ela **deve** aparecer (controle positivo)
e em todas as outras superfícies não pode aparecer nem em bytes crus nem em base64 (SAIDA-AC-14, superfícies 1 a 4). A
foto entra pela rota de anexo (`image/png` no corpo bruto), como no celular simulado.

`find_leaks` devolve só a superfície e o tipo; a mensagem de falha nunca imprime o valor plantado.

Ids determinísticos, só com dígitos: `find_leaks` compara sem caixa, e `A09` casaria `a09` dentro de um id hexadecimal
aleatório (`uuid4().hex`), um falso positivo intermitente. Trocar o `uuid4` por um contador sem letras elimina isso sem
mudar o que o sistema grava.
"""

from __future__ import annotations

import base64
import io
import itertools
import json
import logging
import os
import sys
import tempfile
import uuid
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

import escalista.api.tracker_wiring  # noqa: F401 (importado antes da troca do `uuid4`; ver `digit_only_ids`)
from escalista.api.app import create_app
from escalista.api.fake_agent import FakeSliceAgent
from escalista.audit.protected import CID_REMOVED, Leak, find_leaks
from escalista.config import Settings
from escalista.domain.contracts import ImagePart, LLMMessage
from escalista.ingest.atestado import pdf_text
from tests.fakes import TOOL_ATESTADO, FakeLLMClient

ATESTADOS = Path("data/demo/acompanhamento/atestados")
USED = ("at-09-cid-espalhado", "at-01-legivel")  # na ordem do anexo
THURSDAY = "2027-01-14"
FREE_TEXT = "dor forte CID J11 diagnóstico gripe"  # mandado no JSON do aviso; o servidor deve ignorar
FREE_TEXT_PLANTED = ["dor forte", "gripe"]
READING = {
    "legible": True,
    "issued_on": "2027-01-13",
    "start_on": THURSDAY,
    "days": 3,
    "patient_matches": True,
    "has_crm": True,
}
# Modelo "malicioso": tenta devolver o CID e o texto livre nos campos. O schema é fechado (sem campo de texto, extra
# proibido), então cada resposta é recusada; três por anexo (1 chamada e 2 reenvios), depois RX-12. O primeiro usa o
# CID como nome de campo extra: o motivo do reenvio não pode ecoá-lo ao modelo (`llm.structured._describe`).
MALICIOUS = [
    {**READING, "J11": "dor forte, CID A09"},
    {**READING, "issued_on": "J11.1"},
    {**READING, "cid": "J11", "diagnostico": "gripe"},
]
PATTERN_SURFACES = {"db:track_case", "db:channel_message", "llm:read_atestado", "trace:track"}


def planted_values() -> list[str]:
    planted: list[str] = []
    for stem in USED:
        expected = json.loads((ATESTADOS / f"{stem}.esperado.json").read_text(encoding="utf-8"))
        planted += expected["planted_cid"]
    return [*planted, *FREE_TEXT_PLANTED]


# --- ambiente --------------------------------------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for name in ("DEMO_MODE", "SESSION_SECRET", "DATABASE_URL", "WEB_DIST_DIR"):
        monkeypatch.delenv(name, raising=False)


@pytest.fixture(autouse=True)
def digit_only_ids(monkeypatch):
    """`uuid4` vira um contador só com dígitos (ver docstring do módulo). Os 12 primeiros caracteres variam, porque há
    ids feitos de `uuid4().hex[:12]`. Na saída, desfaz também a troca em módulo importado durante o teste."""
    real = uuid.uuid4
    counter = itertools.count(1)

    def fake_uuid4() -> uuid.UUID:
        n = next(counter)
        return uuid.UUID(hex=f"{n:012d}{n:020d}")

    monkeypatch.setattr(uuid, "uuid4", fake_uuid4)
    for name, module in list(sys.modules.items()):
        if name.startswith("escalista") and getattr(module, "uuid4", None) is real:
            monkeypatch.setattr(module, "uuid4", fake_uuid4)
    yield
    for name, module in list(sys.modules.items()):
        if name.startswith("escalista") and getattr(module, "uuid4", None) is fake_uuid4:
            module.uuid4 = real


class Recorder:
    """`TestClient` que guarda o corpo de cada resposta como superfície `http:<método> <rota>`."""

    def __init__(self, client: TestClient) -> None:
        self.client = client
        self.bodies: dict[str, str] = {}
        self._seen: Counter[str] = Counter()

    def call(self, method: str, path: str, **kwargs: Any):  # noqa: ANN201
        response = self.client.request(method, path, **kwargs)
        key = f"http:{method} {path}"
        self._seen[key] += 1
        if self._seen[key] > 1:
            key = f"{key} #{self._seen[key]}"
        self.bodies[key] = response.text
        return response

    def login(self, role: str) -> None:
        assert self.call("POST", f"/auth/demo/{role}").status_code == 200


def make_api(tmp_path: Path, llm: FakeLLMClient) -> Recorder:
    settings = Settings(
        _env_file=None,
        database_url=f"sqlite:///{tmp_path}/app.db",
        web_dist_dir=str(tmp_path / "dist"),
        demo_mode=True,
        session_secret="segredo-de-teste",
    )
    return Recorder(TestClient(create_app(settings, agent=FakeSliceAgent(), tracker_llm=llm)))


# --- roteiro ---------------------------------------------------------------------------------------------------------


def report_and_attach(api: Recorder) -> list[dict]:
    """Reset, aviso da Ana (P101) com o texto livre plantado no JSON e os dois atestados no corpo bruto."""
    api.login("gestor")
    assert api.call("POST", "/api/demo/reset").status_code == 200
    api.login("colaborador")
    case = api.call(
        "POST",
        "/api/colaborador/aviso",
        json={"as": "P101", "day": THURSDAY, "kind": "falta", "has_text": True, "text": FREE_TEXT},
    )
    assert case.status_code == 200, case.status_code
    case_id = case.json()["case_id"]
    attached = []
    for stem in USED:
        response = api.call(
            "POST",
            f"/api/colaborador/caso/{case_id}/anexo",
            params={"as": "P101", "file_name": f"{stem}.pdf"},
            content=(ATESTADOS / f"{stem}.pdf").read_bytes(),
            headers={"Content-Type": "application/pdf"},
        )
        assert response.status_code == 200, response.status_code
        attached.append(response.json())
    return attached


def run_script(api: Recorder) -> tuple[str, list[dict]]:
    """O roteiro inteiro: aviso e anexos, aceite de P105, gestor decide a COBERTURA, +15 min e todas as leituras."""
    attached = report_and_attach(api)
    case_id = attached[0]["case_id"]

    box = api.call("GET", "/api/colaborador/caixa", params={"as": "P105"}).json()
    offer = box["offers"][0]
    accepted = api.call("POST", f"/api/colaborador/oferta/{offer['offer_id']}", json={"as": "P105", "accept": True})
    assert accepted.status_code == 200

    api.login("gestor")
    queue = api.call("GET", "/api/exceptions").json()
    item = next(i for i in queue["open"] if i["card"]["code"] == "COBERTURA")
    assert api.call("POST", f"/api/exceptions/{item['id']}/decide", json={"option_index": 0}).status_code == 200
    assert api.call("POST", "/api/demo/clock/advance", json={"minutes": 15}).status_code == 200

    # leituras do gestor: fila, relógio, rastro (a rota de rastro é do agente da fatia: para `track-*` responde 404,
    # e o corpo entra na varredura do mesmo jeito), impacto (lê `trace_event`), escala publicada e o próprio usuário
    api.call("GET", "/api/exceptions")
    api.call("GET", "/api/demo/clock")
    api.call("GET", f"/api/runs/track-{case_id}/trace")
    api.call("GET", "/api/runs/track-sweep/trace")
    api.call("GET", "/api/impact")
    api.call("GET", "/api/schedules/published")
    api.call("GET", "/api/me")

    api.login("colaborador")
    api.call("GET", "/api/colaborador/pessoas")
    for person in ("P101", "P105"):
        api.call("GET", "/api/colaborador/caixa", params={"as": person})
    api.call("GET", "/api/colaborador/escala")
    api.call("GET", "/api/demo/clock")
    return case_id, attached


# --- superfícies -----------------------------------------------------------------------------------------------------


def db_surfaces(engine: Engine, db_file: Path) -> dict[str, str]:
    blobs: dict[str, str] = {}
    with engine.connect() as conn:
        for table in inspect(engine).get_table_names():
            rows = conn.execute(text(f'SELECT * FROM "{table}"')).all()
            blobs[f"db:{table}"] = "\n".join(" | ".join(str(value) for value in row) for row in rows)
        track = conn.execute(text("SELECT kind, payload FROM trace_event WHERE kind LIKE 'track.%'")).all()
    blobs["trace:track"] = "\n".join(f"{kind} {payload}" for kind, payload in track)
    raw = b"".join(p.read_bytes() for p in sorted(db_file.parent.glob(f"{db_file.name}*")))
    blobs["db:arquivo"] = raw.decode("latin-1")
    return blobs


def llm_surface(llm: FakeLLMClient) -> str:
    return "\n".join(
        message.content for call in llm.calls if call["tool_name"] == TOOL_ATESTADO for message in call["messages"]
    )


def all_surfaces(api: Recorder, llm: FakeLLMClient, tmp_path: Path, caplog, capsys) -> dict[str, str]:
    captured = capsys.readouterr()
    return {
        **db_surfaces(api.client.app.state.engine, tmp_path / "app.db"),
        "log": caplog.text,
        "stdout": captured.out,
        "stderr": captured.err,
        **api.bodies,
        "llm:read_atestado": llm_surface(llm),
    }


def describe(leaks: list[Leak]) -> str:
    """Só superfície e tipo, nunca o valor."""
    return ", ".join(f"{leak.surface} ({leak.kind})" for leak in leaks)


def assert_no_leaks(blobs: dict[str, str]) -> None:
    leaks = find_leaks(blobs, planted_values(), pattern_surfaces=PATTERN_SURFACES)
    assert leaks == [], f"vazamento RN-06 em: {describe(leaks)}"


# --- testes ----------------------------------------------------------------------------------------------------------


def test_planted_values_are_really_in_the_inputs():
    """Controle positivo: os atestados trazem mesmo os CIDs dos gabaritos (senão o teste de vazamento seria vazio)."""
    for stem in USED:
        expected = json.loads((ATESTADOS / f"{stem}.esperado.json").read_text(encoding="utf-8"))
        raw = pdf_text((ATESTADOS / f"{stem}.pdf").read_bytes())
        assert raw is not None and expected["synthetic"] is True
        assert all(cid in raw for cid in expected["planted_cid"]), stem
    assert all(value in FREE_TEXT for value in FREE_TEXT_PLANTED)


def test_demo_script_leaks_no_cid_nor_free_text(tmp_path, caplog, capsys):
    caplog.set_level(logging.DEBUG)
    llm = FakeLLMClient(by_tool={TOOL_ATESTADO: [READING, READING]})
    api = make_api(tmp_path, llm)

    _, attached = run_script(api)

    assert [a["reading"]["verdict"] for a in attached] == ["valido", "valido"]
    blobs = all_surfaces(api, llm, tmp_path, caplog, capsys)
    assert_no_leaks(blobs)
    # controles positivos: o texto do PDF chegou ao modelo com o CID cortado, o log em DEBUG capturou algo e as
    # superfícies do acompanhamento não estão vazias. Booleanos antes do `assert`: a falha não imprime o conteúdo.
    assert sum(call["tool_name"] == TOOL_ATESTADO for call in llm.calls) == 2
    cid_was_cut = CID_REMOVED in blobs["llm:read_atestado"]
    assert cid_was_cut, "o texto do atestado não chegou ao modelo com o CID cortado"
    filled = all(blobs[name] for name in ("log", "trace:track", "db:channel_message", "db:track_case"))
    assert filled, "superfície do acompanhamento vazia: a varredura não teria o que olhar"
    assert len([k for k in blobs if k.startswith("http:")]) >= 20


def test_malicious_model_output_is_refused_and_leaks_nothing(tmp_path, caplog, capsys):
    """O modelo falso devolve o CID e o texto livre dentro dos argumentos. O schema fechado recusa tudo: a leitura
    fica indisponível (RX-12, abono provisório) e nada do que o modelo tentou chega a banco, log, rastro ou resposta."""
    caplog.set_level(logging.DEBUG)
    llm = FakeLLMClient(by_tool={TOOL_ATESTADO: MALICIOUS * 2})
    api = make_api(tmp_path, llm)

    case_id, attached = run_script(api)

    assert all(a["reading"] is None and a["abono"] == "provisorio" for a in attached)
    assert sum(call["tool_name"] == TOOL_ATESTADO for call in llm.calls) == 6  # 3 por anexo
    api.login("gestor")
    queue = api.call("GET", "/api/exceptions").json()
    assert any(
        i["card"]["code"] == "RX-12" and i["source"].get("case_id") == case_id for i in queue["open"] + queue["decided"]
    ), "a leitura recusada vira cartão RX-12 na fila"
    assert_no_leaks(all_surfaces(api, llm, tmp_path, caplog, capsys))


def _pdf_files_under(root: Path, names: set[str]) -> list[Path]:
    """Dos `names` novos em `root`, os arquivos (também dentro de pastas novas) cujo conteúdo começa com `%PDF`."""
    found: list[Path] = []
    for name in names:
        path = root / name
        candidates = [path] if path.is_file() else [Path(d) / f for d, _, fs in os.walk(path) for f in fs]
        for candidate in candidates:
            try:
                with candidate.open("rb") as handle:
                    head = handle.read(4)
            except OSError:  # arquivo de outro processo que sumiu ou não é nosso
                continue
            if head == b"%PDF":
                found.append(candidate)
    return found


def test_upload_keeps_the_pdf_in_memory(tmp_path, monkeypatch):
    """O anexo não vai a disco: nenhum arquivo PDF novo no diretório temporário do sistema e nenhuma chamada às
    funções de arquivo temporário do `tempfile` durante o upload. Tolerante a arquivos de outros processos."""
    llm = FakeLLMClient(by_tool={TOOL_ATESTADO: [READING, READING]})
    api = make_api(tmp_path, llm)
    temp_root = Path(tempfile.gettempdir())

    calls: list[str] = []
    for name in ("mkstemp", "mkdtemp", "NamedTemporaryFile", "TemporaryFile", "SpooledTemporaryFile"):
        original = getattr(tempfile, name)

        def spy(*args, _name=name, _original=original, **kwargs):  # noqa: ANN002, ANN003, ANN202
            calls.append(_name)
            return _original(*args, **kwargs)

        monkeypatch.setattr(tempfile, name, spy)

    before = set(os.listdir(temp_root))
    report_and_attach(api)
    new = set(os.listdir(temp_root)) - before

    assert _pdf_files_under(temp_root, new) == []
    assert calls == []


# --- foto do atestado (C7 T2) -----------------------------------------------------------------------------------------


def _photo() -> bytes:
    """Foto SINTÉTICA: ruído aleatório em PNG (Pillow, só dev); o ruído torna qualquer trecho inconfundível."""
    from PIL import Image

    buf = io.BytesIO()
    Image.frombytes("RGB", (64, 64), os.urandom(64 * 64 * 3)).save(buf, "PNG")
    return buf.getvalue()


def photo_planted(photo: bytes) -> list[str]:
    """Trechos da foto que não podem aparecer fora da mensagem ao modelo: base64 (começo e meio), bytes crus (latin-1,
    como `db:arquivo` é lido) e o prefixo do data URI."""
    b64 = base64.b64encode(photo).decode("ascii")
    raw = photo.decode("latin-1")
    middle, raw_middle = len(b64) // 2, len(raw) // 2
    return [b64[:64], b64[middle : middle + 64], raw[raw_middle : raw_middle + 32], "data:image/png;base64"]


def photo_script(api: Recorder, photo: bytes) -> str:
    """Reset, aviso da Ana (P101), a foto no corpo bruto da rota de anexo e as leituras do gestor e do colaborador."""
    api.login("gestor")
    assert api.call("POST", "/api/demo/reset").status_code == 200
    api.login("colaborador")
    case = api.call("POST", "/api/colaborador/aviso", json={"as": "P101", "day": THURSDAY, "kind": "falta"})
    assert case.status_code == 200, case.status_code
    case_id = case.json()["case_id"]
    response = api.call(
        "POST",
        f"/api/colaborador/caso/{case_id}/anexo",
        params={"as": "P101", "file_name": "foto.png"},
        content=photo,
        headers={"Content-Type": "image/png"},
    )
    assert response.status_code == 200, response.status_code
    api.call("GET", "/api/colaborador/caixa", params={"as": "P101"})
    api.login("gestor")
    api.call("GET", "/api/exceptions")
    api.call("GET", f"/api/runs/track-{case_id}/trace")
    api.call("GET", "/api/impact")
    return case_id


def _attach_body(api: Recorder) -> dict:
    key = next(k for k in api.bodies if k.startswith("http:POST /api/colaborador/caso/"))
    return json.loads(api.bodies[key])


def photo_surfaces(api: Recorder, tmp_path: Path, caplog, capsys) -> dict[str, str]:
    """Superfícies 1 a 4 da SAIDA-AC-14 (sem a mensagem ao modelo, onde a imagem pode estar)."""
    captured = capsys.readouterr()
    return {
        **db_surfaces(api.client.app.state.engine, tmp_path / "app.db"),
        "log": caplog.text,
        "stdout": captured.out,
        "stderr": captured.err,
        **api.bodies,
    }


def assert_photo_not_leaked(blobs: dict[str, str], photo: bytes) -> None:
    leaks = find_leaks(blobs, photo_planted(photo), pattern_surfaces=set())
    assert leaks == [], f"vazamento RN-06 da foto em: {describe(leaks)}"


def test_photo_goes_only_to_the_model(tmp_path, caplog, capsys):
    caplog.set_level(logging.DEBUG)
    photo = _photo()
    llm = FakeLLMClient(by_tool={TOOL_ATESTADO: [READING]})
    api = make_api(tmp_path, llm)

    photo_script(api, photo)

    assert _attach_body(api)["reading"]["verdict"] == "valido"
    images = [
        part
        for call in llm.calls
        if call["tool_name"] == TOOL_ATESTADO
        for message in call["messages"]
        if not isinstance(message.content, str)
        for part in message.content
        if isinstance(part, ImagePart)
    ]
    went_to_model = [part.data for part in images] == [photo]
    assert went_to_model, "a foto não chegou ao modelo (controle positivo)"
    assert_photo_not_leaked(photo_surfaces(api, tmp_path, caplog, capsys), photo)


class _LateClient:
    """Delegado: o app é montado antes do `FeatherlessClient`, que precisa do `engine` do app para o rastro."""

    target: Any = None

    def complete(self, **kwargs: Any) -> Any:
        return self.target.complete(**kwargs)


def test_photo_through_featherless_client_trace_keeps_only_size_and_type(tmp_path, caplog, capsys):
    """Com o cliente real (transporte falso, nunca a rede): o corpo enviado leva o data URI; o `trace_event`
    `track.llm.read_atestado` leva só `media_type` e tamanho; log do SDK em DEBUG, banco e respostas, nada da foto."""
    import httpx2
    from pydantic import SecretStr

    from escalista.audit.sink import SqlTraceSink
    from escalista.llm.client import FeatherlessClient, ModelChoice
    from escalista.llm.pool import KeyPool
    from tests.fakes import FixedClock

    caplog.set_level(logging.DEBUG)
    photo = _photo()
    bodies: list[str] = []

    def server(request: httpx2.Request) -> httpx2.Response:
        bodies.append(request.content.decode("utf-8"))
        call = {"id": "c1", "type": "function", "function": {"name": TOOL_ATESTADO, "arguments": json.dumps(READING)}}
        return httpx2.Response(
            200,
            json={
                "id": "cmpl-1",
                "object": "chat.completion",
                "created": 0,
                "model": "modelo/visao",
                "choices": [
                    {"index": 0, "message": {"role": "assistant", "content": None, "tool_calls": [call]},
                     "finish_reason": "tool_calls"}
                ],
                "usage": {"prompt_tokens": 900, "completion_tokens": 40, "total_tokens": 940, "cost": 0.0002},
            },
        )  # fmt: skip

    late = _LateClient()
    api = make_api(tmp_path, late)  # type: ignore[arg-type]
    late.target = FeatherlessClient(
        pool=KeyPool([(1, SecretStr("chave-de-teste"))], sleep=lambda _s: None),
        models={m: ModelChoice(f"modelo/{m}") for m in ("small", "large")} | {"vision": ModelChoice("modelo/visao")},
        trace_sink=SqlTraceSink(api.client.app.state.engine),
        clock=FixedClock(datetime(2027, 1, 13, 14, 0)),
        base_url="https://featherless.test/v1",
        http_client=httpx2.Client(transport=httpx2.MockTransport(server)),
    )

    photo_script(api, photo)

    assert _attach_body(api)["reading"]["verdict"] == "valido"
    data_uri = f"data:image/png;base64,{base64.b64encode(photo).decode('ascii')}"
    assert len(bodies) == 1 and data_uri in bodies[0], "a foto não chegou ao provedor (controle positivo)"
    detects = find_leaks({"provedor": bodies[0]}, photo_planted(photo), pattern_surfaces=set()) != []
    assert detects, "a varredura não reconhece a foto em base64 (controle positivo)"
    with api.client.app.state.engine.connect() as conn:
        rows = conn.execute(text("SELECT model, payload FROM trace_event WHERE kind = 'track.llm.read_atestado'")).all()
    assert [r.model for r in rows] == ["modelo/visao"]
    payload = rows[0].payload if isinstance(rows[0].payload, dict) else json.loads(rows[0].payload)
    assert payload["images"] == [{"media_type": "image/png", "bytes": len(photo)}]
    blobs = photo_surfaces(api, tmp_path, caplog, capsys)
    assert blobs["log"] and blobs["trace:track"], "superfície vazia: a varredura não teria o que olhar"
    assert_photo_not_leaked(blobs, photo)


def test_llm_message_with_photo_has_no_bytes_in_repr():
    photo = _photo()
    message = LLMMessage(role="user", content=[ImagePart(media_type="image/png", data=photo)])
    shown = {"repr": repr(message), "str": str(message)}
    assert_photo_not_leaked(shown, photo)
