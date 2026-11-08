import { costUsd, latency, ruleStatusLabel, timeBr } from "@/lib/format";
import type { TraceEvent } from "@/lib/types";
import { StatusChip } from "../StatusChip";
import { Card, DataTable, Muted, cellCls } from "./ui";

/** Status de regra só aparece se o evento o trouxer no payload (a API não o inventa). */
function ruleStatus(e: TraceEvent): string | undefined {
  const v = e.payload["rule_status"];
  return typeof v === "string" ? v : undefined;
}

export function TracePanel({ events }: { events: TraceEvent[] }) {
  const total = events.reduce((acc, e) => acc + (e.cost_usd === null ? 0 : Number(e.cost_usd)), 0);
  return (
    <Card title="Rastro da execução" id="rastro" aside={`custo medido: ${costUsd(String(total))}`}>
      {events.length === 0 ? (
        <Muted>Nenhum evento ainda.</Muted>
      ) : (
        <DataTable caption="Eventos da execução com custo e latência medidos" head={["Evento", "Hora", "Regra", "Modelo", "Custo", "Latência"]}>
          {events.map((e) => {
            const status = ruleStatus(e);
            return (
              <tr key={e.id}>
                <td className={`${cellCls} font-medium`}>{e.kind}</td>
                <td className={`${cellCls} whitespace-nowrap`}>{timeBr(e.at)}</td>
                <td className={cellCls}>{e.rule_ref ? <StatusChip tone="neutral">{status ? `${e.rule_ref} · ${ruleStatusLabel(status)}` : e.rule_ref}</StatusChip> : "—"}</td>
                <td className={cellCls}>{e.model ?? "—"}</td>
                <td className={`${cellCls} whitespace-nowrap`}>{costUsd(e.cost_usd)}</td>
                <td className={`${cellCls} whitespace-nowrap`}>{latency(e.latency_ms)}</td>
              </tr>
            );
          })}
        </DataTable>
      )}
    </Card>
  );
}
