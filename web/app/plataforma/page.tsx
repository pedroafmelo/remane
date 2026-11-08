"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, asFailure } from "@/lib/api";
import type { Failure } from "@/lib/errors";
import { phaseLabel, timeBr } from "@/lib/format";
import { canOperateSchedule, roleLabel } from "@/lib/roles";
import type { Me, ProposedSchedule, PublishedSchedule, RunState, TraceEvent } from "@/lib/types";
import { Button } from "@/components/Button";
import { ComparePanel } from "@/components/plataforma/Compare";
import { ExceptionPanel } from "@/components/plataforma/ExceptionPanel";
import { JustificationPanel } from "@/components/plataforma/Justification";
import { ScheduleView } from "@/components/plataforma/ScheduleView";
import { Shell } from "@/components/plataforma/Shell";
import { SummaryPanel } from "@/components/plataforma/Summary";
import { TracePanel } from "@/components/plataforma/Trace";
import { UploadPanel } from "@/components/plataforma/Upload";
import { Card, Muted, Notice } from "@/components/plataforma/ui";

const BUSY_LABELS: Record<string, string> = {
  upload: "Enviando e lendo o arquivo…",
  confirm: "Otimizando a escala, conferindo as regras e montando a justificativa…",
  approve: "Publicando a escala aprovada…",
  logout: "Saindo…",
};

export default function PlataformaPage() {
  const router = useRouter();
  const [booting, setBooting] = useState(true);
  const [me, setMe] = useState<Me | null>(null);
  const [busy, setBusy] = useState<string | null>(null); // o que está em andamento
  const [problem, setProblem] = useState<Failure | null>(null);
  const [run, setRun] = useState<RunState | null>(null);
  const [proposed, setProposed] = useState<ProposedSchedule | null>(null);
  const [published, setPublished] = useState<PublishedSchedule | null>(null);
  const [trace, setTrace] = useState<TraceEvent[]>([]);

  const toLogin = useCallback(() => router.replace("/entrar/"), [router]);

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

  useEffect(() => {
    let cancelled = false;
    api
      .me()
      .then(async (m) => {
        if (cancelled) return;
        setMe(m);
        if (canOperateSchedule(m.papel)) await refreshPublished();
      })
      .catch((err) => {
        if (cancelled) return;
        const failure = asFailure(err);
        if (failure.kind === "auth") toLogin();
        else setProblem(failure);
      })
      .finally(() => {
        if (!cancelled) setBooting(false);
      });
    return () => {
      cancelled = true;
    };
  }, [refreshPublished, toLogin]);

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

  const logout = () =>
    act("logout", async () => {
      await api.logout();
      reset();
      toLogin();
    });

  /** Envia o CSV (do disco ou de exemplo). Recusas de arquivo (413, 422) voltam com o cartão RX-13 no corpo. */
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

  const confirm = (r: RunState) =>
    act(
      "confirm",
      async () => {
        const state = await api.confirm(r.run_id);
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

  if (booting) {
    return (
      <Shell>
        <p role="status" className="text-ink-muted">
          Carregando…
        </p>
      </Shell>
    );
  }

  if (!me) {
    // sem sessão o redirecionamento já foi pedido; se o servidor não respondeu, a mensagem fica aqui
    return (
      <Shell>
        {problem ? <Notice>{problem.message}</Notice> : <p className="text-ink-muted">Redirecionando para a entrada…</p>}
        <div>
          <Button href="/entrar/" variant="secondary">
            Ir para a entrada
          </Button>
        </div>
      </Shell>
    );
  }

  const who = { nome: me.nome, papelLabel: roleLabel(me.papel) };

  if (!canOperateSchedule(me.papel)) {
    return (
      <Shell who={who} onLogout={logout} busy={busy !== null}>
        {problem && <Notice>{problem.message}</Notice>}
        <Card title="Esta área é do gerente" id="sem-acesso">
          <p className="mb-4 text-[15px] leading-relaxed text-ink-muted">
            Você entrou como {roleLabel(me.papel).toLowerCase()}. Nesta versão, só o gerente envia a escala, confere o antes e o depois e
            aprova a publicação; o servidor recusa essas ações para os demais papéis.
          </p>
          <Button variant="secondary" onClick={logout} disabled={busy !== null}>
            Entrar com outro papel
          </Button>
        </Card>
      </Shell>
    );
  }

  const working = busy !== null;
  // Com exceção na execução (por exemplo RX-12), não há texto de justificativa, mesmo que o corpo traga um.
  const justification = run && !run.exception ? run.justification : null;
  const live = busy ? BUSY_LABELS[busy] : run ? `Execução ${phaseLabel(run.phase).toLowerCase()}.` : "";

  return (
    <Shell who={who} onLogout={logout} onReset={run || problem ? reset : undefined} busy={working}>
      <p role="status" aria-live="polite" className="sr-only">
        {live}
      </p>

      <h1 className="text-[32px] font-semibold leading-[1.1] tracking-[-0.035em]">Escala da semana</h1>

      {problem && (
        <>
          <Notice>{problem.message}</Notice>
          {problem.exception && <ExceptionPanel card={problem.exception} />}
        </>
      )}

      {!run && (
        <>
          <UploadPanel
            busy={busy === "upload"}
            onFile={(f) => send(async () => ({ name: f.name, blob: f }))}
            onDemo={(name) => send(async () => ({ name, blob: await api.demoFile(name) }))}
          />
          {published?.version && (
            <ScheduleView
              id="ultima-publicada"
              title="Última grade publicada"
              schedule={published.version.schedule}
              employees={published.employees}
              note={`Versão ${published.version.id} · ${published.version.violations_total} violações · criada em ${timeBr(published.version.created_at)}`}
            />
          )}
        </>
      )}

      {run && (
        <>
          <p className="text-sm text-ink-muted">
            Execução <span className="tabular font-medium text-ink">{run.run_id}</span> · {phaseLabel(run.phase)}
          </p>

          {run.summary && (
            <SummaryPanel summary={run.summary} canConfirm={run.phase === "awaiting_confirm"} busy={busy === "confirm"} onConfirm={() => confirm(run)} />
          )}

          {run.exception && <ExceptionPanel card={run.exception} />}

          {run.comparison && <ComparePanel comparison={run.comparison} />}
          {justification && <JustificationPanel justification={justification} />}

          {run.phase === "awaiting_approval" && proposed && (
            <>
              <ScheduleView
                id="grade-proposta"
                title="Grade semanal proposta"
                schedule={proposed.schedule}
                employees={proposed.employees}
                note="Proposta do Pat. Só vale depois da aprovação do gerente."
              />
              <div className="flex flex-wrap items-center gap-3">
                <Button onClick={() => approve(run)} disabled={working} aria-busy={busy === "approve"}>
                  {busy === "approve" ? "Publicando…" : "Aprovar e publicar"}
                </Button>
                <Muted>Ato do gerente: fica gravado com quem aprovou e quando.</Muted>
              </div>
            </>
          )}

          {run.phase === "published" && published?.version && (
            <ScheduleView
              id="grade-publicada"
              title="Grade publicada"
              schedule={published.version.schedule}
              employees={published.employees}
              note={`Versão ${published.version.id} · ${published.version.violations_total} violações · criada em ${timeBr(published.version.created_at)}`}
            />
          )}

          <TracePanel events={trace} />
        </>
      )}
    </Shell>
  );
}
