import type { Role } from "./types.ts";

export const ROLE_LABELS: Record<Role, string> = {
  gerente: "Gerente",
  dp: "DP (departamento pessoal)",
  colaborador: "Colaborador",
};

export const DEMO_ROLES: { role: Role; blurb: string }[] = [
  { role: "gerente", blurb: "Envia a escala, confere o antes e o depois e aprova a publicação." },
  { role: "dp", blurb: "Entra como o departamento pessoal. Nesta versão, o acesso ainda é só de leitura da conta." },
  { role: "colaborador", blurb: "Entra como quem trabalha na escala. Nesta versão, o acesso ainda é só de leitura da conta." },
];

export function roleLabel(role: string): string {
  return ROLE_LABELS[role as Role] ?? role;
}

/** Dica de interface: na fatia só o gerente opera a escala. Quem decide é sempre o backend (401/403). */
export function canOperateSchedule(role: Role): boolean {
  return role === "gerente";
}
