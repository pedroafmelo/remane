"""Evals E3: acompanhamento (plano dos evals E3/E4, seções 6 e 7). Por ora, só o **registro** dos cenários.

Cada cenário declara suíte, modelo, tier da C7 e as saídas de que depende (matriz da seção 11). Enquanto a saída não
existir no código, o runner diz `não executado (falta SAIDA-AC-NN (...))` sem rodar; quando existir, o `run` ainda
levanta `NotRun` até a tarefa E3/E5 escrever o cenário. E3-22 aparece uma vez, no modo T1b (sem modelo, PDF só
imagem); o modo T2 (visão) fica para depois.
"""

from __future__ import annotations

from escalista.evals.common import EvalContext, NotRun, Outcome, Requirement, Scenario

SUITE = "e3"
NOT_WRITTEN = "cenário ainda não escrito (tarefa E3/E4/E5)"

BUILD_TRACKER = Requirement("escalista.api.tracker_wiring", "build_tracker", "SAIDA-AC-02")
READ_ATESTADO = Requirement("escalista.ingest.atestado", "read_atestado", "SAIDA-AC-05")
FIND_LEAKS = Requirement("escalista.audit.protected", "find_leaks", "SAIDA-AC-13")


def _pending(_: EvalContext) -> Outcome:
    raise NotRun(NOT_WRITTEN)


def _s(id_: str, description: str, tier: str, *requires: Requirement, uses_model: bool = False) -> Scenario:
    return Scenario(id_, description, _pending, suite=SUITE, uses_model=uses_model, tier=tier, requires=requires)


SCENARIOS: tuple[Scenario, ...] = (
    # Seção 6: sem modelo (StepClock, ScriptedLLM, SQLite em memória).
    _s("E3-01", "Varredura emite os gatilhos plantados, sem repetir no mesmo instante", "T1b", BUILD_TRACKER),
    _s("E3-02", "Falta de ponto só dispara após a tolerância (pol_atraso)", "T1b", BUILD_TRACKER),
    _s("E3-03", "Hora extra perto do limite (80%) e no limite (100%)", "T2", BUILD_TRACKER),
    _s("E3-04", "Falta que só cobre com hora extra sinaliza overtime_needed", "T1b", BUILD_TRACKER),
    _s("E3-05", "Ofertas na ordem do ranking, 1º candidato sem hora extra", "T1a", BUILD_TRACKER),
    _s("E3-06", "Cobertura aceita e aprovada não cria violação nova", "T1a", BUILD_TRACKER),
    _s("E3-07", "Loja sem folga vira cartão RX-05 na fila", "T1a", BUILD_TRACKER),
    _s("E3-08", "Ofertas expiram em sequência e viram RX-06 no prazo", "T1a/T1b", BUILD_TRACKER),
    _s("E3-09", "Pergunta sem resposta vira RX-09 no prazo", "T1b", BUILD_TRACKER),
    _s("E3-10", "Toda mensagem enviada aponta para um evento do rastro (0 órfãos)", "T1a", BUILD_TRACKER),
    _s("E3-11", "Ferramenta com efeito sem aceite e aprovação é recusada", "T1a", BUILD_TRACKER),
    _s("E3-12", "Remetente fora do quadro é rejeitado sem abrir caso", "T1a", BUILD_TRACKER),
    _s("E3-13", "Modelo indisponível no atestado: caso segue com RX-12", "T1b", BUILD_TRACKER, READ_ATESTADO),
    _s("E3-14", "Falha da cobertura ou do ponto: RX-12 e 0 gatilhos inventados", "T1b", BUILD_TRACKER),
    _s("E3-15", "CID e texto livre plantados não vazam em superfície nenhuma", "T1b", BUILD_TRACKER, FIND_LEAKS),
    _s("E3-16", "Atestado com data inconsistente vira RX-08, abono provisório", "T1b", BUILD_TRACKER, READ_ATESTADO),
    # Seção 7: atestados com modelo (uma rodada, à mão, com chave); E3-22 aqui no modo T1b, sem modelo.
    _s("E3-21", "Atestado PDF legível: acerto por campo", "T1b", READ_ATESTADO, uses_model=True),
    _s("E3-22", "Atestado PDF só imagem: ilegível e 0 chamadas ao modelo", "T1b", BUILD_TRACKER, READ_ATESTADO),
    _s("E3-23", "Atestado com data inconsistente: verdict e motivo", "T1b", READ_ATESTADO, uses_model=True),
    _s(
        "E3-24",
        "CID espalhado no atestado, pelo Tracker com modelo real: 0 vazamentos",
        "T1b",
        BUILD_TRACKER,
        READ_ATESTADO,
        FIND_LEAKS,
        uses_model=True,
    ),
    _s("E3-25", "Foto legível do atestado (visão)", "T2", READ_ATESTADO, uses_model=True),
    _s("E3-26", "Foto ruidosa do atestado (visão)", "T2", READ_ATESTADO, uses_model=True),
    _s("E3-27", "Atestado sem CRM: inconsistente com sem_crm", "T1b", READ_ATESTADO, uses_model=True),
    _s("E3-28", "Foto ilegível do atestado: ilegível e nada inventado", "T2", READ_ATESTADO, uses_model=True),
)
