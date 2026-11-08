import Link from "next/link";
import type { ReactNode } from "react";
import { Button } from "../Button";
import { Logo } from "../Logo";
import { SyntheticBadge } from "./ui";

/** As quatro áreas do gestor (design system: Regras, Escala, Exceções, Impacto), na ordem do trabalho. */
export const AREAS = [
  { key: "escala", label: "Escala", href: "/plataforma/" },
  { key: "excecoes", label: "Exceções", href: "/plataforma/excecoes/" },
  { key: "impacto", label: "Impacto", href: "/plataforma/impacto/" },
  { key: "regras", label: "Regras", href: "/plataforma/regras/" },
] as const;

export type Area = (typeof AREAS)[number]["key"];

type ShellProps = {
  who?: { nome: string; papelLabel: string } | null;
  /** área ativa do gestor; sem ela, não há menu (entrada, colaborador) */
  area?: Area;
  /** contador ao lado de uma área (por exemplo, exceções abertas) */
  badges?: Partial<Record<Area, number>>;
  onLogout?: () => void;
  onReset?: () => void;
  busy?: boolean;
  children: ReactNode;
};

export function Shell({ who, area, badges, onLogout, onReset, busy, children }: ShellProps) {
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
        {area && (
          <nav aria-label="Áreas da plataforma" className="mx-auto w-full max-w-5xl px-4 sm:px-6">
            <ul className="-mb-px flex gap-1 overflow-x-auto">
              {AREAS.map((a) => {
                const active = a.key === area;
                const count = badges?.[a.key];
                return (
                  <li key={a.key}>
                    <Link
                      href={a.href}
                      aria-current={active ? "page" : undefined}
                      className={`inline-flex items-center gap-2 whitespace-nowrap border-b-2 px-3 py-2.5 text-[15px] font-medium transition-colors ${
                        active ? "border-ink text-ink" : "border-transparent text-ink-muted hover:text-ink"
                      }`}
                    >
                      {a.label}
                      {count ? (
                        <span className="tabular rounded-full bg-warning-soft px-1.5 text-[12px] font-semibold text-warning-ink" aria-label={`${count} abertas`}>
                          {count}
                        </span>
                      ) : null}
                    </Link>
                  </li>
                );
              })}
            </ul>
          </nav>
        )}
      </header>
      <main className="mx-auto flex w-full max-w-5xl flex-1 flex-col gap-4 px-4 py-6 sm:px-6 sm:py-8">{children}</main>
      <footer className="px-4 pb-8 pt-2 text-center text-xs text-ink-muted">
        Todos os dados desta demonstração são sintéticos e o tempo é simulado. Nada é publicado fora daqui.
      </footer>
    </div>
  );
}
