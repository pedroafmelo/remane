"""Leitura do atestado em PDF (C7 B3, SAIDA-AC-05 v1.1): CID cortado antes do modelo, verdict do código, sem modelo
para o que não tem texto."""

from __future__ import annotations

import io
import logging
from datetime import date

import pytest

from escalista.domain.contracts import LLMUnavailableError
from escalista.domain.ports import AtestadoReader
from escalista.ingest.atestado import make_reader, pdf_text, read_atestado
from escalista.llm.prompts.atestado import TOOL_NAME
from tests.fakes import FakeLLMClient

DIA = date(2027, 1, 12)
NOME = "Ana Souza Lima"
CAMPOS_OK = {
    "legible": True,
    "issued_on": "2027-01-12",
    "start_on": "2027-01-12",
    "days": 2,
    "patient_matches": True,
    "has_crm": True,
}


def _pdf_texto(linhas: list[str]) -> bytes:
    """PDF mínimo escrito à mão: uma página com as linhas de texto (só ASCII, sem parênteses)."""
    texto = "BT /F1 12 Tf 72 760 Td 18 TL\n" + "\n".join(f"({linha}) Tj T*" for linha in linhas) + "\nET"
    objetos = [
        "<< /Type /Catalog /Pages 2 0 R >>",
        "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents 4 0 R "
        "/Resources << /Font << /F1 5 0 R >> >> >>",
        f"<< /Length {len(texto)} >>\nstream\n{texto}\nendstream",
        "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    pdf = b"%PDF-1.4\n"
    posicoes = []
    for numero, corpo in enumerate(objetos, start=1):
        posicoes.append(len(pdf))
        pdf += f"{numero} 0 obj\n{corpo}\nendobj\n".encode("ascii")
    xref = len(pdf)
    pdf += f"xref\n0 {len(objetos) + 1}\n0000000000 65535 f \n".encode("ascii")
    pdf += b"".join(f"{p:010d} 00000 n \n".encode("ascii") for p in posicoes)
    pdf += f"trailer\n<< /Size {len(objetos) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode("ascii")
    return pdf


def _pdf_so_imagem() -> bytes:
    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (200, 120), "white").save(buf, "PDF")
    return buf.getvalue()


ATESTADO = _pdf_texto(
    [
        "ATESTADO MEDICO (ficticio)",
        "Atesto que Ana Souza Lima esteve em consulta e deve ficar afastada por 2 dias.",
        "Emitido em 12/01/2027.",
        "CID: J11.1",
        "Diagnostico associado J11 (influenza).",
        "Dr. Fulano de Tal CRM 12345-PE",
    ]
)


def _mensagens(llm: FakeLLMClient) -> str:
    return "\n".join(m.content for call in llm.calls for m in call["messages"])


def _ler(llm: FakeLLMClient, data: bytes = ATESTADO, media_type: str = "application/pdf"):
    return read_atestado(
        data=data, media_type=media_type, llm=llm, run_id="track-c1", expected_day=DIA, employee_name=NOME
    )


def test_pdf_text_extrai_o_texto_em_memoria() -> None:
    texto = pdf_text(ATESTADO)
    assert texto is not None
    assert "Ana Souza Lima" in texto
    assert "J11.1" in texto  # o corte do CID é do passo seguinte, não do pdf_text


def test_pdf_text_so_imagem_e_none() -> None:
    assert pdf_text(_pdf_so_imagem()) is None


def test_pdf_text_corrompido_e_none_sem_logar(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.DEBUG):
        assert pdf_text(b"%PDF-1.4\nSEGREDO-DO-ARQUIVO nao e um pdf") is None
    assert "SEGREDO-DO-ARQUIVO" not in caplog.text


def test_pdf_text_respeita_max_paginas() -> None:
    assert pdf_text(ATESTADO, max_pages=0) is None


def test_cid_nao_chega_ao_modelo() -> None:
    llm = FakeLLMClient(by_tool={TOOL_NAME: [CAMPOS_OK]})
    _ler(llm)
    assert len(llm.calls) == 1
    enviado = _mensagens(llm)
    assert "J11" not in enviado
    assert "Ana Souza Lima" in enviado  # o resto do texto segue
    assert llm.calls[0]["size"] == "small"
    assert llm.calls[0]["tool_name"] == TOOL_NAME


def test_campos_validos_viram_valido() -> None:
    reading = _ler(FakeLLMClient(by_tool={TOOL_NAME: [CAMPOS_OK]}))
    assert reading.verdict == "valido"
    assert reading.reasons == []
    assert reading.days == 2
    assert reading.legible is True


def test_data_fora_e_julgada_pelo_codigo() -> None:
    fora = {**CAMPOS_OK, "issued_on": "2027-02-20", "start_on": "2027-02-20"}
    reading = _ler(FakeLLMClient(by_tool={TOOL_NAME: [fora]}))
    assert reading.verdict == "inconsistente"
    assert reading.reasons == ["data_nao_bate"]


def test_o_modelo_nao_decide_o_verdict() -> None:
    # `verdict` não é campo do schema fechado: se o modelo o devolver, a resposta é recusada (RX-12)
    forjado = {**CAMPOS_OK, "verdict": "valido"}
    with pytest.raises(LLMUnavailableError):
        _ler(FakeLLMClient(by_tool={TOOL_NAME: [forjado] * 3}))


def test_pdf_so_imagem_e_ilegivel_sem_modelo() -> None:
    llm = FakeLLMClient()
    reading = _ler(llm, _pdf_so_imagem())
    assert (reading.legible, reading.verdict, reading.reasons) == (False, "ilegivel", ["ilegivel"])
    assert llm.calls == []


def test_bytes_corrompidos_sao_ilegiveis_sem_modelo() -> None:
    llm = FakeLLMClient()
    reading = _ler(llm, b"isto nao e um pdf")
    assert reading.verdict == "ilegivel"
    assert llm.calls == []


@pytest.mark.parametrize("media_type", ["image/png", "image/jpeg"])
def test_foto_no_t1_e_ilegivel_sem_modelo(media_type: str) -> None:
    llm = FakeLLMClient()
    reading = _ler(llm, b"\x89PNG fake", media_type)
    assert reading.verdict == "ilegivel"
    assert llm.calls == []


def test_modelo_fora_levanta_rx12() -> None:
    llm = FakeLLMClient(fail_tools={TOOL_NAME})
    with pytest.raises(LLMUnavailableError) as exc:
        _ler(llm)
    assert exc.value.card.code == "RX-12"


@pytest.mark.parametrize("extra", [{"cid": "J11.1"}, {"medico": "Dr. Fulano"}, {"texto": "trecho do atestado"}])
def test_campo_extra_nao_vira_leitura(extra: dict[str, str]) -> None:
    llm = FakeLLMClient(by_tool={TOOL_NAME: [{**CAMPOS_OK, **extra}] * 3})
    with pytest.raises(LLMUnavailableError) as exc:
        _ler(llm)
    assert exc.value.card.code == "RX-12"
    assert len(llm.calls) == 3  # 1 chamada e 2 reenvios, depois recusa


def test_campo_extra_recusado_e_depois_corrigido_vira_leitura() -> None:
    llm = FakeLLMClient(by_tool={TOOL_NAME: [{**CAMPOS_OK, "cid": "J11.1"}, CAMPOS_OK]})
    reading = _ler(llm)
    assert reading.verdict == "valido"
    assert len(llm.calls) == 2
    assert not hasattr(reading, "cid")


def test_retorno_e_log_nao_trazem_o_texto(caplog: pytest.LogCaptureFixture) -> None:
    llm = FakeLLMClient(by_tool={TOOL_NAME: [CAMPOS_OK]})
    with caplog.at_level(logging.DEBUG):
        reading = _ler(llm)
    dump = reading.model_dump_json()
    for trecho in ("Ana Souza", "Fulano", "J11", "influenza"):
        assert trecho not in dump
        assert trecho not in caplog.text


def test_make_reader_satisfaz_a_porta() -> None:
    llm = FakeLLMClient(by_tool={TOOL_NAME: [CAMPOS_OK]})
    reader = make_reader(llm)
    assert isinstance(reader, AtestadoReader)
    reading = reader(
        data=ATESTADO, media_type="application/pdf", run_id="track-c1", expected_day=DIA, employee_name=NOME
    )
    assert reading.verdict == "valido"
    assert len(llm.calls) == 1
