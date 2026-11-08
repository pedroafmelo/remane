"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, asFailure } from "@/lib/api";
import type { Failure } from "@/lib/errors";
import { HOME_BY_ROLE, roleLabel } from "@/lib/roles";
import type { Me, Role } from "@/lib/types";
import { Button } from "../Button";
import { Shell } from "./Shell";
import { Notice } from "./ui";

export type Session = {
  booting: boolean;
  me: Me | null;
  problem: Failure | null;
  who: { nome: string; papelLabel: string } | null;
  toLogin: () => void;
  logout: () => Promise<void>;
};

/**
 * Sessão de uma tela da plataforma: lê `/api/me`, manda para `/entrar/` sem sessão e para a casa do papel quando o papel
 * não é o da tela (o backend recusa de qualquer forma; isto só evita mostrar uma tela vazia).
 */
export function useSession(role: Role, onReady?: () => Promise<void> | void): Session {
  const router = useRouter();
  const [booting, setBooting] = useState(true);
  const [me, setMe] = useState<Me | null>(null);
  const [problem, setProblem] = useState<Failure | null>(null);

  const toLogin = useCallback(() => router.replace("/entrar/"), [router]);

  useEffect(() => {
    let cancelled = false;
    api
      .me()
      .then(async (m) => {
        if (cancelled) return;
        if (m.papel !== role) {
          router.replace(HOME_BY_ROLE[m.papel] ?? "/entrar/");
          return;
        }
        setMe(m);
        await onReady?.();
      })
      .catch((err) => {
        if (cancelled) return;
        const failure = asFailure(err);
        if (failure.kind === "auth") toLogin();
        else setProblem(failure);
      })
      .finally(() => {
        if (!cancelled) setBooting(false);
      });
    return () => {
      cancelled = true;
    };
    // onReady roda uma vez, na entrada da tela
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [role, router, toLogin]);

  const logout = useCallback(async () => {
    try {
      await api.logout();
    } finally {
      toLogin();
    }
  }, [toLogin]);

  const who = me ? { nome: me.nome, papelLabel: roleLabel(me.papel) } : null;
  return { booting, me, problem, who, toLogin, logout };
}

/** O que a tela mostra enquanto a sessão não está pronta: carregando, ou o erro com o caminho de volta. */
export function SessionGate({ session }: { session: Session }) {
  if (session.booting) {
    return (
      <Shell>
        <p role="status" className="text-ink-muted">
          Carregando…
        </p>
      </Shell>
    );
  }
  return (
    <Shell>
      {session.problem ? <Notice>{session.problem.message}</Notice> : <p className="text-ink-muted">Redirecionando…</p>}
      <div>
        <Button href="/entrar/" variant="secondary">
          Ir para a entrada
        </Button>
      </div>
    </Shell>
  );
}
