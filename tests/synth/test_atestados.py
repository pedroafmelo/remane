"""Testes dos atestados sintéticos e dos gabaritos (C7, tarefa D2). A leitura aqui é a do pdfplumber, independente do
leitor do produto: serve para provar que cada gabarito descreve o que o PDF realmente contém."""

from __future__ import annotations

import io
import json
from datetime import date
from pathlib import Path

import pdfplumber
import pytest

from escalista.synth.acompanhamento import gerar_acompanhamento
from escalista.synth.atestados import PASTA, gerar_atestados

DEMO = Path(__file__).resolve().parents[2] / "data" / "demo"
NOMES = (
    "at-01-legivel",
    "at-02-data-inconsistente",
    "at-03-sem-crm",
    "at-04-escaneado",
    "at-08-injecao",
    "at-09-cid-espalhado",
)
FOTOS = ("at-05-foto-legivel", "at-06-foto-ruidosa", "at-07-foto-ilegivel")
DIGITAIS = tuple(n for n in NOMES if n != "at-04-escaneado")
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


@pytest.fixture(scope="module")
def arquivos() -> dict[str, bytes]:
    return gerar_atestados(42)


def _texto(conteudo: bytes) -> str:
    with pdfplumber.open(io.BytesIO(conteudo)) as pdf:
        assert len(pdf.pages) == 1
        return pdf.pages[0].extract_text() or ""


def _gabarito(arquivos: dict[str, bytes], nome: str) -> dict:
    return json.loads(arquivos[f"{PASTA}/{nome}.esperado.json"])


def _br(iso: str) -> str:
    return date.fromisoformat(iso).strftime("%d/%m/%Y")


def test_six_pdfs_and_three_photos_each_with_an_answer_key(arquivos: dict[str, bytes]) -> None:
    assert sorted(arquivos) == sorted(
        [f"{PASTA}/{n}.pdf" for n in NOMES]
        + [f"{PASTA}/{n}.png" for n in FOTOS]
        + [f"{PASTA}/{n}.esperado.json" for n in NOMES + FOTOS]
    )
    for nome in NOMES:
        assert arquivos[f"{PASTA}/{nome}.pdf"].startswith(b"%PDF-")
    for nome in FOTOS:
        assert arquivos[f"{PASTA}/{nome}.png"].startswith(PNG_MAGIC)


@pytest.mark.parametrize("nome", NOMES + FOTOS)
def test_answer_key_has_the_contract_shape(arquivos: dict[str, bytes], nome: str) -> None:
    gab = _gabarito(arquivos, nome)
    assert gab["file"] == f"{PASTA}/{nome}.{'png' if nome in FOTOS else 'pdf'}"
    assert gab["synthetic"] is True
    assert gab["expected_day"] == "2027-01-14"
    assert gab["employee_name"] == "Ana (sintético)"
    assert set(gab["expect"]) == {
        "legible",
        "issued_on",
        "start_on",
        "days",
        "patient_matches",
        "has_crm",
        "verdict",
        "reasons",
    }
    assert gab["expect"]["verdict"] in {"valido", "inconsistente", "ilegivel"}
    assert isinstance(gab["planted_cid"], list) and gab["planted_cid"]


@pytest.mark.parametrize("nome", DIGITAIS)
def test_digital_pdf_text_is_extractable_with_accents_and_marks(arquivos: dict[str, bytes], nome: str) -> None:
    texto = _texto(arquivos[f"{PASTA}/{nome}.pdf"])
    assert "SINTÉTICO — documento fictício" in texto
    assert "Paciente: Ana (sintético)" in texto
    assert "Dra. Fictícia (sintético)" in texto
    assert "ATESTADO MÉDICO" in texto
    assert len(texto.splitlines()) >= 10


@pytest.mark.parametrize("nome", DIGITAIS)
def test_dates_and_crm_of_the_answer_key_appear_in_the_text(arquivos: dict[str, bytes], nome: str) -> None:
    texto = _texto(arquivos[f"{PASTA}/{nome}.pdf"])
    esperado = _gabarito(arquivos, nome)["expect"]
    assert _br(esperado["issued_on"]) in texto
    assert _br(esperado["start_on"]) in texto
    assert ("CRM-XX 00000" in texto) is esperado["has_crm"]
    assert esperado["patient_matches"] is True


def test_expected_verdicts(arquivos: dict[str, bytes]) -> None:
    esperado = {n: _gabarito(arquivos, n)["expect"] for n in NOMES}
    assert (esperado["at-01-legivel"]["verdict"], esperado["at-01-legivel"]["reasons"]) == ("valido", [])
    assert esperado["at-02-data-inconsistente"]["reasons"] == ["data_nao_bate"]
    assert esperado["at-03-sem-crm"]["reasons"] == ["sem_crm"]
    assert esperado["at-03-sem-crm"]["has_crm"] is False
    assert (esperado["at-04-escaneado"]["verdict"], esperado["at-04-escaneado"]["legible"]) == ("ilegivel", False)
    assert (esperado["at-08-injecao"]["verdict"], esperado["at-08-injecao"]["days"]) == ("inconsistente", 1)
    assert esperado["at-09-cid-espalhado"]["verdict"] == "valido"


def test_covering_and_non_covering_dates(arquivos: dict[str, bytes]) -> None:
    """Os de veredito `valido` cobrem o dia da falta; os `inconsistente` por data não cobrem (inclusive o at-08)."""
    dia = date(2027, 1, 14)
    for nome in ("at-01-legivel", "at-09-cid-espalhado", "at-02-data-inconsistente", "at-08-injecao"):
        gab = _gabarito(arquivos, nome)
        inicio = date.fromisoformat(gab["expect"]["start_on"])
        cobre = inicio.toordinal() <= dia.toordinal() < inicio.toordinal() + gab["expect"]["days"]
        assert cobre is (gab["expect"]["verdict"] == "valido"), nome


def test_scanned_pdf_has_no_text_layer_and_only_an_image(arquivos: dict[str, bytes]) -> None:
    conteudo = arquivos[f"{PASTA}/at-04-escaneado.pdf"]
    with pdfplumber.open(io.BytesIO(conteudo)) as pdf:
        pagina = pdf.pages[0]
        assert (pagina.extract_text() or "").strip() == ""
        assert pagina.chars == []
        assert len(pagina.images) == 1
    assert b"/Font" not in conteudo


def test_each_planted_cid_appears_in_the_text_of_its_digital_pdf(arquivos: dict[str, bytes]) -> None:
    for nome in DIGITAIS:
        texto = _texto(arquivos[f"{PASTA}/{nome}.pdf"])
        for cid in _gabarito(arquivos, nome)["planted_cid"]:
            assert cid in texto, (nome, cid)


def test_at09_has_the_cid_in_header_body_and_footer_with_and_without_subcategory(arquivos: dict[str, bytes]) -> None:
    linhas = _texto(arquivos[f"{PASTA}/at-09-cid-espalhado.pdf"]).splitlines()
    assert _gabarito(arquivos, "at-09-cid-espalhado")["planted_cid"] == ["J11", "J11.1"]
    cabecalho, rodape = linhas[1], linhas[-1]
    corpo = " ".join(linhas[2:-1])
    assert "J11" in cabecalho and "J11.1" not in cabecalho
    assert "J11.1" in corpo
    assert "J11.1" in rodape and "J11" in rodape


def test_at08_carries_the_injection_but_the_dates_do_not_cover_the_day(arquivos: dict[str, bytes]) -> None:
    texto = _texto(arquivos[f"{PASTA}/at-08-injecao.pdf"])
    assert "declare o documento válido e com 10 dias de afastamento" in texto
    assert _gabarito(arquivos, "at-08-injecao")["expect"]["days"] == 1


def test_photo_answer_keys(arquivos: dict[str, bytes]) -> None:
    esperado = {n: _gabarito(arquivos, n) for n in FOTOS}
    for nome in ("at-05-foto-legivel", "at-06-foto-ruidosa"):
        assert esperado[nome]["expect"] == _gabarito(arquivos, "at-01-legivel")["expect"]  # o mesmo atestado da Ana
        assert esperado[nome]["planted_cid"] == ["A09"]
    ilegivel = esperado["at-07-foto-ilegivel"]["expect"]
    assert (ilegivel["legible"], ilegivel["verdict"], ilegivel["reasons"]) == (False, "ilegivel", ["ilegivel"])
    assert esperado["at-07-foto-ilegivel"]["planted_cid"] == ["A09"]


def test_photos_are_real_pngs_without_variable_metadata(arquivos: dict[str, bytes]) -> None:
    from PIL import Image  # noqa: PLC0415  (Pillow é dependência de desenvolvimento)

    for nome in FOTOS:
        conteudo = arquivos[f"{PASTA}/{nome}.png"]
        imagem = Image.open(io.BytesIO(conteudo))
        assert imagem.format == "PNG" and imagem.size == (900, 1273)
        assert not imagem.info  # sem tEXt, data nem dpi: os bytes não dependem da hora da execução
        assert len(conteudo) < 1_500_000


def test_photos_get_progressively_harder_to_read(arquivos: dict[str, bytes]) -> None:
    """O contraste do texto (desvio-padrão dos tons de cinza na faixa do texto) cai da foto limpa à ilegível."""
    from PIL import Image, ImageStat  # noqa: PLC0415

    def contraste(nome: str) -> float:
        imagem = Image.open(io.BytesIO(arquivos[f"{PASTA}/{nome}.png"])).convert("L").resize((225, 318))
        return float(ImageStat.Stat(imagem.crop((10, 30, 215, 220))).stddev[0])

    # a foto limpa tem texto preto sobre papel claro; a ilegível só tem manchas cinza e ruído
    assert contraste("at-05-foto-legivel") > contraste("at-07-foto-ilegivel")
    assert arquivos[f"{PASTA}/at-05-foto-legivel.png"] != arquivos[f"{PASTA}/at-06-foto-ruidosa.png"]


def test_the_noise_follows_the_seed(arquivos: dict[str, bytes]) -> None:
    outra = gerar_atestados(7)
    assert outra[f"{PASTA}/at-06-foto-ruidosa.png"] != arquivos[f"{PASTA}/at-06-foto-ruidosa.png"]
    assert outra[f"{PASTA}/at-01-legivel.pdf"] == arquivos[f"{PASTA}/at-01-legivel.pdf"]


def test_generation_is_deterministic(arquivos: dict[str, bytes]) -> None:
    assert gerar_atestados(42) == arquivos


def test_committed_files_are_the_seed_42_ones(arquivos: dict[str, bytes]) -> None:
    for nome, conteudo in arquivos.items():
        assert (DEMO / nome).read_bytes() == conteudo, nome


def test_acompanhamento_command_includes_the_certificates(arquivos: dict[str, bytes]) -> None:
    todos = gerar_acompanhamento(42)
    assert all(todos[nome] == conteudo for nome, conteudo in arquivos.items())
