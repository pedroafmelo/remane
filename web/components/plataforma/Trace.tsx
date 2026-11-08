import { costUsd, latency, ruleStatusLabel, timeBr } from "@/lib/format";
import type { TraceEvent } from "@/lib/types";
import { StatusChip } from "../StatusChip";
import { Card, DataTable, Muted, cellCls } from "./ui";

/** Status de regra só aparece se o evento o trouxer no payload (a API não o inventa). */
function ruleStatus(e: TraceEvent): string | undefined {
  const v = e.payload["rule_status"];
  return typeof v === "string" ? v : undefined;
}

/** Tokens de entrada e saída de um evento de modelo; "—" quando o evento não chamou modelo. */
function tokens(e: TraceEvent): string {
  if (e.tokens_in === null && e.tokens_out === null) return "—";
  return `${e.tokens_in ?? "?"} / ${e.tokens_out ?? "?"}`;
}

/** Custo: num evento de modelo sem custo medido, diz "não medido" (nunca estima). */
function cost(e: TraceEvent): string {
  return e.cost_usd === null && e.model ? "não medido" : costUsd(e.cost_usd);
}

type Props = {
  events: TraceEvent[];
  title?: string;
  id?: string;
  /** horas no tempo simulado do relógio de demo (acompanhamento) */
  simulated?: boolean;
};

export function TracePanel({ events, title = "Rastro da execução", id = "rastro", simulated = false }: Props) {
  const total = events.reduce((acc, e) => acc + (e.cost_usd === null ? 0 : Number(e.cost_usd)), 0);
  const hour = simulated ? "Hora (tempo simulado)" : "Hora";
  return (
    <Card title={title} id={id} aside={`custo medido: ${costUsd(String(total))}`}>
      {events.length === 0 ? (
        <Muted>Nenhum evento ainda.</Muted>
      ) : (
        <DataTable
          caption="Eventos com tokens, custo e latência medidos"
          head={["Evento", hour, "Regra", "Modelo", "Tokens (entrada / saída)", "Custo", "Latência"]}
        >
          {events.map((e) => {
            const status = ruleStatus(e);
            return (
              <tr key={e.id}>
                <td className={`${cellCls} font-medium`}>{e.kind}</td>
                <td className={`${cellCls} whitespace-nowrap`}>{timeBr(e.at)}</td>
                <td className={cellCls}>{e.rule_ref ? <StatusChip tone="neutral">{status ? `${e.rule_ref} · ${ruleStatusLabel(status)}` : e.rule_ref}</StatusChip> : "—"}</td>
                <td className={cellCls}>{e.model ?? "—"}</td>
                <td className={`${cellCls} whitespace-nowrap tabular`}>{tokens(e)}</td>
                <td className={`${cellCls} whitespace-nowrap`}>{cost(e)}</td>
                <td className={`${cellCls} whitespace-nowrap`}>{latency(e.latency_ms)}</td>
              </tr>
            );
          })}
        </DataTable>
      )}
    </Card>
  );
}
