const INK = [
  [4, 4], [24, 4], [44, 4],
  [4, 24], [24, 24],
  [4, 44], [24, 44], [44, 44],
];

type LogoProps = { animated?: boolean; size?: number; mark?: string; block?: string; word?: boolean };

export function LogoMark({ animated = false, size = 32, mark = "#17181a", block = "#2bd48a" }: Omit<LogoProps, "word">) {
  return (
    <svg width={size} height={(size * 64) / 70} viewBox="0 0 70 64" aria-hidden="true" className="shrink-0">
      <g fill={mark}>
        {INK.map(([x, y]) => (
          <rect key={`${x}-${y}`} x={x} y={y} width="16" height="16" rx="5" />
        ))}
      </g>
      {animated ? (
        <>
          <rect x="44.75" y="24.75" width="14.5" height="14.5" rx="4.5" fill="none" stroke="#d5d7d1" strokeWidth="1.5" strokeDasharray="3 2.5" />
          <rect x="44" y="24" width="16" height="16" rx="5" fill={block} className="animate-slide" />
        </>
      ) : (
        <rect x="50" y="18" width="16" height="16" rx="5" fill={block} />
      )}
    </svg>
  );
}

export function Logo({ animated, size = 32, word = true }: LogoProps) {
  return (
    <span className="inline-flex items-center gap-2.5">
      <LogoMark animated={animated} size={size} />
      {word && (
        <span className="font-medium tracking-[-0.06em]" style={{ fontSize: size * 0.72 }}>
          remane
        </span>
      )}
    </span>
  );
}
