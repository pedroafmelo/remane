"""`SqlRepository`: implementa as portas `Repository` e `RosterRepository` sobre as tabelas de
`store.tables` (plano da C5, seção 3.2; quadro: C6, seção 5.2).

Decisões:
- `save_*` faz upsert pela chave (`run_id`, `id`).
- `record_approval`: uma aprovação por versão; a segunda **substitui** a primeira (mesmo comportamento do falso).
  O histórico de quem aprovou fica no rastro (`approval.recorded`), não aqui.
- `mark_published`: muda o status da versão para `published` e a coloca como a última publicada (ordem de gravação
  por `publish_seq`, não o relógio); versão desconhecida levanta `KeyError`.
- `save_roster` só acrescenta: versão repetida levanta `ValueError` (igual ao falso); `latest_roster` é a maior versão.
- Leitura devolve o modelo pydantic gravado, igual ao original (`Decimal` preservado).
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Engine, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from escalista.clock.system import to_brasilia_naive
from escalista.domain.results import Approval, RunState, ScheduleVersion
from escalista.domain.roster import Roster
from escalista.store.tables import ApprovalRow, RosterVersionRow, RunStateRow, ScheduleVersionRow


class SqlRepository:
    """Exemplo: `init_db(engine)` (com este módulo importado) e `SqlRepository(engine)`. Cada chamada abre a sua
    sessão e confirma ao sair: duas instâncias sobre o mesmo engine veem os mesmos dados."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def __repr__(self) -> str:
        return f"SqlRepository({self._engine.url.render_as_string(hide_password=True)!r})"

    def save_run(self, state: RunState) -> None:
        data = state.model_dump(mode="json")
        with Session(self._engine) as session, session.begin():
            row = session.get(RunStateRow, state.run_id)
            if row is None:
                row = RunStateRow(run_id=state.run_id)
                session.add(row)
            row.phase, row.version_id, row.data = state.phase, state.version_id, data

    def get_run(self, run_id: str) -> RunState | None:
        with Session(self._engine) as session:
            row = session.get(RunStateRow, run_id)
            return None if row is None else RunState.model_validate(row.data)

    def save_version(self, v: ScheduleVersion) -> None:
        data = v.model_dump(mode="json")
        with Session(self._engine) as session, session.begin():
            row = session.get(ScheduleVersionRow, v.id)
            if row is None:
                row = ScheduleVersionRow(id=v.id)
                session.add(row)
            row.run_id, row.status, row.data = v.run_id, v.status, data
            row.created_at = to_brasilia_naive(v.created_at)

    def get_version(self, version_id: str) -> ScheduleVersion | None:
        with Session(self._engine) as session:
            row = session.get(ScheduleVersionRow, version_id)
            return None if row is None else ScheduleVersion.model_validate(row.data)

    def record_approval(self, a: Approval) -> None:
        data = a.model_dump(mode="json")
        with Session(self._engine) as session, session.begin():
            row = session.scalar(select(ApprovalRow).where(ApprovalRow.version_id == a.version_id))
            if row is None:
                row = ApprovalRow(version_id=a.version_id)
                session.add(row)
            row.id, row.data = a.id, data
            row.at = to_brasilia_naive(a.at)

    def get_approval(self, version_id: str) -> Approval | None:
        with Session(self._engine) as session:
            row = session.scalar(select(ApprovalRow).where(ApprovalRow.version_id == version_id))
            return None if row is None else Approval.model_validate(row.data)

    def mark_published(self, version_id: str, at: datetime) -> None:
        with Session(self._engine) as session, session.begin():
            row = session.get(ScheduleVersionRow, version_id)
            if row is None:
                raise KeyError(version_id)
            version = ScheduleVersion.model_validate(row.data).model_copy(update={"status": "published"})
            row.status, row.data = "published", version.model_dump(mode="json")
            row.published_at = to_brasilia_naive(at)
            row.publish_seq = (session.scalar(select(func.max(ScheduleVersionRow.publish_seq))) or 0) + 1

    def latest_published(self) -> ScheduleVersion | None:
        stmt = (
            select(ScheduleVersionRow)
            .where(ScheduleVersionRow.publish_seq.is_not(None))
            .order_by(ScheduleVersionRow.publish_seq.desc())
            .limit(1)
        )
        with Session(self._engine) as session:
            row = session.scalars(stmt).first()
            return None if row is None else ScheduleVersion.model_validate(row.data)

    def save_roster(self, r: Roster) -> None:
        message = f"o quadro versão {r.version} já existe; cada confirmação acrescenta uma versão"
        try:
            with Session(self._engine) as session, session.begin():
                if session.get(RosterVersionRow, r.version) is not None:
                    raise ValueError(message)
                session.add(
                    RosterVersionRow(
                        version=r.version,
                        confirmed_at=to_brasilia_naive(r.confirmed_at),
                        data=r.model_dump(mode="json"),
                    )
                )
        except IntegrityError as exc:  # corrida entre duas gravações da mesma versão
            raise ValueError(message) from exc

    def latest_roster(self) -> Roster | None:
        stmt = select(RosterVersionRow).order_by(RosterVersionRow.version.desc()).limit(1)
        with Session(self._engine) as session:
            row = session.scalars(stmt).first()
            return None if row is None else Roster.model_validate(row.data)

    def get_roster(self, version: int) -> Roster | None:
        with Session(self._engine) as session:
            row = session.get(RosterVersionRow, version)
            return None if row is None else Roster.model_validate(row.data)
