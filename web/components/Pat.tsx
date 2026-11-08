import { patLabel, patPose, type PatEstado } from "@/lib/pat";

const INK = "#17181a";
const ACCENT = "#2bd48a";
const WARNING = "#e8890c";

type PatProps = { estado?: PatEstado; size?: number; label?: string; decorativo?: boolean };

/**
 * Pat, o agente do Remane: o bloco remanejado do logo (quadrado accent, rx na proporção do símbolo) com dois olhos.
 * Accent marca o que o agente fez; warning só aparece quando precisa de uma pessoa. Sem movimento com reduced-motion.
 */
export function Pat({ estado = "parado", size = 64, label, decorativo = false }: PatProps) {
  const pose = patPose(estado);
  const eyeY = pose.eyes === "baixo" ? 33 : pose.eyes === "cima" ? 25 : pose.eyes === "concentrado" ? 28 : 29;
  const pupilDx = pose.eyes === "cima" ? 1.5 : pose.eyes === "concentrado" ? 3 : 0;
  const boxStyle = { transformBox: "fill-box", transformOrigin: "center" } as const;
  const motionClass = pose.motion === "slide" ? "animate-slide" : pose.motion === "pop" ? "animate-pop" : undefined;

  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 64 64"
      role={decorativo ? undefined : "img"}
      aria-label={decorativo ? undefined : (label ?? patLabel(estado))}
      aria-hidden={decorativo ? true : undefined}
      className="shrink-0"
    >
      {pose.ghost && (
        <rect x="8.75" y="8.75" width="46.5" height="46.5" rx="14.5" fill="none" stroke="#d5d7d1" strokeWidth="1.5" strokeDasharray="4 3" />
      )}
      <g className={motionClass} style={boxStyle}>
        <rect
          x="8"
          y="8"
          width="48"
          height="48"
          rx="15"
          fill={ACCENT}
          stroke={pose.ring ? WARNING : "none"}
          strokeWidth={pose.ring ? 3 : 0}
        />
        {pose.eyes === "feliz" ? (
          <g fill="none" stroke={INK} strokeWidth="3.5" strokeLinecap="round">
            <path d="M19 31 Q24 24 29 31" />
            <path d="M35 31 Q40 24 45 31" />
          </g>
        ) : pose.eyes === "concentrado" ? (
          <g>
            <g className="pat-scan" style={boxStyle}>
              <ellipse cx={24 + pupilDx} cy={eyeY} rx="3.7" ry="2.4" fill={INK} />
              <ellipse cx={40 + pupilDx} cy={eyeY} rx="3.7" ry="2.4" fill={INK} />
            </g>
            <g fill="none" stroke={INK} strokeWidth="2.2" strokeLinecap="round">
              <path d="M20 23 L29 24" />
              <path d="M35 24 L44 23" />
            </g>
          </g>
        ) : (
          <g fill={INK} className={pose.motion === "blink" ? "pat-blink" : undefined} style={boxStyle}>
            <circle cx={24 + pupilDx} cy={eyeY} r="3.6" />
            <circle cx={40 + pupilDx} cy={eyeY} r="3.6" />
          </g>
        )}
        {pose.dots && (
          <g fill={INK}>
            {[25, 32, 39].map((cx, i) => (
              <circle key={cx} cx={cx} cy="44" r="2.2" className="pat-dot" style={{ animationDelay: `${i * 160}ms` }} />
            ))}
          </g>
        )}
      </g>
    </svg>
  );
}
