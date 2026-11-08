import type { Justification } from "@/lib/types";
import { ChatBubble } from "../ChatBubble";
import { StatusChip } from "../StatusChip";
import { Card } from "./ui";

/** A justificativa do Pat, com as regras citadas. Quem chama só renderiza isto sem `exception` na execução. */
export function JustificationPanel({ justification }: { justification: Justification }) {
  return (
    <Card title="Por que o Pat propôs esta escala" id="justificativa">
      <div className="flex flex-col gap-2 rounded-card bg-surface-chat p-4">
        <ChatBubble from="agent">
          <span className="mb-1 block text-xs font-medium text-accent-strong">Pat</span>
          {justification.summary}
        </ChatBubble>
        {justification.items.map((item, i) => (
          <ChatBubble key={`${i}-${item.text}`} from="agent">
            {item.text}
            {item.rule_refs.length > 0 && (
              <span className="mt-1.5 flex flex-wrap gap-1.5">
                {item.rule_refs.map((r) => (
                  <StatusChip key={r} tone="neutral">
                    {r}
                  </StatusChip>
                ))}
              </span>
            )}
          </ChatBubble>
        ))}
      </div>
    </Card>
  );
}
