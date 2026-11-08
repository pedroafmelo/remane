"""Lista única de campos protegidos (RN-06, SAIDA-AC-13 v1.1): nome de campo, padrão de CID e busca de vazamento."""

import dataclasses
import json

import pytest

from escalista.audit.protected import (
    CID_PATTERN,
    CID_REMOVED,
    PROTECTED_KEYS,
    REDACTED,
    Leak,
    find_leaks,
    scrub,
    strip_cid,
)

# --- lista e padrão ---------------------------------------------------------------------------------------------


def test_protected_keys_is_the_contract_list():
    assert isinstance(PROTECTED_KEYS, frozenset)
    assert {
        "cid",
        "cid10",
        "diagnostico",
        "diagnóstico",
        "text",
        "texto",
        "texto_livre",
        "raw_text",
        "image",
        "imagem",
        "attachment",
        "anexo",
        "medico",
        "médico",
    } == PROTECTED_KEYS


@pytest.mark.parametrize("code", ["J11", "J11.1", "A00", "Z99.9", "F32.0"])
def test_cid_pattern_matches_cid10_codes(code):
    assert CID_PATTERN.fullmatch(code)


@pytest.mark.parametrize("code", ["U07", "j11", "J1", "CID", "10"])
def test_cid_pattern_ignores_non_codes(code):
    assert not CID_PATTERN.search(code)


# --- strip_cid --------------------------------------------------------------------------------------------------


def test_strip_cid_removes_bare_codes_with_and_without_subcategory():
    out = strip_cid("Afastamento por J11 (J11.1) por 3 dias")
    assert "J11" not in out
    assert out.count(CID_REMOVED) == 2
    assert "por 3 dias" in out


@pytest.mark.parametrize(
    "line",
    ["CID: J11", "CID-10: J11.1", "CID 10 J11", "cid: j11.1", "CID10: j11", "CID = J11"],
)
def test_strip_cid_removes_value_after_label_even_lowercase(line):
    out = strip_cid(line)
    assert "j11" not in out.lower()
    assert CID_REMOVED in out


def test_strip_cid_covers_header_body_and_footer():
    text = (
        "ATESTADO MÉDICO (SINTÉTICO)  CID: J11\n"
        "Atesto que a paciente esteve sob meus cuidados, diagnóstico J11.1, devendo afastar-se por 2 dias.\n"
        "Emitido em 12/01/2026.\n"
        "Rodapé: cid-10 j11.1 | Dr. Fulano CRM 0000"
    )
    out = strip_cid(text)
    assert "j11" not in out.lower()
    assert "afastar-se por 2 dias" in out and "Emitido em 12/01/2026." in out
    assert out.count("\n") == 3  # o rótulo só apaga o valor da mesma linha


def test_strip_cid_keeps_text_without_cid():
    text = "Atestado de 2 dias a partir de 13/01/2026."
    assert strip_cid(text) == text


# --- scrub ------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("kind", ["llm.map_columns", "solver.run", "track.atestado.read", "exception.raised"])
@pytest.mark.parametrize("key", ["cid", "CID", "Diagnóstico", "TEXT", "raw_text", "Anexo", "médico"])
def test_scrub_redacts_protected_key_in_any_kind(kind, key):
    assert scrub({key: "J11 qualquer coisa", "ok": 1}, kind=kind) == {key: REDACTED, "ok": 1}


def test_scrub_redacts_whole_value_of_protected_key_even_nested_structures():
    payload = {"anexo": {"bytes": 10, "nome": "a.pdf"}, "items": [{"image": [1, 2]}, {"texto": None}]}
    assert scrub(payload, kind="solver.run") == {
        "anexo": REDACTED,
        "items": [{"image": REDACTED}, {"texto": REDACTED}],
    }


def test_scrub_strips_cid_in_any_string_of_track_payload():
    payload = {"nota": "J11.1", "reasons": ["CID: J11", "ok"], "deep": {"x": ("veja J11",)}, "days": 2, "ok": True}
    out = scrub(payload, kind="track.atestado.read")
    assert "J11" not in json.dumps(out)
    assert out["days"] == 2 and out["ok"] is True
    assert out["reasons"][1] == "ok"


def test_scrub_keeps_cell_reference_outside_track_kinds():
    payload = {"evidence": "célula B12", "mapping": [{"col": "C10", "field": "employee_id"}]}
    assert scrub(payload, kind="llm.map_columns") == payload


def test_scrub_applies_pattern_to_channel_message_surface():
    assert "J11" not in json.dumps(scrub({"body": "J11"}, kind="channel_message"))


def test_scrub_does_not_mutate_input():
    payload = {"text": "segredo", "nota": ["J11"]}
    scrub(payload, kind="track.report.received")
    assert payload == {"text": "segredo", "nota": ["J11"]}


# --- find_leaks -------------------------------------------------------------------------------------------------


def test_find_leaks_empty_when_clean():
    blobs = {"trace_event": "track.case.closed coberta", "log": "nada", "sheet": "célula B12"}
    assert find_leaks(blobs, ["J11", "febre alta"], pattern_surfaces={"trace_event"}) == []


def test_find_leaks_reports_planted_case_insensitive_without_value():
    leaks = find_leaks({"log": "paciente com FEBRE ALTA"}, ["febre alta"], pattern_surfaces=set())
    assert leaks == [Leak(surface="log", kind="planted")]
    assert "febre" not in repr(leaks).lower()
    assert {f.name for f in dataclasses.fields(Leak)} == {"surface", "kind"}


def test_find_leaks_pattern_only_on_pattern_surfaces():
    blobs = {"trace_event": "evidência B12", "channel_message": "código Z99", "http": "Z99"}
    leaks = find_leaks(blobs, [], pattern_surfaces={"channel_message"})
    assert leaks == [Leak(surface="channel_message", kind="pattern")]


def test_find_leaks_pattern_surface_prefix_with_star():
    blobs = {"track.atestado.read": "J11", "llm.map_columns": "B12", "track.case.closed": "ok"}
    leaks = find_leaks(blobs, [], pattern_surfaces={"track.*"})
    assert leaks == [Leak(surface="track.atestado.read", kind="pattern")]


def test_find_leaks_can_report_both_kinds_on_one_surface():
    leaks = find_leaks({"track.x": "J11 febre"}, ["febre"], pattern_surfaces={"track.*"})
    assert set(leaks) == {Leak("track.x", "planted"), Leak("track.x", "pattern")}


def test_find_leaks_ignores_empty_planted_strings():
    assert find_leaks({"log": "qualquer"}, [""], pattern_surfaces=set()) == []


def test_leak_is_frozen():
    with pytest.raises(dataclasses.FrozenInstanceError):
        Leak("log", "planted").surface = "x"  # type: ignore[misc]
