// Cliente das rotas do painel do gestor (regras, simulação de vigência, impacto, evals).

import { post, request } from "./api.ts";
import type { EvalsResponse, Impact, RulesView, VigenciaSimulation } from "./types-insights.ts";

export const insightsApi = {
  rules: () => request<RulesView>("/api/rules"),
  simulateVigencia: () => post<VigenciaSimulation>("/api/simulate/vigencia"),
  impact: () => request<Impact>("/api/impact"),
  evals: () => request<EvalsResponse>("/api/evals"),
};
