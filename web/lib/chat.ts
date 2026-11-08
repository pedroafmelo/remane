// Chat do celular simulado e do assistente do gestor (C7b): limite, contador e sugestões. As sugestões só preenchem o
// campo; quem decide o que a frase quer dizer é o servidor, e toda resposta vem de modelos de texto do servidor.

export const CHAT_MAX_CHARS = 300;

export function chatInputError(text: string): string | null {
  if (!text.trim()) return "Escreva uma mensagem.";
  if (text.length > CHAT_MAX_CHARS) return `Até ${CHAT_MAX_CHARS} caracteres.`;
  return null;
}

export function chatCounter(text: string): string {
  return `${text.length}/${CHAT_MAX_CHARS}`;
}

const SUGGEST_DEFAULT = ["Amanhã não vou conseguir ir", "Vou me atrasar 40 min", "Qual é a minha escala?"];
const SUGGEST_OFFER = ["Pode ser, aceito", "Não posso"];
const SUGGEST_QUESTION = ["Estou a caminho", "Hoje não vou"];

/** Mesmas sugestões que o servidor devolve em cada resposta, para a tela já abrir com elas. */
export function chatSuggestions(open: { openQuestions: number; openOffers: number }): string[] {
  if (open.openQuestions > 0) return [...SUGGEST_QUESTION];
  if (open.openOffers > 0) return [...SUGGEST_OFFER];
  return [...SUGGEST_DEFAULT];
}

export const ASSISTANT_SUGGESTIONS = [
  "Quais exceções estão abertas?",
  "Quem faz hora extra esta semana?",
  "Como está a escala de quinta?",
  "O que diz a regra da jornada semanal?",
  "O que aconteceu no último caso?",
];
