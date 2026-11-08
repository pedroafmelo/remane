import Link from "next/link";
import type { ReactNode } from "react";
import { Button } from "../Button";
import { Logo } from "../Logo";
import { SyntheticBadge } from "./ui";

type ShellProps = {
  who?: { nome: string; papelLabel: string } | null;
  onLogout?: () => void;
  onReset?: () => void;
  busy?: boolean;
  children: ReactNode;
};

export function Shell({ who, onLogout, onReset, busy, children }: ShellProps) {
  return (
    <div className="flex min-h-svh flex-col">
      <header className="border-b border-line bg-surface">
        <div className="mx-auto flex w-full max-w-5xl flex-wrap items-center gap-x-4 gap-y-2 px-4 py-3 sm:px-6">
          <Link href="/" aria-label="Remane, ir para o início" className="rounded-full">
            <Logo size={28} />
          </Link>
          <SyntheticBadge />
          <span className="flex-1" />
          {onReset && (
            <Button size="sm" variant="secondary" onClick={onReset} disabled={busy}>
              Nova execução
            </Button>
          )}
          {who && (
            <>
              <span className="text-[13px] text-ink-muted">
                {who.nome} · {who.papelLabel}
              </span>
              <Button size="sm" variant="secondary" onClick={onLogout} disabled={busy}>
                Sair
              </Button>
            </>
          )}
        </div>
      </header>
      <main className="mx-auto flex w-full max-w-5xl flex-1 flex-col gap-4 px-4 py-6 sm:px-6 sm:py-8">{children}</main>
      <footer className="px-4 pb-8 pt-2 text-center text-xs text-ink-muted">
        Todos os dados desta demonstração são sintéticos e o tempo é simulado. Nada é publicado fora daqui.
      </footer>
    </div>
  );
}
