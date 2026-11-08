"""Ferramentas do acompanhamento com portão no código (plano da C7, seção 7; SAIDA-AC-09 e 16).

- `enviar`: mensagem de saída só para quem está no roteiro do caso (o faltante, os candidatos do caso ou o gestor).
  Oferecer o turno é ato do agente sozinho, mas outro destinatário é recusado (`track.tool.refused`).
- `aplicar_cobertura`: só com a oferta **aceita** pelo colega **e** a aprovação do gestor gravada no `Repository`,
  lidas aqui. Então chama a mesma `publicar` da otimização, que relê a aprovação.

Toda recusa grava `track.tool.refused {tool, reason, case_id}` e levanta `ToolRefusedError`.
"""

from __future__ import annotations

from collections.abc import Callable

from escalista.agents.optimizer.tools import Tracer, publicar
from escalista.domain.ports import Channel, Repository
from escalista.domain.results import ScheduleVersion
from escalista.domain.tracking import Case, ChannelMessage, ToolRefusedError

GESTOR_PARTY = "gestor"


def refuse(tracer: Tracer, case: Case, tool: str, reason: str) -> ToolRefusedError:
    """Grava a recusa no rastro do caso e devolve o erro para o chamador levantar."""
    tracer.step(case.run_id, "track.tool.refused", payload={"tool": tool, "reason": reason, "case_id": case.id})
    return ToolRefusedError(tool, reason)


def allowed_parties(case: Case) -> set[str]:
    return {case.employee_id, GESTOR_PARTY, *case.ranked, *(o.candidate_id for o in case.offers)}


def enviar(
    *,
    channel: Channel,
    tracer: Tracer,
    case: Case,
    to: str,
    template: str,
    body: str,
    decision_ref: str,
    new_id: Callable[[], str],
) -> ChannelMessage:
    """Envia `body` (texto nosso) a `to` e registra `track.message.sent` encadeado no evento que gerou a mensagem."""
    if to not in allowed_parties(case):
        raise refuse(tracer, case, "enviar", "destinatário fora do roteiro do caso")
    message = ChannelMessage(
        id=new_id(),
        case_id=case.id,
        direction="out",
        party=to,
        template=template,
        body=body,
        decision_ref=decision_ref,
        at=tracer.now(),
    )
    channel.send(message)
    tracer.follow(case.run_id, decision_ref)
    tracer.step(
        case.run_id,
        "track.message.sent",
        payload={"case_id": case.id, "message_id": message.id, "to": to, "template": template},
    )
    return message


def aplicar_cobertura(*, repo: Repository, tracer: Tracer, case: Case, version_id: str | None) -> ScheduleVersion:
    """Publica a versão com o turno coberto. Recusa sem oferta aceita no caso ou sem aprovação gravada da versão."""
    if not any(o.status == "aceita" for o in case.offers):
        raise refuse(tracer, case, "aplicar_cobertura", "nenhuma oferta aceita pelo colega neste caso")
    version = repo.get_version(version_id) if version_id else None
    if version is None:
        raise refuse(tracer, case, "aplicar_cobertura", "versão da escala não encontrada")
    if repo.get_approval(version.id) is None:
        raise refuse(tracer, case, "aplicar_cobertura", "aprovação do gestor não encontrada para esta versão")
    return publicar(repo=repo, tracer=tracer, run_id=version.run_id, version_id=version.id)
