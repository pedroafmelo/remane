import type { Role } from "./types.ts";

// DEC-044: na demo, o gestor reúne gerente e DP; o colaborador é quem trabalha na escala.
export const ROLE_LABELS: Record<Role, string> = {
  gestor: "Gestor",
  colaborador: "Colaborador",
};

export const ROLE_SHORT: Record<Role, string> = { gestor: "gestor", colaborador: "colaborador" };

export const DEMO_ROLES: { role: Role; blurb: string }[] = [
  { role: "gestor", blurb: "Envia a escala, confere o antes e o depois, decide as exceções e aprova a publicação." },
  { role: "colaborador", blurb: "Vê a própria escala no celular simulado e avisa uma falta ao Pat." },
];

/** Para onde cada papel vai depois de entrar. */
export const HOME_BY_ROLE: Record<Role, string> = { gestor: "/plataforma/", colaborador: "/colaborador/" };

export function roleLabel(role: string): string {
  return ROLE_LABELS[role as Role] ?? role;
}

/** Dica de interface: só o gestor opera a escala. Quem decide é sempre o backend (401/403). */
export function canOperateSchedule(role: Role): boolean {
  return role === "gestor";
}
