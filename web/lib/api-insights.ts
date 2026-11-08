// Cliente das rotas do painel do gestor (regras, simulação de vigência, impacto).

import { post, request } from "./api.ts";
import type { Impact, RulesView, VigenciaSimulation } from "./types-insights.ts";

export const insightsApi = {
  rules: () => request<RulesView>("/api/rules"),
  simulateVigencia: () => post<VigenciaSimulation>("/api/simulate/vigencia"),
  impact: () => request<Impact>("/api/impact"),
};
