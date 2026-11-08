"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api, asFailure } from "@/lib/api";
import { loginMessage } from "@/lib/errors";
import { DEMO_ROLES, ROLE_LABELS, ROLE_SHORT } from "@/lib/roles";
import type { Role } from "@/lib/types";
import { Button } from "../Button";
import { Logo } from "../Logo";
import { Notice, SyntheticBadge } from "./ui";

/** Entrada da demonstração: um botão por papel que o backend aceita em `POST /auth/demo/{papel}`. */
export function EntrarPanel() {
  const router = useRouter();
  const [busy, setBusy] = useState<Role | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function enter(role: Role) {
    setBusy(role);
    setError(null);
    try {
      await api.loginDemo(role);
      router.push("/plataforma/");
    } catch (err) {
      setError(loginMessage(asFailure(err)));
      setBusy(null);
    }
  }

  return (
    <main className="mx-auto flex min-h-svh w-full max-w-2xl flex-col justify-center gap-6 px-4 py-10 sm:px-6">
      <Link href="/" aria-label="Remane, voltar ao início" className="self-start rounded-full">
        <Logo animated size={36} />
      </Link>

      <div className="flex flex-col gap-3">
        <SyntheticBadge />
        <h1 className="text-[32px] font-semibold leading-[1.1] tracking-[-0.035em]">Entre na demonstração do Remane</h1>
        <p className="text-lg leading-normal text-ink-muted">
          O Pat, o agente do Remane, lê a escala da semana, confere as regras, mostra o antes e o depois com custo medido e só publica
          depois que o gestor aprova.
        </p>
        <p className="text-[15px] leading-relaxed text-ink-muted">
          Tudo aqui usa dados sintéticos, gerados pelo time, e regras fictícias onde a convenção e a política da empresa seriam aplicadas.
          Não há senha: escolha um papel para entrar.
        </p>
      </div>

      <div aria-live="polite">{error && <Notice>{error}</Notice>}</div>

      <ul className="flex flex-col gap-3">
        {DEMO_ROLES.map(({ role, blurb }) => (
          <li key={role} className="flex flex-col gap-3 rounded-card bg-surface p-5 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h2 className="text-lg font-bold tracking-[-0.02em]">{ROLE_LABELS[role]}</h2>
              <p className="text-sm text-ink-muted">{blurb}</p>
            </div>
            <Button
              variant={role === "gestor" ? "primary" : "secondary"}
              className="shrink-0"
              disabled={busy !== null}
              aria-busy={busy === role}
              onClick={() => enter(role)}
            >
              {busy === role ? "Entrando…" : `Entrar como ${ROLE_SHORT[role]}`}
            </Button>
          </li>
        ))}
      </ul>

      <div>
        <Button href="/" variant="secondary" size="sm">
          Voltar para o início
        </Button>
      </div>
    </main>
  );
}
