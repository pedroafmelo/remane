"use client";

import { useEffect, useId, useMemo, useState } from "react";
import { api } from "@/lib/api";
import { NOTE_MAX, blockers, buildConfirmInput, emptyForm, fitAll, storeOptions, weekWasShifted } from "@/lib/confirm";
import { dateBr, hours } from "@/lib/format";
import type { ConfirmInput, ReadSummary, RunState } from "@/lib/types";
import { Button } from "../Button";
import { ImpactStat } from "../ImpactStat";
import { CapacityPanel } from "./CapacityPanel";
import { IdentityCards } from "./IdentityCards";
import { MappingTable } from "./MappingTable";
import { Card, DataTable, Muted, cellCls } from "./ui";

const fieldCls = "h-11 rounded-bubble border border-line-strong bg-surface px-3.5 text-[15px] focus-visible:outline-2";

/** Resumo da leitura (RF-23): o gestor confere, corrige o que precisar e confirma. */
export function SummaryPanel({
  summary,
  mode,
  canConfirm,
  busy,
  onConfirm,
}: {
  summary: ReadSummary;
  mode: RunState["mode"];
  canConfirm: boolean;
  busy: boolean;
  onConfirm: (input: ConfirmInput) => void;
}) {
  const ids = { wage: useId(), week: useId(), note: useId() };
  const [form, setForm] = useState(emptyForm);
  const [rosterStores, setRosterStores] = useState<{ id: string; name: string }[] | null>(null);
  const editable = canConfirm && summary.ok;

  // O quadro guardado dá as lojas quando o resumo não traz a lista (404 = ainda não há quadro).
  const needsRoster = editable && summary.capacity !== null && !(summary.store_ids && summary.store_ids.length > 0);
  useEffect(() => {
    if (!needsRoster) return;
    let cancelled = false;
    api
      .roster()
      .then((r) => !cancelled && setRosterStores(r.stores))
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, [needsRoster]);

  const stores = useMemo(() => storeOptions(summary, rosterStores), [summary, rosterStores]);
  const storeIds = useMemo(() => stores.map((s) => s.id), [stores]);
  const stops = blockers(summary, mode, form);
  const shifted = weekWasShifted(summary, form.plannedWeek);
  const plannedWeek = summary.planned_week_start ?? summary.week_start;

  return (
    <Card title="Resumo da leitura" id="resumo" aside={summary.file_name}>
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
        <ImpactStat size="sm" label="Linhas" value={String(summary.rows)} />
        <ImpactStat size="sm" label="Pessoas" value={String(summary.employees)} />
        <ImpactStat size="sm" label="Lojas" value={String(summary.stores)} />
        <ImpactStat size="sm" label="Semana (segunda)" value={summary.week_start ? dateBr(summary.week_start) : "—"} />
        <ImpactStat size="sm" label="Horas totais" value={hours(summary.total_hours)} />
      </div>

      <MappingTable summary={summary} />

      <div className="mt-5">
        {summary.issues.length > 0 ? (
          <>
            <h3 className="mb-2 text-base font-bold tracking-[-0.02em]">Problemas encontrados ({summary.issues.length})</h3>
            <DataTable caption="Problemas encontrados na leitura" head={["Linha", "Campo", "Célula", "Motivo"]}>
              {summary.issues.map((issue, i) => (
                <tr key={`${issue.line}-${i}`}>
                  <td className={cellCls}>{issue.line}</td>
                  <td className={cellCls}>{issue.field ?? "—"}</td>
                  <td className={cellCls}>{issue.col != null ? `${issue.table ? `${issue.table}, ` : ""}coluna ${issue.col + 1}` : "—"}</td>
                  <td className={cellCls}>{issue.reason}</td>
                </tr>
              ))}
            </DataTable>
          </>
        ) : (
          <p className="font-medium text-accent-strong">Nenhum problema encontrado na leitura.</p>
        )}
      </div>

      {editable && (
        <>
          <IdentityCards cards={summary.identity} answers={form.identity} onAnswer={(id, same) => setForm((f) => ({ ...f, identity: { ...f.identity, [id]: same } }))} />

          {summary.capacity && (
            <CapacityPanel
              capacity={summary.capacity}
              stores={stores}
              coverage={form.coverage}
              onChange={(id, pct) => setForm((f) => ({ ...f, coverage: { ...f.coverage, [id]: pct } }))}
              onFit={() => setForm((f) => ({ ...f, coverage: fitAll(storeIds, summary.capacity?.max_fitting_pct ?? 100) }))}
            />
          )}

          <div className="mt-5 grid gap-4 sm:grid-cols-2">
            <div className="flex flex-col gap-1.5">
              <label htmlFor={ids.wage} className="text-sm font-medium">
                Salário-hora único (opcional)
              </label>
              <input
                id={ids.wage}
                inputMode="decimal"
                autoComplete="off"
                placeholder="ex.: 18,50"
                value={form.wage}
                onChange={(e) => setForm((f) => ({ ...f, wage: e.target.value }))}
                aria-describedby={`${ids.wage}-help`}
                className={fieldCls}
              />
              <p id={`${ids.wage}-help`} className="text-xs text-ink-muted">
                Em reais por hora, para quem o arquivo não traz salário. Em branco, vale o que o arquivo ou o cadastro simulado trouxer.
              </p>
            </div>

            {mode === "upload" ? (
              <div className="flex flex-col gap-1.5">
                <label htmlFor={ids.week} className="text-sm font-medium">
                  Semana a planejar (segunda-feira)
                </label>
                <input
                  id={ids.week}
                  type="date"
                  value={form.plannedWeek}
                  onChange={(e) => setForm((f) => ({ ...f, plannedWeek: e.target.value }))}
                  aria-describedby={`${ids.week}-help`}
                  className={fieldCls}
                />
                <p id={`${ids.week}-help`} className="text-xs text-ink-muted">
                  {shifted && summary.week_start
                    ? `Escala enviada (${dateBr(summary.week_start)}), levada para a semana de ${dateBr(form.plannedWeek)}: o "antes" é a escala do arquivo deslocada em semanas inteiras.`
                    : summary.week_start
                      ? `Em branco, vale a semana do arquivo (${dateBr(summary.week_start)}).`
                      : "O arquivo não traz a data: escolha a segunda-feira da semana."}
                </p>
              </div>
            ) : (
              <div className="flex flex-col gap-1.5">
                <span className="text-sm font-medium">Semana planejada</span>
                <p className="flex h-11 items-center text-[15px]">{plannedWeek ? dateBr(plannedWeek) : "—"}</p>
                <p className="text-xs text-ink-muted">A seguinte à última escala publicada.</p>
              </div>
            )}
          </div>

          <div className="mt-4 flex flex-col gap-1.5">
            <label htmlFor={ids.note} className="text-sm font-medium">
              Algo a considerar nesta semana?
            </label>
            <textarea
              id={ids.note}
              rows={3}
              maxLength={NOTE_MAX}
              placeholder="ex.: a Ana está de férias na quarta"
              value={form.note}
              onChange={(e) => setForm((f) => ({ ...f, note: e.target.value }))}
              aria-describedby={`${ids.note}-help`}
              className="rounded-bubble border border-line-strong bg-surface px-3.5 py-3 text-[15px] focus-visible:outline-2"
            />
            <p id={`${ids.note}-help`} className="tabular flex justify-between gap-3 text-xs text-ink-muted">
              <span>Texto livre: o agente transforma em pedidos que só restringem, nunca afrouxam a lei.</span>
              <span>
                {form.note.length}/{NOTE_MAX}
              </span>
            </p>
          </div>

          {stops.length > 0 && (
            <ul role="status" className="mt-4 flex flex-col gap-1 rounded-bubble border border-[#f4d6ad] bg-warning-soft px-4 py-3 text-sm font-medium text-warning-ink">
              {stops.map((b) => (
                <li key={b.id}>{b.text}</li>
              ))}
            </ul>
          )}

          <div className="mt-5 flex flex-wrap items-center gap-3">
            <Button onClick={() => onConfirm(buildConfirmInput(form, mode, storeIds))} disabled={busy || stops.length > 0} aria-busy={busy}>
              {busy ? "Otimizando…" : "Confirmar a leitura"}
            </Button>
            <Muted>Confirma que a leitura está certa e libera a otimização.</Muted>
          </div>
        </>
      )}
    </Card>
  );
}
