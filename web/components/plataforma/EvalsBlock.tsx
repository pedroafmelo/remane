import { countsLine, evalsCommand, isReport, modelRows, rn04Metrics, suiteRows, type Metric } from "@/lib/evals";
import { timeBr } from "@/lib/format";
import type { EvalsReport, EvalsResponse } from "@/lib/types-insights";
import { Pat } from "../Pat";
import { StatusChip } from "../StatusChip";
import { Card, DataTable, Muted, cellCls } from "./ui";

/** Bloco "Evals (dados sintéticos)" do Impacto: o retrato do relatório, só com o que foi medido. */
export function EvalsBlock({ data }: { data: EvalsResponse }) {
  if (!isReport(data)) return <EvalsEmpty />;
  return (
    <Card title="Evals (dados sintéticos)" id="evals" aside="retrato do relatório, não é medição ao vivo">
      <div className="flex flex-col gap-5">
        <Provenance r={data} />
        <Suites r={data} />
        <Rn04 r={data} />
        <ModelUse r={data} />
        <ul className="flex list-disc flex-col gap-1 pl-5 text-sm text-ink-muted">
          <li>
            Cenário <strong className="font-semibold">não executado</strong> (sem chave, teto de orçamento ou saída ausente) nunca conta como aprovado: aparece à parte, em cinza.
          </li>
          <li>&quot;não medido&quot; quer dizer que a rodada não mediu; não é zero.</li>
          {data.privacidade && <li>Privacidade: {data.privacidade}.</li>}
        </ul>
      </div>
    </Card>
  );
}

function EvalsEmpty() {
  return (
    <Card title="Evals (dados sintéticos)" id="evals">
      <div className="flex flex-col items-start gap-4 sm:flex-row sm:items-center">
        <Pat estado="parado" size={48} />
        <p className="text-[15px] leading-relaxed text-ink-muted">Relatório de evals ainda não publicado.</p>
      </div>
    </Card>
  );
}

function Provenance({ r }: { r: EvalsReport }) {
  return (
    <div className="flex flex-col gap-2">
      <p className="tabular text-[15px] font-semibold">{countsLine(r)}</p>
      <div className="flex flex-wrap items-center gap-2 text-[13px] text-ink-muted">
        <StatusChip tone="neutral">{r.modo === "com_modelo" ? "com modelo" : "sem modelo"}</StatusChip>
        <span>gerado em {r.gerado_em ? timeBr(r.gerado_em) : "—"}</span>
        <span>· commit {r.git_sha ? <code className="tabular">{r.git_sha.slice(0, 7)}</code> : "—"}</span>
      </div>
      <code className="tabular block overflow-x-auto whitespace-nowrap rounded-bubble bg-surface-chat px-3 py-2 text-xs text-ink-muted">{evalsCommand(r)}</code>
    </div>
  );
}

function Suites({ r }: { r: EvalsReport }) {
  const rows = suiteRows(r);
  if (rows.length === 0) return <Muted>O relatório não trouxe o placar por suíte.</Muted>;
  const cell = (n: number | null) => (n === null ? "—" : String(n));
  return (
    <DataTable caption="Placar por suíte de evals" head={["Suíte", "Cenários", "Passaram", "Falharam", "Não executados"]}>
      {rows.map((s) => (
        <tr key={s.key}>
          <td className={cellCls}>{s.title}</td>
          <td className={cellCls}>{cell(s.cenarios)}</td>
          <td className={cellCls}>{cell(s.passaram)}</td>
          <td className={`${cellCls} ${s.falharam ? "font-semibold text-danger" : ""}`}>{cell(s.falharam)}</td>
          <td className={`${cellCls} text-ink-subtle`}>{cell(s.naoExecutados)}</td>
        </tr>
      ))}
    </DataTable>
  );
}

function MetricTile({ m }: { m: Metric }) {
  const tone = m.tone === "good" ? "text-accent-strong" : m.tone === "bad" ? "text-danger" : "";
  return (
    <div className="rounded-card border border-line p-4">
      <p className="text-sm text-ink-muted">{m.label}</p>
      <p className={`tabular mt-1 break-words font-bold leading-tight tracking-[-0.03em] ${m.measured ? `text-2xl ${tone}` : "text-lg text-ink-subtle"}`}>{m.value}</p>
      <p className="mt-1 text-xs text-ink-muted">{m.note}</p>
    </div>
  );
}

function Rn04({ r }: { r: EvalsReport }) {
  return (
    <section aria-labelledby="evals-rn04" className="flex flex-col gap-3">
      <h3 id="evals-rn04" className="text-[15px] font-semibold">
        As quatro métricas de resultado
      </h3>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        {rn04Metrics(r).map((m) => (
          <MetricTile key={m.label} m={m} />
        ))}
      </div>
    </section>
  );
}

function ModelUse({ r }: { r: EvalsReport }) {
  return (
    <section aria-labelledby="evals-modelo" className="flex flex-col gap-3">
      <h3 id="evals-modelo" className="text-[15px] font-semibold">
        Modelo na rodada
      </h3>
      <dl className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {modelRows(r).map((row) => (
          <div key={row.label} className="rounded-bubble bg-surface-chat px-3 py-2">
            <dt className="text-xs text-ink-muted">{row.label}</dt>
            <dd className={`tabular text-[15px] font-semibold ${row.measured ? "" : "text-ink-subtle"}`}>{row.value}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}
