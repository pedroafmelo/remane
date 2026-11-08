import { toExceptionView } from "@/lib/exception";
import type { ExceptionCard as Card } from "@/lib/types";
import { ExceptionCard } from "../ExceptionCard";

/** Liga o cartão do backend (RX-12, RX-13, recusa de publicação) ao componente do design system. */
export function ExceptionPanel({ card }: { card: Card }) {
  const v = toExceptionView(card);
  const facts = [
    { label: "Quem decide", value: v.decider },
    ...(v.recommendation ? [{ label: "Recomendação", value: v.recommendation }] : []),
    ...(v.ifNoAnswer ? [{ label: "Se ninguém responder", value: v.ifNoAnswer }] : []),
  ];
  return <ExceptionCard chip={v.chip} time={v.time} title={v.title} reason={v.reason} options={v.options} evidence={v.evidence} facts={facts} />;
}
