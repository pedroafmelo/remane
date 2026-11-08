/**
 * Símbolo do Remane: o rosto do Pat (quadrado accent com óculos redondos e bigode), vetorizado de
 * `docs/design-system/assets/logos/remane-logo-original.png`. Tudo em unidades de um quadrado 64 x 64; o Pat reaproveita
 * estas peças (FACE, Glasses, Mustache) para que mascote e logo sejam o mesmo desenho.
 */
export const FACE = {
  ink: "#17181a",
  accent: "#2bd48a",
  rx: 19,
  /** centro das lentes (x esquerda, x direita, y) e raio do aro */
  lensL: 19.5,
  lensR: 44.5,
  lensY: 29.3,
  lensR0: 9.1,
  pupilY: 29.4,
  pupilR: 3.4,
} as const;

const STROKE = 1.75;

/** Aros, hastes e ponte dos óculos. */
export function Glasses() {
  return (
    <g fill="none" stroke={FACE.ink} strokeWidth={STROKE} strokeLinecap="round">
      <circle cx={FACE.lensL} cy={FACE.lensY} r={FACE.lensR0} />
      <circle cx={FACE.lensR} cy={FACE.lensY} r={FACE.lensR0} />
      <path d="M6.9 27.9 H10.5 M53.5 27.9 H57.1" />
      <path d="M28.6 29.6 C28.9 26.6 35.1 26.6 35.4 29.6" />
    </g>
  );
}

export function Mustache() {
  return (
    <path
      fill={FACE.ink}
      d="M32 40.8 C30 39.2 28.2 39 26.6 39.6 C24.8 40.2 23.4 41.8 22 41.6 C21.1 41.5 20.9 42.3 21.4 43 C22.6 44.8 24.6 45.6 26.8 45.6 C29 45.6 30.6 44.2 32 43.2 C33.4 44.2 35 45.6 37.2 45.6 C39.4 45.6 41.4 44.8 42.6 43 C43.1 42.3 42.9 41.5 42 41.6 C40.6 41.8 39.2 40.2 37.4 39.6 C35.8 39 34 39.2 32 40.8 Z"
    />
  );
}

const boxStyle = { transformBox: "fill-box", transformOrigin: "center" } as const;

type LogoProps = { animated?: boolean; size?: number; word?: boolean };

/** `animated`: o olhar vai para um lado e para o outro, como quem confere a escala, e pisca. Parado com reduced-motion. */
export function LogoMark({ animated = false, size = 32 }: Omit<LogoProps, "word">) {
  return (
    <svg width={size} height={size} viewBox="0 0 64 64" aria-hidden="true" className="shrink-0">
      <rect width="64" height="64" rx={FACE.rx} fill={FACE.accent} />
      <Glasses />
      <g className={animated ? "pat-blink" : undefined} style={boxStyle}>
        <g fill={FACE.ink} className={animated ? "logo-look" : undefined}>
          <circle cx={FACE.lensL} cy={FACE.pupilY} r={FACE.pupilR} />
          <circle cx={FACE.lensR} cy={FACE.pupilY} r={FACE.pupilR} />
        </g>
      </g>
      <Mustache />
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
