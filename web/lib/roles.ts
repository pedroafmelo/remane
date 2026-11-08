import type { Role } from "./types.ts";

/** Papéis da demo (DEC-044): o gestor reúne quem opera a loja e quem cuida das regras; o colaborador trabalha na escala. */
export const ROLE_LABELS: Record<Role, string> = {
  gestor: "Gestor",
  colaborador: "Colaborador",
};

export const ROLE_SHORT: Record<Role, string> = { gestor: "gestor", colaborador: "colaborador" };

export const DEMO_ROLES: { role: Role; blurb: string }[] = [
  { role: "gestor", blurb: "Envia a escala, confere o antes e o depois e aprova a publicação." },
  { role: "colaborador", blurb: "Entra como quem trabalha na escala. Nesta versão, o acesso ainda é só de leitura da conta." },
];

export function roleLabel(role: string): string {
  return ROLE_LABELS[role as Role] ?? role;
}

/** Dica de interface: só o gestor opera a escala. Quem decide é sempre o backend (401/403). */
export function canOperateSchedule(role: Role): boolean {
  return role === "gestor";
}
