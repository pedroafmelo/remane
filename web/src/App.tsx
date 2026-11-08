import { useCallback, useEffect, useState } from 'react'
import { ApiError, api } from './api'
import { CompareView } from './components/Compare'
import { ExceptionCardView, SyntheticBadge } from './components/Common'
import { GridView } from './components/Grid'
import { JustificationView } from './components/Justification'
import { SummaryView } from './components/Summary'
import { TraceView } from './components/Trace'
import { UploadView } from './components/Upload'
import { PHASE_LABELS, timeBr } from './format'
import type { ExceptionCard, Me, ProposedSchedule, PublishedSchedule, RunState, TraceEvent } from './types'

interface Problem {
  message: string
  card: ExceptionCard | null
}

function toProblem(err: unknown): Problem {
  if (err instanceof ApiError) return { message: err.message, card: err.exception }
  return { message: 'Não foi possível falar com o servidor. Tente de novo.', card: null }
}

export default function App() {
  const [booting, setBooting] = useState(true)
  const [me, setMe] = useState<Me | null>(null)
  const [busy, setBusy] = useState<string | null>(null) // o que está em andamento
  const [problem, setProblem] = useState<Problem | null>(null)
  const [run, setRun] = useState<RunState | null>(null)
  const [proposed, setProposed] = useState<ProposedSchedule | null>(null)
  const [published, setPublished] = useState<PublishedSchedule | null>(null)
  const [trace, setTrace] = useState<TraceEvent[]>([])

  const refreshTrace = useCallback(async (runId: string) => {
    try {
      setTrace(await api.trace(runId))
    } catch {
      // o rastro é informativo: falhar aqui não derruba o fluxo
    }
  }, [])

  const refreshPublished = useCallback(async () => {
    try {
      setPublished(await api.published())
    } catch {
      setPublished(null)
    }
  }, [])

  useEffect(() => {
    api
      .me()
      .then((m) => {
        setMe(m)
        return refreshPublished()
      })
      .catch(() => setMe(null))
      .finally(() => setBooting(false))
  }, [refreshPublished])

  /** Executa uma ação da tela: marca ocupado, limpa o problema e traduz os erros (401 volta à landing). */
  async function act(label: string, fn: () => Promise<void>, runId?: string) {
    setBusy(label)
    setProblem(null)
    try {
      await fn()
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        setMe(null)
        setRun(null)
        return
      }
      setProblem(toProblem(err))
    } finally {
      if (runId) await refreshTrace(runId)
      setBusy(null)
    }
  }

  async function login() {
    await act('login', async () => {
      setMe(await api.loginGerente())
      await refreshPublished()
    })
  }

  async function logout() {
    await act('logout', async () => {
      await api.logout()
      setMe(null)
      reset()
    })
  }

  function reset() {
    setRun(null)
    setProposed(null)
    setTrace([])
    setProblem(null)
  }

  /** Envia o CSV (do disco ou de exemplo). Recusas de arquivo (413, 422) voltam com o cartão RX-13 no corpo. */
  const send = (load: () => Promise<{ name: string; blob: Blob }>) =>
    act('upload', async () => {
      setRun(null)
      setProposed(null)
      setTrace([])
      const { name, blob } = await load()
      const state = await api.startRun(name, blob)
      setRun(state)
      await refreshTrace(state.run_id)
    })

  const confirm = (r: RunState) =>
    act(
      'confirm',
      async () => {
        const state = await api.confirm(r.run_id)
        setRun(state)
        if (state.phase === 'awaiting_approval') setProposed(await api.schedule(r.run_id))
      },
      r.run_id,
    )

  const approve = (r: RunState) =>
    act(
      'approve',
      async () => {
        const state = await api.approve(r.run_id)
        setRun(state)
        await refreshPublished()
      },
      r.run_id,
    )

  if (booting) {
    return (
      <Shell me={null}>
        <p className="muted">Carregando…</p>
      </Shell>
    )
  }

  if (!me) {
    return (
      <Shell me={null}>
        <Landing busy={busy === 'login'} problem={problem} onLogin={login} />
      </Shell>
    )
  }

  const working = busy !== null
  const showCard = run?.exception ?? null
  // Com exceção na execução (por exemplo RX-12), não há texto de justificativa, mesmo que o corpo traga um.
  const justification = run && !run.exception ? run.justification : null

  return (
    <Shell me={me} onLogout={logout} onReset={run || problem ? reset : undefined}>
      {problem && <ProblemView problem={problem} />}

      {!run && (
        <>
          <UploadView
            busy={busy === 'upload'}
            onFile={(f) => send(async () => ({ name: f.name, blob: f }))}
            onDemo={(name) => send(async () => ({ name, blob: await api.demoFile(name) }))}
          />
          {published?.version && <PublishedView published={published} title="Última grade publicada" />}
        </>
      )}

      {run && (
        <>
          <p className="status-line">
            Execução <code>{run.run_id}</code> · {PHASE_LABELS[run.phase] ?? run.phase}
          </p>

          {run.summary && (
            <SummaryView
              summary={run.summary}
              canConfirm={run.phase === 'awaiting_confirm'}
              busy={busy === 'confirm'}
              onConfirm={() => confirm(run)}
            />
          )}

          {showCard && <ExceptionCardView card={showCard} />}

          {run.comparison && <CompareView comparison={run.comparison} />}
          {justification && <JustificationView justification={justification} />}

          {run.phase === 'awaiting_approval' && proposed && (
            <>
              <GridView
                title="Grade semanal proposta"
                schedule={proposed.schedule}
                employees={proposed.employees}
                note="Proposta do agente. Só vale depois da aprovação do gerente."
              />
              <div className="actions approve">
                <button className="btn btn-primary btn-lg" onClick={() => approve(run)} disabled={working}>
                  {busy === 'approve' ? 'Publicando…' : 'Aprovar e publicar'}
                </button>
                <span className="muted">Ato do gerente: fica gravado com quem aprovou e quando.</span>
              </div>
            </>
          )}

          {run.phase === 'published' && published?.version && (
            <PublishedView published={published} title="Grade publicada" />
          )}

          <TraceView events={trace} />
        </>
      )}
    </Shell>
  )
}

function Shell({
  me,
  onLogout,
  onReset,
  children,
}: {
  me: Me | null
  onLogout?: () => void
  onReset?: () => void
  children: React.ReactNode
}) {
  return (
    <>
      <header className="topbar">
        <div className="topbar-inner">
          <strong className="brand">Escalista</strong>
          <SyntheticBadge />
          <span className="spacer" />
          {onReset && (
            <button className="btn btn-small" onClick={onReset}>
              Nova execução
            </button>
          )}
          {me && (
            <>
              <span className="muted who">
                {me.nome} · {me.papel}
              </span>
              <button className="btn btn-small" onClick={onLogout}>
                Sair
              </button>
            </>
          )}
        </div>
      </header>
      <main className="page">{children}</main>
      <footer className="footer">
        Todos os dados desta demonstração são sintéticos e o tempo é simulado. Nada é publicado fora daqui.
      </footer>
    </>
  )
}

function Landing({ busy, problem, onLogin }: { busy: boolean; problem: Problem | null; onLogin: () => void }) {
  return (
    <section className="hero">
      <h1>Escala de lojas sob a EC 141, com o gerente no comando</h1>
      <p>
        O Escalista lê a escala da semana, refaz a grade dentro das regras (jornada de 42h e repousos), mostra o antes
        e o depois com custo medido e só publica depois que o gerente aprova.
      </p>
      <p>
        <SyntheticBadge /> A demonstração usa apenas dados sintéticos e regras fictícias (demo) onde a convenção e a
        política da empresa seriam aplicadas.
      </p>
      {problem && <ProblemView problem={problem} />}
      <button className="btn btn-primary btn-lg" onClick={onLogin} disabled={busy}>
        {busy ? 'Entrando…' : 'Entrar como gerente (demo)'}
      </button>
    </section>
  )
}

function ProblemView({ problem }: { problem: Problem }) {
  return (
    <>
      <div className="notice" role="alert">
        {problem.message}
      </div>
      {problem.card && <ExceptionCardView card={problem.card} />}
    </>
  )
}

function PublishedView({ published, title }: { published: PublishedSchedule; title: string }) {
  const v = published.version
  if (!v) return null
  return (
    <GridView
      title={title}
      schedule={v.schedule}
      employees={published.employees}
      note={`Versão ${v.id} · ${v.violations_total} violações · criada em ${timeBr(v.created_at)}`}
    />
  )
}

