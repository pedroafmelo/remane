"""Leitura do atestado (plano da C7, seção 4.7; SAIDA-AC-05 v1.1): borda entre o PDF e `AtestadoReading`.

Caminho: `pdf_text` (pdfplumber, em memória) → `audit.protected.strip_cid` (o CID sai **antes** do modelo) →
`call_structured` com o schema fechado `AtestadoFields` (modelo `small`) → `rules.atestado.judge` (o `verdict` e as
`reasons` saem do código, nunca do modelo).

- Privacidade (RN-06): os bytes e o texto extraído ficam em memória; nada vai a arquivo, a log nem ao retorno. Falha ao
  abrir o PDF não loga a mensagem da exceção (ela pode conter texto do arquivo).
- PDF sem texto (escaneado), corrompido ou protegido → `ilegivel`, **sem chamar o modelo**.
- Foto (image/png, image/jpeg): leitura pelo modelo de visão fica no T2 (DEC-057); no T1 devolve `ilegivel`, sem modelo.
- Falha do modelo: `LLMUnavailableError` (RX-12) sobe; o `Tracker` trata (abono provisório, `reading=None`).
"""

from __future__ import annotations

import io
import logging
from datetime import date

from escalista.audit.protected import strip_cid
from escalista.domain.ports import AtestadoReader, LLMClient
from escalista.domain.tracking import AtestadoFields, AtestadoReading
from escalista.llm.prompts.atestado import KIND, TOOL_DESCRIPTION, TOOL_NAME, build_messages
from escalista.llm.structured import call_structured
from escalista.rules.atestado import judge

PDF_MEDIA_TYPE = "application/pdf"
MAX_PAGES = 5

# O pdfminer registra em DEBUG o conteúdo do que lê (operadores e trechos de texto). Com o log do processo em DEBUG isso
# vazaria o atestado (RN-06): os loggers da leitura de PDF ficam em WARNING, qualquer que seja o nível da raiz.
for _name in ("pdfminer", "pdfplumber"):
    logging.getLogger(_name).setLevel(logging.WARNING)


def pdf_text(data: bytes, *, max_pages: int = MAX_PAGES) -> str | None:
    """Texto das primeiras `max_pages` páginas do PDF, em memória; `None` se corrompido, protegido, sem páginas ou
    sem texto. Nunca loga o conteúdo nem a mensagem da exceção."""
    import pdfplumber  # importado só aqui: quem não lê PDF não paga o custo

    try:
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            parts = [(page.extract_text() or "").strip() for page in pdf.pages[:max_pages]]
    except Exception:  # borda: PDF corrompido ou fora do padrão; a mensagem pode ter texto do arquivo
        return None
    text = "\n".join(part for part in parts if part).strip()
    return text or None


def read_atestado(
    *, data: bytes, media_type: str, llm: LLMClient, run_id: str, expected_day: date, employee_name: str
) -> AtestadoReading:
    """Lê a comprovação e devolve os campos fechados já julgados. Levanta `LLMUnavailableError` (RX-12)."""
    text = pdf_text(data) if media_type == PDF_MEDIA_TYPE else None
    if text is None:
        return judge(AtestadoFields(legible=False), expected_day=expected_day)
    fields = call_structured(
        llm,
        AtestadoFields,
        messages=build_messages(strip_cid(text), employee_name=employee_name, expected_day=expected_day),
        run_id=run_id,
        tool_name=TOOL_NAME,
        tool_description=TOOL_DESCRIPTION,
        size="small",
        kind=KIND,
        what="leitura do atestado",
    )
    return judge(fields, expected_day=expected_day)


def make_reader(llm: LLMClient) -> AtestadoReader:
    """Leitor que satisfaz a porta `AtestadoReader`, com o cliente do modelo já preso."""

    def reader(*, data: bytes, media_type: str, run_id: str, expected_day: date, employee_name: str) -> AtestadoReading:
        return read_atestado(
            data=data,
            media_type=media_type,
            llm=llm,
            run_id=run_id,
            expected_day=expected_day,
            employee_name=employee_name,
        )

    return reader
