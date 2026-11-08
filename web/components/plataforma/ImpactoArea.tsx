"use client";

import { useState } from "react";
import { api, asFailure } from "@/lib/api";
import { insightsApi } from "@/lib/api-insights";
import type { Failure } from "@/lib/errors";
import { costUsd, hours, latency, money, pct, phaseLabel, timeBr } from "@/lib/format";
import type { TraceEvent } from "@/lib/types";
import type { EvalsResponse, Impact, RunImpact } from "@/lib/types-insights";
import { Button } from "../Button";
import { EvalsBlock } from "./EvalsBlock";
import { ImpactStat } from "../ImpactStat";
import { Pat } from "../Pat";
import { Shell } from "./Shell";
import { TracePanel } from "./Trace";
import { SessionGate, useSession } from "./session";
import { Card, DataTable, Muted, Notice, cellCls } from "./ui";

export function ImpactoArea() {
  const [data, setData] = useState<Impact | null>(null);
  const [evals, setEvals] = useState<EvalsResponse | null>(null);
  const [problem, setProblem] = useState<Failure | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [trace, setTrace] = useState<TraceEvent[] | null>(null);
  const session = useSession("gestor", async () => {
    try {
      setData(await insightsApi.impact());
    } catch (err) {
      setProblem(asFailure(err));
    }
    try {
      setEvals(await insightsApi.evals());
    } catch {
      setEvals({ status: "sem_relatorio" }); // o bloco de evals nunca derruba o Impacto
    }
  });

  async function openTrace(runId: string) {
    setSelected(runId);
    setTrace(null);
    try {
      setTrace(await api.trace(runId));
    } catch (err) {
      setProblem(asFailure(err));
    }
    document.getElementById("rastro-da-execucao")?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  const toRuns = () => document.getElementById("execucoes")?.scrollIntoView({ behavior: "smooth", block: "start" });

  if (!session.me) return <SessionGate session={session} />;
  return (
    <Shell who={session.who} area="impacto" onLogout={session.logout}>
      <h1 className="text-[32px] font-semibold leading-[1.1] tracking-[-0.035em]">Impacto</h1>
      {problem && <Notice>{problem.message}</Notice>}
      {data && data.runs_total === 0 && <Empty />}
      {data && data.runs_total > 0 && (
        <>
          <Tiles data={data} onCurrent={() => data.current && openTrace(data.current.run_id)} onRuns={toRuns} />
          <RunsTable runs={data.runs} total={data.runs_total} selected={selected} onOpen={openTrace} />
          {selected && (
            <div id="rastro-da-execucao" className="scroll-mt-4">
              {trace ? <TracePanel events={trace} /> : <Muted>Carregando o rastro…</Muted>}
            </div>
          )}
        </>
      )}
      {evals && <EvalsBlock data={evals} />}
    </Shell>
  );
}

function Empty() {
  return (
    <Card title="Nada medido ainda" id="vazio">
      <div className="flex flex-col items-start gap-4 sm:flex-row sm:items-center">
        <Pat estado="parado" size={48} />
        <p className="text-[15px] leading-relaxed text-ink-muted">
          O painel mostra só o que foi medido nas execuções do agente. Envie e publique uma escala para ver economia, horas extras evitadas e o custo do
          agente aqui.
        </p>
        <Button href="/plataforma/" variant="secondary">
          Ir para a Escala
        </Button>
      </div>
    </Card>
  );
}

/** Um número clicável: leva ao rastro (comparação) ou à lista de execuções (agente). */
function Tile({ onClick, hint, wide, ...stat }: Parameters<typeof ImpactStat>[0] & { onClick: () => void; hint: string; wide?: boolean }) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label={`${stat.label}: ${stat.value}. ${hint}`}
      className={`${wide ? "col-span-2 lg:col-span-1 " : ""}rounded-card border border-line text-left outline-offset-2 transition-colors hover:border-ink-subtle focus-visible:outline-2`}
    >
      <ImpactStat size="sm" {...stat} />
    </button>
  );
}

function Tiles({ data, onCurrent, onRuns }: { data: Impact; onCurrent: () => void; onRuns: () => void }) {
  const c = data.current;
  const toTrace = "Abre o rastro da execução publicada.";
  const toList = "Vai para a lista de execuções.";
  return (
    <Card title="Números medidos" id="numeros" aside="clique num número para auditar">
      <div className="flex flex-col gap-4">
        {c ? (
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            <Tile wide onClick={onCurrent} hint={toTrace} label="Economia na semana" value={money(c.savings ?? "0")} tone="good" note={`antes ${money(c.cost_before ?? "0")} · depois ${money(c.cost_after ?? "0")}`} />
            <Tile onClick={onCurrent} hint={toTrace} label="Horas extras evitadas" value={hours(c.overtime_hours_avoided ?? "0")} note="mesma função de custo" />
            <Tile onClick={onCurrent} hint={toTrace} label="Violações evitadas" value={String(c.violations_avoided ?? 0)} note="verificador independente" />
            <Tile onClick={onCurrent} hint={toTrace} label="Cobertura depois" value={pct(c.coverage_after ?? 0)} note="da demanda sintética" />
          </div>
        ) : (
          <Muted>Nenhuma escala publicada ainda: os números de custo aparecem depois da primeira publicação.</Muted>
        )}
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-3">
          <Tile wide onClick={onRuns} hint={toList} label="Custo do agente (total)" value={costUsd(data.agent_cost_usd_total)} note="medido no rastro" />
          <Tile onClick={onRuns} hint={toList} label="Execuções" value={String(data.runs_total)} note={`${data.runs_published} publicada(s)`} />
          <Tile onClick={onRuns} hint={toList} label="Latência média por execução" value={latency(data.agent_latency_ms_avg)} note="soma das latências no rastro" />
        </div>
        <ul className="flex list-disc flex-col gap-1 pl-5 text-sm text-ink-muted">
          <li>{data.provenance.comparison}</li>
          <li>{data.provenance.agent}</li>
          <li>{data.provenance.scope}</li>
        </ul>
      </div>
    </Card>
  );
}

function RunsTable({ runs, total, selected, onOpen }: { runs: RunImpact[]; total: number; selected: string | null; onOpen: (id: string) => void }) {
  return (
    <div id="execucoes" className="scroll-mt-4">
      <Card title="Execuções" id="execucoes-titulo" aside={runs.length < total ? `últimas ${runs.length} de ${total}` : `${total}`}>
        <DataTable caption="Execuções do agente com os números de cada uma" head={["Início", "Fase", "Economia", "Cobertura", "Custo do agente", "Latência", ""]}>
          {runs.map((r) => (
            <tr key={r.run_id} className={r.run_id === selected ? "bg-surface-chat" : undefined}>
              <td className={`${cellCls} whitespace-nowrap`}>{r.started_at ? timeBr(r.started_at) : "—"}</td>
              <td className={cellCls}>{phaseLabel(r.phase)}</td>
              <td className={`${cellCls} whitespace-nowrap`}>{r.savings === null ? "—" : money(r.savings)}</td>
              <td className={cellCls}>{r.coverage_after === null ? "—" : pct(r.coverage_after)}</td>
              <td className={`${cellCls} whitespace-nowrap`}>{costUsd(r.agent_cost_usd)}</td>
              <td className={`${cellCls} whitespace-nowrap`}>{latency(r.agent_latency_ms)}</td>
              <td className={cellCls}>
                <Button size="sm" variant="secondary" onClick={() => onOpen(r.run_id)}>
                  Ver rastro
                </Button>
              </td>
            </tr>
          ))}
        </DataTable>
        <div className="mt-3">
          <Muted>Números de cada execução gravados por ela mesma; &quot;—&quot; quando a execução não chegou à comparação.</Muted>
        </div>
      </Card>
    </div>
  );
}
