import { Logo } from "@/components/Logo";
import { Button } from "@/components/Button";

export const metadata = { title: "Remane · entrar" };

// Placeholder: login e botões de demo por papel entram aqui (C4, frente C; arquitetura.md, seção 11).
export default function EntrarPage() {
  return (
    <main className="grid min-h-svh place-items-center px-4 text-center">
      <div>
        <Logo animated size={40} />
        <p className="mt-6 text-lg text-ink-muted">O acesso à demo abre aqui em breve.</p>
        <Button href="/" variant="secondary" className="mt-6">Voltar para o início</Button>
      </div>
    </main>
  );
}
