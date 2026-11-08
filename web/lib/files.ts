// Tipos de arquivo que o envio aceita (o servidor decide pelos bytes iniciais e pela extensão; o tipo do cabeçalho é só honestidade).

export const UPLOAD_ACCEPT = ".csv,.xlsx,.pdf,text/csv,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,application/pdf";

const TYPES: Record<string, string> = {
  csv: "text/csv",
  txt: "text/plain",
  xlsx: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  pdf: "application/pdf",
};

/** `Content-Type` do corpo bruto pelo nome do arquivo; extensão desconhecida vai como binário genérico. */
export function contentTypeFor(fileName: string): string {
  const dot = fileName.lastIndexOf(".");
  const ext = dot < 0 ? "" : fileName.slice(dot + 1).toLowerCase();
  return TYPES[ext] ?? "application/octet-stream";
}
