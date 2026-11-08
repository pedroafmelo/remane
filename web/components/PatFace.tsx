/**
 * Rosto do Pat, o agente do Remane (quadrado accent com óculos redondos e bigode), vetorizado de
 * `docs/design-system/assets/logos/pat-rosto-original.png`. Tudo em unidades de um quadrado 64 x 64. Não é a logo da
 * Remane (a grade com o bloco verde, em `Logo.tsx`): é só o mascote.
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
