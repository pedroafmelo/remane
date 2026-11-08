"use client";

import { useId, useState } from "react";
import type { ReportInput } from "@/lib/types-tracker";
import { Button } from "../Button";

export const TEXT_MAX = 300;

type Props = {
  kind: ReportInput["kind"];
  days: { day: string; label: string }[];
  busy: boolean;
  onSubmit: (day: string, text: string, file: File | null) => void;
  onCancel: () => void;
};

/** Aviso ao Pat no celular simulado: o turno, um texto opcional e um PDF opcional (só dados fictícios). */
export function ReportForm({ kind, days, busy, onSubmit, onCancel }: Props) {
  const id = useId();
  const [day, setDay] = useState(days[0]?.day ?? "");
  const [text, setText] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);

  function pick(f: File | null) {
    if (f && f.type !== "application/pdf" && !f.name.toLowerCase().endsWith(".pdf")) {
      setError("O anexo precisa ser um PDF.");
      setFile(null);
      return;
    }
    setError(null);
    setFile(f);
  }

  const fieldCls = "rounded-bubble border border-line-strong bg-surface px-3 py-2 text-[14px] focus-visible:outline-2";
  return (
    <form
      className="flex w-full flex-col gap-2.5"
      onSubmit={(e) => {
        e.preventDefault();
        if (day) onSubmit(day, text, file);
      }}
    >
      <p className="text-sm font-medium">{kind === "falta" ? "Vou faltar" : "Vou me atrasar"}</p>
      <label htmlFor={`${id}-day`} className="text-xs text-ink-muted">
        Qual turno?
      </label>
      <select id={`${id}-day`} value={day} onChange={(e) => setDay(e.target.value)} disabled={busy} className={fieldCls}>
        {days.map((d) => (
          <option key={d.day} value={d.day}>
            {d.label}
          </option>
        ))}
      </select>
      <label htmlFor={`${id}-text`} className="text-xs text-ink-muted">
        Quer contar algo ao Pat? (opcional)
      </label>
      <textarea
        id={`${id}-text`}
        rows={2}
        maxLength={TEXT_MAX}
        value={text}
        onChange={(e) => setText(e.target.value)}
        disabled={busy}
        className={fieldCls}
      />
      <label htmlFor={`${id}-file`} className="text-xs text-ink-muted">
        Anexar atestado em PDF (opcional)
      </label>
      <input
        id={`${id}-file`}
        type="file"
        accept="application/pdf"
        disabled={busy}
        onChange={(e) => pick(e.target.files?.[0] ?? null)}
        className="text-xs file:mr-2 file:rounded-full file:border file:border-line-strong file:bg-surface file:px-3 file:py-1.5 file:text-xs"
      />
      <p className="text-xs font-medium text-warning-ink">Use só dados fictícios: nada de documento ou nome reais.</p>
      {error && (
        <p role="alert" className="text-xs font-medium text-danger">
          {error}
        </p>
      )}
      <div className="flex flex-wrap justify-end gap-2">
        <Button size="sm" variant="secondary" onClick={onCancel} disabled={busy}>
          Voltar
        </Button>
        <Button size="sm" type="submit" disabled={busy || !day || days.length === 0} aria-busy={busy}>
          {busy ? "Enviando…" : "Enviar ao Pat"}
        </Button>
      </div>
    </form>
  );
}
