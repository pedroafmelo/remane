export function ImpactStat({ value, label }: { value: string; label: string }) {
  return (
    <div className="rounded-card bg-surface p-7">
      <div className="tabular text-[40px] font-bold leading-none tracking-[-0.045em]">{value}</div>
      <p className="mt-3 leading-normal text-ink-muted">{label}</p>
    </div>
  );
}
