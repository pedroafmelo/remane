import { useRef } from 'react'
import { Section } from './Common'

/** Envio: um CSV do disco ou um dos arquivos de exemplo (sintéticos) da rota de demo. */
export function UploadView({
  busy,
  onFile,
  onDemo,
}: {
  busy: boolean
  onFile: (file: File) => void
  onDemo: (name: string) => void
}) {
  const input = useRef<HTMLInputElement>(null)
  return (
    <Section title="Enviar a escala atual">
      <p>
        Envie a escala da semana em CSV (UTF-8, até 1 MB) ou use um arquivo de exemplo. Os exemplos são dados
        sintéticos gerados pelo time.
      </p>
      <div className="actions">
        <input
          ref={input}
          type="file"
          accept=".csv,text/csv"
          disabled={busy}
          onChange={(e) => {
            const f = e.target.files?.[0]
            if (f) onFile(f)
            e.target.value = ''
          }}
        />
      </div>
      <div className="actions">
        <button className="btn btn-primary" disabled={busy} onClick={() => onDemo('escala_atual.csv')}>
          Usar escala de exemplo
        </button>
        <button className="btn" disabled={busy} onClick={() => onDemo('escala_defeito.csv')}>
          Usar exemplo com defeitos (mostra o RX-13)
        </button>
      </div>
      {busy && <p className="muted">Enviando e lendo o arquivo…</p>}
    </Section>
  )
}
