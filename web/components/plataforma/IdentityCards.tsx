import { IDENTITY_KIND_LABELS } from "@/lib/confirm";
import type { IdentityCard } from "@/lib/types";
import { StatusChip } from "../StatusChip";

/** Dúvidas de identidade: nunca há fusão automática. A resposta do gestor vai em `ConfirmInput.identity`. */
export function IdentityCards({ cards, answers, onAnswer }: { cards: IdentityCard[]; answers: Record<string, boolean>; onAnswer: (id: string, same: boolean) => void }) {
  if (cards.length === 0) return null;
  return (
    <div className="mt-5">
      <h3 className="mb-2 text-base font-bold tracking-[-0.02em]">Essas pessoas são as mesmas? ({cards.length})</h3>
      <ul className="flex flex-col gap-3">
        {cards.map((c) => {
          const blocking = c.kind === "homonimo" && answers[c.id] === undefined;
          return (
            <li key={c.id}>
              <fieldset className="rounded-bubble border border-line bg-paper px-4 py-3.5">
                <legend className="sr-only">{`${IDENTITY_KIND_LABELS[c.kind]}: ${c.names.join(" e ")}`}</legend>
                <div className="mb-2 flex flex-wrap items-center gap-2">
                  <StatusChip tone={c.kind === "homonimo" ? "warning" : "neutral"}>{IDENTITY_KIND_LABELS[c.kind]}</StatusChip>
                  <span className="text-[15px] font-medium">{c.names.join(" · ")}</span>
                </div>
                <p className="mb-3 text-sm text-ink-muted">
                  {c.reason} <span className="whitespace-nowrap">Sugestão do Pat: {c.suggestion === "mesma" ? "mesma pessoa" : "pessoas diferentes"}.</span>
                </p>
                <div className="flex flex-wrap gap-x-5 gap-y-2 text-[15px]">
                  {([true, false] as const).map((same) => (
                    <label key={String(same)} className="inline-flex cursor-pointer items-center gap-2">
                      <input type="radio" name={`id-${c.id}`} checked={answers[c.id] === same} onChange={() => onAnswer(c.id, same)} className="size-4 accent-accent-strong" />
                      {same ? "Mesma pessoa" : "Pessoas diferentes"}
                    </label>
                  ))}
                </div>
                {blocking && <p className="mt-2 text-xs font-medium text-warning-ink">Resposta necessária para confirmar.</p>}
              </fieldset>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
