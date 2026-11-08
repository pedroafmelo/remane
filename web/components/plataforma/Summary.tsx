import { dateBr, hours } from "@/lib/format";
import type { ReadSummary } from "@/lib/types";
import { Button } from "../Button";
import { ImpactStat } from "../ImpactStat";
import { Card, DataTable, Muted, cellCls } from "./ui";

/** Resumo da leitura (RF-23): o gestor confere antes de confirmar. */
export function SummaryPanel({ summary, canConfirm, busy, onConfirm }: { summary: ReadSummary; canConfirm: boolean; busy: boolean; onConfirm: () => void }) {
  return (
    <Card title="Resumo da leitura" id="resumo" aside={summary.file_name}>
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
        <ImpactStat size="sm" label="Linhas" value={String(summary.rows)} />
        <ImpactStat size="sm" label="Pessoas" value={String(summary.employees)} />
        <ImpactStat size="sm" label="Lojas" value={String(summary.stores)} />
        <ImpactStat size="sm" label="Semana (segunda)" value={summary.week_start ? dateBr(summary.week_start) : "—"} />
        <ImpactStat size="sm" label="Horas totais" value={hours(summary.total_hours)} />
      </div>
      <div className="mt-5">
        {summary.issues.length > 0 ? (
          <>
            <h3 className="mb-2 text-base font-bold tracking-[-0.02em]">Problemas encontrados ({summary.issues.length})</h3>
            <DataTable caption="Problemas encontrados na leitura" head={["Linha", "Campo", "Motivo"]}>
              {summary.issues.map((issue, i) => (
                <tr key={`${issue.line}-${i}`}>
                  <td className={cellCls}>{issue.line}</td>
                  <td className={cellCls}>{issue.field ?? "—"}</td>
                  <td className={cellCls}>{issue.reason}</td>
                </tr>
              ))}
            </DataTable>
          </>
        ) : (
          <p className="font-medium text-accent-strong">Nenhum problema encontrado na leitura.</p>
        )}
      </div>
      {canConfirm && summary.ok && (
        <div className="mt-5 flex flex-wrap items-center gap-3">
          <Button onClick={onConfirm} disabled={busy} aria-busy={busy}>
            {busy ? "Otimizando…" : "Confirmar a leitura"}
          </Button>
          <Muted>Confirma que a leitura está certa e libera a otimização.</Muted>
        </div>
      )}
    </Card>
  );
}
