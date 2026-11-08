import type { ExceptionCard } from "@/lib/types";
import { ExceptionPanel } from "./ExceptionPanel";
import { Muted } from "./ui";

/** Avisos que não bloqueiam (RX-02, RX-12 da leitura e da formulação): o fluxo segue, e o gestor lê e decide depois. */
export function NoticeList({ notices }: { notices: ExceptionCard[] }) {
  if (notices.length === 0) return null;
  return (
    <section aria-label="Avisos que não bloqueiam" className="flex flex-col gap-3">
      <Muted>{notices.length === 1 ? "Um aviso" : `${notices.length} avisos`} desta execução: não bloqueiam o fluxo, mas pedem a sua atenção.</Muted>
      {notices.map((n, i) => (
        <ExceptionPanel key={`${n.code}-${i}`} card={n} />
      ))}
    </section>
  );
}
