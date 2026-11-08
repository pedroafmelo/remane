import type { ReactNode } from "react";

const tones = {
  ok: "border-line bg-surface-chat text-ink",
  warning: "border-[#f4d6ad] bg-warning-soft text-warning-ink",
};

export function StatusChip({ tone = "ok", children }: { tone?: keyof typeof tones; children: ReactNode }) {
  return (
    <span className={`tabular inline-block whitespace-nowrap rounded-full border px-3 py-1.5 text-[13px] font-medium transition-colors duration-300 ${tones[tone]}`}>
      {children}
    </span>
  );
}
