// Onde começar a rolagem suave para não atravessar a página inteira:
// longe demais → salta para `span` antes do destino; perto → desliza de onde está.
export function glideStart(current: number, target: number, span: number): number {
  const distance = target - current;
  if (Math.abs(distance) <= span) return current;
  return target - Math.sign(distance) * span;
}
