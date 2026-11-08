"use client";

import { useCallback, useState } from "react";
import { api, asFailure } from "@/lib/api";
import type { Failure } from "@/lib/errors";
import { phaseLabel, timeBr } from "@/lib/format";
import type { ConfirmInput, ProposedSchedule, PublishedSchedule, RunState, TraceEvent } from "@/lib/types";
import { Button } from "@/components/Button";
import { ComparePanel } from "@/components/plataforma/Compare";
import { ExceptionPanel } from "@/components/plataforma/ExceptionPanel";
import { NoticeList } from "@/components/plataforma/NoticeList";
import { useClockChange } from "@/components/plataforma/DemoClockBar";
import { PatWorking } from "@/components/plataforma/PatWorking";
import { JustificationPanel } from "@/components/plataforma/Justification";
import { SpecApplied } from "@/components/plataforma/SpecApplied";
import { ScheduleView } from "@/components/plataforma/ScheduleView";
import { Shell } from "@/components/plataforma/Shell";
import { SessionGate, useSession } from "@/components/plataforma/session";
import { SummaryPanel } from "@/components/plataforma/Summary";
import { TracePanel } from "@/components/plataforma/Trace";
import { UploadPanel } from "@/components/plataforma/Upload";
import { Muted, Notice } from "@/components/plataforma/ui";

const BUSY_LABELS: Record<string, string> = {
  upload: "Enviando e lendo o arquivo…",
  nextweek: "Preparando a próxima semana a partir da última escala publicada…",
  confirm: "Otimizando a escala, conferindo as regras e montando a justificativa…",
  approve: "Publicando a escala aprovada…",
  logout: "Saindo…",
};

export default function PlataformaPage() {
  const [busy, setBusy] = useState<string | null>(null); // o que está em andamento
  const [problem, setProblem] = useState<Failure | null>(null);
  const [run, setRun] = useState<RunState | null>(null);
  const [proposed, setProposed] = useState<ProposedSchedule | null>(null);
  const [published, setPublished] = useState<PublishedSchedule | null>(null);
  const [trace, setTrace] = useState<TraceEvent[]>([]);

  const refreshTrace = useCallback(async (runId: string) => {
    try {
      setTrace(await api.trace(runId));
    } catch {
      // o rastro é informativo: falhar aqui não derruba o fluxo
    }
  }, []);

  const refreshPublished = useCallback(async () => {
    try {
      setPublished(await api.published());
    } catch {
      setPublished(null);
    }
  }, []);

  const session = useSession("gestor", refreshPublished);
  const { toLogin } = session;

  /** Executa uma ação da tela: marca ocupado, limpa o problema e traduz os erros (401 volta a `/entrar/`). */
  async function act(label: string, fn: () => Promise<void>, runId?: string) {
    setBusy(label);
    setProblem(null);
    try {
      await fn();
    } catch (err) {
      const failure = asFailure(err);
      if (failure.kind === "auth") {
        toLogin();
        return;
      }
      setProblem(failure);
    } finally {
      if (runId) await refreshTrace(runId);
      setBusy(null);
    }
  }

  function reset() {
    setRun(null);
    setProposed(null);
    setTrace([]);
    setProblem(null);
  }

  // "Reiniciar demo" publica a semana sintética: a tela larga a execução em andamento e relê a escala publicada
  useClockChange((change) => {
    if (change.action !== "reset") return;
    reset();
    void refreshPublished();
  });

  const logout = () =>
    act("logout", async () => {
      reset();
      await session.logout();
    });

  /** Envia o arquivo (CSV, XLSX ou PDF, do disco ou de exemplo). Recusas (413, 422) voltam com o cartão RX-13 no corpo. */
  const send = (load: () => Promise<{ name: string; blob: Blob }>) =>
    act("upload", async () => {
      setRun(null);
      setProposed(null);
      setTrace([]);
      const { name, blob } = await load();
      const state = await api.startRun(name, blob);
      setRun(state);
      await refreshTrace(state.run_id);
    });

  /** Sem upload: parte da última escala publicada e do quadro guardado. 409 sem publicada volta com a mensagem do servidor. */
  const planNextWeek = () =>
    act("nextweek", async () => {
      setRun(null);
      setProposed(null);
      setTrace([]);
      const state = await api.nextWeek();
      setRun(state);
      await refreshTrace(state.run_id);
    });

  const confirm = (r: RunState, input: ConfirmInput) =>
    act(
      "confirm",
      async () => {
        const state = await api.confirm(r.run_id, input);
        setRun(state);
        if (state.phase === "awaiting_approval") setProposed(await api.schedule(r.run_id));
      },
      r.run_id,
    );

  const approve = (r: RunState) =>
    act(
      "approve",
      async () => {
        const state = await api.approve(r.run_id);
        setRun(state);
        await refreshPublished();
      },
      r.run_id,
    );

  if (!session.me) return <SessionGate session={session} />;

  const working = busy !== null;
  // Com exceção na execução (por exemplo RX-12), não há texto de justificativa, mesmo que o corpo traga um.
  const justification = run && !run.exception ? run.justification : null;
  const live = busy ? BUSY_LABELS[busy] : run ? `Execução ${phaseLabel(run.phase).toLowerCase()}.` : "";

  return (
    <Shell who={session.who} area="escala" onLogout={logout} onReset={run || problem ? reset : undefined} busy={working}>
      <p role="status" aria-live="polite" className="sr-only">
        {live}
      </p>

      <h1 className="text-[32px] font-semibold leading-[1.1] tracking-[-0.035em]">Escala da semana</h1>

      {(problem ?? session.problem) && (
        <>
          <Notice>{(problem ?? session.problem)!.message}</Notice>
          {problem?.exception && <ExceptionPanel card={problem.exception} />}
        </>
      )}

      {!run && (
        <>
          {published?.version && (
            <ScheduleView
              id="escala-vigente"
              title="Escala vigente"
              schedule={published.version.schedule}
              employees={published.employees}
              note={`Criada em ${timeBr(published.version.created_at)} · ${published.version.violations_total} violações das regras`}
            />
          )}
          <UploadPanel
            title={published?.version ? "Planejar uma nova escala" : "Enviar a escala atual"}
            busy={busy === "upload"}
            onFile={(f) => send(async () => ({ name: f.name, blob: f }))}
            onDemo={(name) => send(async () => ({ name, blob: await api.demoFile(name) }))}
          />
          {published?.version && (
            <div className="flex flex-wrap items-center gap-3">
              <Button variant="secondary" onClick={planNextWeek} disabled={working} aria-busy={busy === "nextweek"}>
                {busy === "nextweek" ? "Preparando…" : "Planejar a próxima semana"}
              </Button>
              <Muted>Sem novo arquivo: parte da escala vigente e do quadro já confirmado.</Muted>
            </div>
          )}
        </>
      )}

      {run && (
        <>
          <p className="text-sm text-ink-muted">
            Execução <span className="tabular font-medium text-ink">{run.run_id}</span> · {phaseLabel(run.phase)}
          </p>

          {run.summary && (
            <SummaryPanel
              key={run.run_id}
              summary={run.summary}
              mode={run.mode}
              canConfirm={run.phase === "awaiting_confirm"}
              busy={busy === "confirm"}
              onConfirm={(input) => confirm(run, input)}
            />
          )}

          {busy === "confirm" && (
            <PatWorking
              title="O Pat está montando a escala"
              steps={[
                "Otimiza a semana dentro da lei, da convenção e da política (cerca de 20 s)",
                "Confere a proposta com um verificador independente",
                "Compara antes e depois com a mesma função de custo",
                "Escreve a justificativa com o modelo (cerca de 15 s)",
              ]}
            />
          )}

          {run.exception && <ExceptionPanel card={run.exception} />}
          <NoticeList notices={run.notices} />

          {run.comparison && <ComparePanel comparison={run.comparison} />}
          {run.spec && proposed && !run.exception && <SpecApplied spec={run.spec} employees={proposed.employees} />}
          {justification && <JustificationPanel justification={justification} />}

          {run.phase === "awaiting_approval" && proposed && (
            <>
              <ScheduleView
                id="grade-proposta"
                title="Grade semanal proposta"
                schedule={proposed.schedule}
                employees={proposed.employees}
                note="Proposta do Pat. Só vale depois da aprovação do gestor."
              />
              <div className="flex flex-wrap items-center gap-3">
                <Button onClick={() => approve(run)} disabled={working} aria-busy={busy === "approve"}>
                  {busy === "approve" ? "Publicando…" : "Aprovar e publicar"}
                </Button>
                <Muted>Ato do gestor: fica gravado com quem aprovou e quando.</Muted>
              </div>
            </>
          )}

          {run.phase === "published" && published?.version && (
            <>
              <ScheduleView
                id="grade-publicada"
                title="Grade publicada"
                schedule={published.version.schedule}
                employees={published.employees}
                note={`Versão ${published.version.id} · ${published.version.violations_total} violações · criada em ${timeBr(published.version.created_at)}`}
              />
              <div className="flex flex-wrap items-center gap-3">
                <Button onClick={planNextWeek} disabled={working} aria-busy={busy === "nextweek"}>
                  {busy === "nextweek" ? "Preparando…" : "Planejar a próxima semana"}
                </Button>
                <Muted>Sem novo arquivo: o antes é esta escala levada para a semana seguinte.</Muted>
              </div>
            </>
          )}

          <TracePanel events={trace} />
        </>
      )}
    </Shell>
  );
}
