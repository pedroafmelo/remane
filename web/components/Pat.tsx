import { patLabel, patPose, type PatEstado } from "@/lib/pat";
import { FACE, Glasses, Mustache } from "./Logo";

const INK = FACE.ink;
const WARNING = "#e8890c";

type PatProps = { estado?: PatEstado; size?: number; label?: string; decorativo?: boolean };

/**
 * Pat, o agente do Remane: o mesmo rosto do logo (quadrado accent, óculos redondos e bigode), com o olhar mudando por estado.
 * O rosto é desenhado em 64 x 64 e reduzido a 48 x 48 no centro, deixando margem para o contorno tracejado e o deslize.
 * Accent marca o que o agente fez; warning só aparece quando precisa de uma pessoa. Sem movimento com reduced-motion.
 */
export function Pat({ estado = "parado", size = 64, label, decorativo = false }: PatProps) {
  const pose = patPose(estado);
  const eyeY = pose.eyes === "baixo" ? 31.8 : pose.eyes === "cima" ? 27 : FACE.pupilY;
  const pupilDx = pose.eyes === "cima" ? 1.2 : pose.eyes === "concentrado" ? 2.5 : 0;
  const boxStyle = { transformBox: "fill-box", transformOrigin: "center" } as const;
  const motionClass = pose.motion === "slide" ? "animate-slide" : pose.motion === "pop" ? "animate-pop" : undefined;
  const lx = FACE.lensL + pupilDx;
  const rx = FACE.lensR + pupilDx;

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
        <rect x="8.75" y="8.75" width="46.5" height="46.5" rx="13.5" fill="none" stroke="#d5d7d1" strokeWidth="1.5" strokeDasharray="4 3" />
      )}
      <g className={motionClass} style={boxStyle}>
        <g transform="translate(8 8) scale(0.75)">
          <rect
            width="64"
            height="64"
            rx={FACE.rx}
            fill={FACE.accent}
            stroke={pose.ring ? WARNING : "none"}
            strokeWidth={pose.ring ? 4 : 0}
          />
          <Glasses />
          {pose.eyes === "feliz" ? (
            <g fill="none" stroke={INK} strokeWidth="2.6" strokeLinecap="round">
              <path d="M15 31 Q19.5 24.5 24 31" />
              <path d="M40 31 Q44.5 24.5 49 31" />
            </g>
          ) : pose.eyes === "concentrado" ? (
            <g>
              <g className="pat-scan" style={boxStyle}>
                <ellipse cx={lx} cy={eyeY} rx="3.6" ry="2.2" fill={INK} />
                <ellipse cx={rx} cy={eyeY} rx="3.6" ry="2.2" fill={INK} />
              </g>
              <g fill="none" stroke={INK} strokeWidth="2.4" strokeLinecap="round">
                <path d="M13.5 15.2 L25 16.8" />
                <path d="M39 16.8 L50.5 15.2" />
              </g>
            </g>
          ) : (
            <g fill={INK} className={pose.motion === "blink" ? "pat-blink" : undefined} style={boxStyle}>
              <circle cx={lx} cy={eyeY} r={FACE.pupilR} />
              <circle cx={rx} cy={eyeY} r={FACE.pupilR} />
            </g>
          )}
          <Mustache />
          {pose.dots && (
            <g fill={INK}>
              {[24, 32, 40].map((cx, i) => (
                <circle key={cx} cx={cx} cy="53.5" r="2.6" className="pat-dot" style={{ animationDelay: `${i * 160}ms` }} />
              ))}
            </g>
          )}
        </g>
      </g>
    </svg>
  );
}
