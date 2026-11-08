"""Leitura do atestado (plano da C7, seção 4.7; SAIDA-AC-05 v1.1): borda entre o PDF (ou a foto) e `AtestadoReading`.

Caminho: `pdf_text` (pdfplumber, em memória) → `audit.protected.strip_cid` (o CID sai **antes** do modelo) →
`call_structured` com o schema fechado `AtestadoFields` (modelo `small`) → `rules.atestado.judge` (o `verdict` e as
`reasons` saem do código, nunca do modelo).

- Privacidade (RN-06): os bytes e o texto extraído ficam em memória; nada vai a arquivo, a log nem ao retorno. Falha ao
  abrir o PDF não loga a mensagem da exceção (ela pode conter texto do arquivo).
- PDF sem texto (escaneado), corrompido ou protegido → `ilegivel`, **sem chamar o modelo**.
- Foto (image/png, image/jpeg; T2, DEC-058): o tipo vem da **assinatura dos bytes** (PNG `\\x89PNG\\r\\n\\x1a\\n`, JPEG
  `\\xff\\xd8\\xff`), não do rótulo; até `MAX_IMAGE_BYTES` (5 MB). A imagem vai, em memória, ao modelo `vision`
  (DEC-020: `Qwen/Qwen3.5-9B`, **nunca testado com imagem**) por `call_structured`, com o mesmo schema e a mesma
  ferramenta do PDF. Não há corte de CID na foto (o CID está nos pixels): a proteção é o schema fechado, que não tem
  onde devolvê-lo. Bytes que não são PNG/JPEG, imagem grande demais ou tipo desconhecido → `ilegivel`, sem modelo.
- PDF escaneado continua `ilegivel` sem modelo: convertê-lo em imagem exigiria renderizar PDF (dependência nova).
- Falha do modelo: `LLMUnavailableError` (RX-12) sobe; o `Tracker` trata (abono provisório, `reading=None`).
"""

from __future__ import annotations

import io
import logging
from datetime import date
from typing import Literal

from escalista.audit.protected import strip_cid
from escalista.domain.contracts import LLMMessage
from escalista.domain.ports import AtestadoReader, LLMClient
from escalista.domain.tracking import AtestadoFields, AtestadoReading
from escalista.llm.prompts.atestado import KIND, TOOL_DESCRIPTION, TOOL_NAME, build_image_messages, build_messages
from escalista.llm.structured import call_structured
from escalista.rules.atestado import judge

PDF_MEDIA_TYPE = "application/pdf"
IMAGE_MEDIA_TYPES = ("image/png", "image/jpeg")
MAX_PAGES = 5
MAX_IMAGE_BYTES = 5 * 1024 * 1024
_SIGNATURES = ((b"\x89PNG\r\n\x1a\n", "image/png"), (b"\xff\xd8\xff", "image/jpeg"))

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


def image_type(data: bytes) -> str | None:
    """Tipo da imagem pela assinatura dos bytes (PNG ou JPEG); `None` se não for uma delas."""
    return next((media_type for signature, media_type in _SIGNATURES if data.startswith(signature)), None)


def read_atestado(
    *, data: bytes, media_type: str, llm: LLMClient, run_id: str, expected_day: date, employee_name: str
) -> AtestadoReading:
    """Lê a comprovação e devolve os campos fechados já julgados. Levanta `LLMUnavailableError` (RX-12)."""
    illegible = judge(AtestadoFields(legible=False), expected_day=expected_day)
    if media_type in IMAGE_MEDIA_TYPES:
        detected = image_type(data) if len(data) <= MAX_IMAGE_BYTES else None
        if detected is None:
            return illegible
        messages = build_image_messages(
            data, media_type=detected, employee_name=employee_name, expected_day=expected_day
        )
        return judge(_read(llm, messages, run_id, size="vision"), expected_day=expected_day)
    text = pdf_text(data) if media_type == PDF_MEDIA_TYPE else None
    if text is None:
        return illegible
    messages = build_messages(strip_cid(text), employee_name=employee_name, expected_day=expected_day)
    return judge(_read(llm, messages, run_id, size="small"), expected_day=expected_day)


def _read(
    llm: LLMClient, messages: list[LLMMessage], run_id: str, *, size: Literal["small", "vision"]
) -> AtestadoFields:
    return call_structured(
        llm,
        AtestadoFields,
        messages=messages,
        run_id=run_id,
        tool_name=TOOL_NAME,
        tool_description=TOOL_DESCRIPTION,
        size=size,
        kind=KIND,
        what="leitura do atestado",
    )


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
