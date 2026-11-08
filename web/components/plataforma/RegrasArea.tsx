"use client";

import { useState } from "react";
import { asFailure } from "@/lib/api";
import { insightsApi } from "@/lib/api-insights";
import type { Failure } from "@/lib/errors";
import { dateBr, hours, latency, money, pct, ruleStatusLabel } from "@/lib/format";
import type { RegimeResult, RuleGroup, RulesView, VigenciaSimulation } from "@/lib/types-insights";
import type { ChipTone } from "../StatusChip";
import { Button } from "../Button";
import { ImpactStat } from "../ImpactStat";
import { Pat } from "../Pat";
import { StatusChip } from "../StatusChip";
import { Shell } from "./Shell";
import { SessionGate, useSession } from "./session";
import { Card, DataTable, Muted, Notice, cellCls } from "./ui";

const STATUS_TONE: Record<string, ChipTone> = { conferida: "ok", interpretacao: "neutral", pendente: "warning", ficticia: "neutral" };

export function RegrasArea() {
  const [rules, setRules] = useState<RulesView | null>(null);
  const [problem, setProblem] = useState<Failure | null>(null);
  const session = useSession("gestor", async () => {
    try {
      setRules(await insightsApi.rules());
    } catch (err) {
      setProblem(asFailure(err));
    }
  });
  if (!session.me) return <SessionGate session={session} />;
  return (
    <Shell who={session.who} area="regras" onLogout={session.logout}>
      <h1 className="text-[32px] font-semibold leading-[1.1] tracking-[-0.035em]">Regras</h1>
      <SimulationCard />
      {problem && <Notice>{problem.message}</Notice>}
      {rules && (
        <>
          <Muted>
            Cartão de regras em vigor na semana da demo ({dateBr(rules.reference_date)}), montado pelo mesmo carregador que o motor usa. Convenção e
            política são fictícias.
          </Muted>
          {rules.groups.map((g) => (
            <GroupCard key={g.layer} group={g} />
          ))}
        </>
      )}
    </Shell>
  );
}

function GroupCard({ group }: { group: RuleGroup }) {
  const used = group.rules.filter((r) => r.engine).length;
  return (
    <Card title={group.title} id={`camada-${group.layer}`} aside={`${used} de ${group.rules.length} usadas pelo motor`}>
      <DataTable caption={`Regras da camada ${group.title}`} head={["Regra", "O que limita", "Status", "Origem", "No motor"]}>
        {group.rules.map((r) => (
          <tr key={r.id}>
            <th scope="row" className={`${cellCls} font-medium`}>
              {r.title}
            </th>
            <td className={`${cellCls} max-w-[340px] text-ink-muted`}>
              <span className="line-clamp-3" title={r.limit}>
                {r.limit || "—"}
              </span>
            </td>
            <td className={cellCls}>
              <StatusChip tone={STATUS_TONE[r.status] ?? "neutral"}>{ruleStatusLabel(r.status)}</StatusChip>
            </td>
            <td className={`${cellCls} text-ink-muted`}>{r.source}</td>
            <td className={cellCls}>
              {r.engine ? (
                <StatusChip tone="ok">usada{r.provisional ? " · provisória" : ""}</StatusChip>
              ) : (
                <span className="text-ink-muted">{r.escalates ? "informativa · escala ao humano" : "informativa"}</span>
              )}
            </td>
          </tr>
        ))}
      </DataTable>
    </Card>
  );
}

const ROWS: [string, (r: RegimeResult) => string][] = [
  ["Custo total", (r) => money(r.metrics.total_cost)],
  ["Horas normais", (r) => hours(r.metrics.regular_hours)],
  ["Horas extras", (r) => hours(r.metrics.overtime_hours)],
  ["Cobertura da demanda", (r) => pct(r.metrics.coverage_pct)],
  ["Faixas sem cobertura", (r) => String(r.metrics.uncovered_slots)],
  ["Pessoa-horas sem cobertura", (r) => hours(r.uncovered_person_hours)],
  ["Violações (regras do próprio regime)", (r) => String(r.metrics.violations)],
  ["Violações contra a EC 141", (r) => String(r.violations_under_ec141)],
  ["Tempo do solver (medido)", (r) => latency(r.solve_ms)],
];

function SimulationCard() {
  const [sim, setSim] = useState<VigenciaSimulation | null>(null);
  const [busy, setBusy] = useState(false);
  const [problem, setProblem] = useState<Failure | null>(null);

  async function run() {
    setBusy(true);
    setProblem(null);
    try {
      setSim(await insightsApi.simulateVigencia());
    } catch (err) {
      setProblem(asFailure(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card title="E se a EC 141 não estivesse em vigor?" id="simulacao" aside={<StatusChip tone="warning">vigência simulada · dados sintéticos</StatusChip>}>
      <div className="flex flex-col gap-5">
        <div className="flex items-start gap-4">
          <Pat estado={busy ? "trabalhando" : sim ? "resolveu" : "parado"} size={48} />
          <div className="flex flex-col gap-3">
            <p className="text-[15px] leading-relaxed" role="status">
              {busy
                ? "O Pat está otimizando as duas versões (~30 s)."
                : "O Pat resolve a mesma semana duas vezes: com as regras de antes da EC 141 (44 h por semana, 1 dia de repouso) e com as de agora (42 h, 2 dias). Você compara e decide; nada muda na escala."}
            </p>
            {!sim && (
              <div>
                <Button onClick={run} disabled={busy} aria-busy={busy}>
                  {busy ? "Otimizando…" : "Simular 44 h × 42 h"}
                </Button>
              </div>
            )}
          </div>
        </div>
        {problem && <Notice>{problem.message}</Notice>}
        {sim && <SimulationResult sim={sim} />}
      </div>
    </Card>
  );
}

function SimulationResult({ sim }: { sim: VigenciaSimulation }) {
  const { before, after } = sim;
  const diff = Number(sim.cost_of_ec141);
  const hiring = after.hiring;
  return (
    <>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        <ImpactStat
          size="sm"
          label="Custo de cumprir a EC 141 nesta semana"
          value={`${diff > 0 ? "+" : ""}${money(sim.cost_of_ec141)}`}
          note="custo 42 h − custo 44 h, pela mesma função de custo"
        />
        <ImpactStat size="sm" label="Cobertura (42 h − 44 h)" value={`${sim.coverage_change_pct > 0 ? "+" : ""}${pct(sim.coverage_change_pct).replace("%", " p.p.")}`} note="cobertura da demanda, medida" />
        <ImpactStat
          size="sm"
          label="Violações da escala de 44 h contra a EC 141"
          value={String(before.violations_under_ec141)}
          tone={before.violations_under_ec141 > 0 ? "bad" : undefined}
          note="pelo verificador independente"
        />
      </div>
      <DataTable caption="A mesma semana sob o regime anterior e o atual" head={["", before.label, after.label]}>
        <tr>
          <th scope="row" className={`${cellCls} font-medium`}>
            Regras usadas
          </th>
          {[before, after].map((r) => (
            <td key={r.regime} className={`${cellCls} text-[13px] text-ink-muted`}>
              <ul className="flex flex-col gap-1">
                {r.limits.map((l) => (
                  <li key={l}>{l}</li>
                ))}
              </ul>
            </td>
          ))}
        </tr>
        {ROWS.map(([label, fmt]) => (
          <tr key={label}>
            <th scope="row" className={`${cellCls} font-medium`}>
              {label}
            </th>
            <td className={cellCls}>{fmt(before)}</td>
            <td className={cellCls}>{fmt(after)}</td>
          </tr>
        ))}
      </DataTable>
      {hiring && (
        <Notice tone="warning" role="status">
          {hiring.reason} {hiring.recommendation}
        </Notice>
      )}
      <div className="rounded-bubble bg-surface-chat px-4 py-3 text-[15px] leading-relaxed">
        <strong className="font-semibold">Recomendação do Pat:</strong> seguir com a escala de 42 h.
        {before.violations_under_ec141 > 0 && ` A de 44 h quebraria a EC 141 em ${before.violations_under_ec141} pontos nesta semana.`} A decisão é sua;
        nenhuma escala foi alterada.
      </div>
      <ul className="flex list-disc flex-col gap-1 pl-5 text-sm text-ink-muted">
        {sim.notes.map((n) => (
          <li key={n}>{n}</li>
        ))}
        <li>{sim.cached ? "Resultado do cache: as mesmas entradas já foram resolvidas." : "Calculado agora."}</li>
      </ul>
    </>
  );
}
