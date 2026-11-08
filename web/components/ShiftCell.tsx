export type ShiftKind = "shift" | "off" | "sick" | "moved";

export type ShiftCellProps = { kind: ShiftKind; label: string; alert?: boolean };

const styles: Record<ShiftKind, string> = {
  shift: "bg-[#f1f2ee] font-medium",
  off: "border-[1.5px] border-dashed border-line-strong text-ink-subtle",
  sick: "bg-[repeating-linear-gradient(135deg,#eceee9_0_6px,#f6f7f3_6px_12px)] text-ink-subtle line-through",
  moved: "bg-accent font-medium text-ink shadow-accent animate-pop",
};

export function ShiftCell({ kind, label, alert }: ShiftCellProps) {
  return (
    <div
      className={`tabular grid min-h-9 place-items-center rounded-cell px-1 text-center text-[13px] outline-2 transition-[outline-color,background-color,color,box-shadow] duration-300 sm:min-h-11 sm:text-sm ${styles[kind]} ${
        alert ? "outline-warning" : "outline-transparent"
      }`}
    >
      {label}
    </div>
  );
}
