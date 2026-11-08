type Tone = "good" | "bad";

const toneText: Record<Tone, string> = { good: "text-accent-strong", bad: "text-danger" };

type Props = {
  value: string;
  label: string;
  /** Contexto abaixo do rótulo ("meta 0", "medido no trace", "premissa"). O estado é dito em texto, não só pela cor. */
  note?: string;
  tone?: Tone;
  /** `sm` para valores longos (R$ 12.345,67) em grades de vários números. */
  size?: "md" | "sm";
};

export function ImpactStat({ value, label, note, tone, size = "md" }: Props) {
  const sm = size === "sm";
  return (
    <div className={`rounded-card bg-surface ${sm ? "p-5" : "p-7"}`}>
      <div className={`tabular font-bold leading-none tracking-[-0.045em] ${sm ? "text-[28px]" : "text-[40px]"} ${tone ? toneText[tone] : ""}`}>
        {value}
      </div>
      <p className={`leading-normal text-ink-muted ${sm ? "mt-2 text-sm" : "mt-3"}`}>{label}</p>
      {note && <p className="mt-1 text-xs text-ink-muted">{note}</p>}
    </div>
  );
}
