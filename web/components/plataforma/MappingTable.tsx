import { FORMAT_LABELS, mappingRows, mappingSourceLabel } from "@/lib/confirm";
import type { ReadSummary } from "@/lib/types";
import { StatusChip } from "../StatusChip";
import { DataTable, Muted, cellCls } from "./ui";

/** Como o arquivo foi entendido: formato, fonte do mapeamento, coluna → campo e o que o agente assumiu. */
export function MappingTable({ summary }: { summary: ReadSummary }) {
  const rows = summary.mapping ? mappingRows(summary.mapping) : [];
  const weak = summary.mapping_source === "heuristica";
  return (
    <div className="mt-5">
      <h3 className="mb-2 text-base font-bold tracking-[-0.02em]">Como o arquivo foi entendido</h3>
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <StatusChip tone="neutral">{FORMAT_LABELS[summary.format]}</StatusChip>
        <StatusChip tone={weak ? "warning" : "ok"}>{mappingSourceLabel(summary.mapping_source)}</StatusChip>
        {summary.mapping && <StatusChip tone="neutral">{summary.mapping.layout === "grid" ? "grade: pessoa por dia" : "lista: um turno por linha"}</StatusChip>}
      </div>
      {rows.length > 0 ? (
        <DataTable caption="Coluna do arquivo e o campo que ela alimenta" head={["Campo", "Coluna do arquivo"]}>
          {rows.map((r) => (
            <tr key={r.field}>
              <th scope="row" className={`${cellCls} font-medium`}>
                {r.field}
              </th>
              <td className={cellCls}>{r.column}</td>
            </tr>
          ))}
        </DataTable>
      ) : (
        <Muted>
          {summary.mapping_source === "plataforma"
            ? "Sem arquivo: a base é a última escala publicada e o quadro confirmado."
            : "Formato padrão do projeto: as colunas já vêm nos campos esperados."}
        </Muted>
      )}
      {summary.assumptions.length > 0 && (
        <div role="note" className="mt-4 rounded-bubble border border-[#f4d6ad] bg-warning-soft px-4 py-3 text-warning-ink">
          <p className="mb-1.5 text-[15px] font-bold">Confirme estas suposições do agente</p>
          <ul className="list-disc pl-5 text-sm">
            {summary.assumptions.map((a, i) => (
              <li key={`${i}-${a}`}>{a}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
