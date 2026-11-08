"use client";

import { useId } from "react";
import { Button } from "../Button";
import { Card, Muted } from "./ui";

/** Envio: um CSV do disco ou um dos arquivos de exemplo (sintéticos) da rota de demo. */
export function UploadPanel({ title = "Enviar a escala atual", busy, onFile, onDemo }: { title?: string; busy: boolean; onFile: (file: File) => void; onDemo: (name: string) => void }) {
  const inputId = useId();
  return (
    <Card title={title}>
      <p className="mb-4 text-[15px] leading-relaxed text-ink-muted">
        Envie a escala da semana em CSV (UTF-8, até 1 MB) ou use um arquivo de exemplo. Os exemplos são dados sintéticos gerados pelo
        time.
      </p>
      <div className="flex flex-wrap items-center gap-3">
        <Button disabled={busy} aria-busy={busy} onClick={() => onDemo("escala_atual.csv")}>
          Usar escala de exemplo
        </Button>
        <Button variant="secondary" disabled={busy} onClick={() => onDemo("escala_defeito.csv")}>
          Exemplo com defeitos (mostra o RX-13)
        </Button>
        <span className="text-[13px] text-ink-muted">ou</span>
        <input
          id={inputId}
          type="file"
          accept=".csv,text/csv"
          disabled={busy}
          className="peer sr-only"
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (f) onFile(f);
            e.target.value = "";
          }}
        />
        <label
          htmlFor={inputId}
          className="inline-flex h-11 cursor-pointer items-center rounded-full border border-line-strong bg-surface px-5.5 text-[15px] font-medium transition-colors hover:border-ink-subtle peer-focus-visible:outline-2 peer-focus-visible:outline-offset-3 peer-focus-visible:outline-ink peer-disabled:cursor-not-allowed peer-disabled:opacity-50"
        >
          Escolher um arquivo CSV
        </label>
      </div>
      {busy && (
        <div className="mt-3">
          <Muted>Enviando e lendo o arquivo…</Muted>
        </div>
      )}
    </Card>
  );
}
