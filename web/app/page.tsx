import type { ReactNode } from "react";
import { Logo } from "@/components/Logo";
import { Button } from "@/components/Button";
import { ImpactStat } from "@/components/ImpactStat";
import { HeroStory } from "@/components/landing/HeroStory";
import { HowItWorks } from "@/components/landing/HowItWorks";
import { AnchorGlide } from "@/components/landing/AnchorGlide";
import { Reveal } from "@/components/landing/Reveal";
import { WhatsAppQR } from "@/components/landing/WhatsAppQR";
import { JOANA_TEXT, WHATSAPP_NUMBER, waLink } from "@/lib/whatsapp";

const wa = WHATSAPP_NUMBER ? waLink(WHATSAPP_NUMBER, JOANA_TEXT) : null;

const Section = ({ id, children }: { id?: string; children: ReactNode }) => (
  <section id={id} className="mx-auto max-w-[1180px] px-4 py-24 sm:px-6 lg:px-10 lg:py-32">
    {children}
  </section>
);

const H2 = ({ children }: { children: ReactNode }) => (
  <Reveal>
    <h2 className="max-w-[820px] text-[34px] font-bold leading-[1.03] tracking-[-0.045em] sm:text-5xl">{children}</h2>
  </Reveal>
);

const PROBLEMS = [
  ["Hora extra cara", "Quem cobre a falta é quem atende o telefone, não quem sai mais barato."],
  ["Turno descoberto no pico", "A falta só aparece quando a fila já está formada."],
  ["Passivo trabalhista", "Uma troca de turno no improviso pode furar descanso e jornada."],
];

const TIMELINE = [
  ["16/10/2026", "EC 141 promulgada"],
  ["~15/12/2026", "Jornada máxima de 42h e 2 folgas por semana"],
  ["~dez/2027", "Jornada máxima de 40h"],
];

export default function Home() {
  return (
    <>
      <AnchorGlide />
      <nav className="sticky top-0 z-20 flex items-center justify-between bg-paper/80 px-4 py-3.5 backdrop-blur-md sm:px-6 lg:px-10">
        <a href="#topo" aria-label="Remane, início" className="rounded-full">
          <Logo animated size={30} />
        </a>
        <div className="flex items-center gap-7 text-[15px]">
          <a href="#como-funciona" className="hidden hover:text-ink-muted md:inline">Como funciona</a>
          <a href="#fim-da-6x1" className="hidden hover:text-ink-muted md:inline">Fim da 6x1</a>
          <a href="#whatsapp" className="hidden hover:text-ink-muted md:inline">WhatsApp</a>
          <Button href="/entrar">Testar a demo</Button>
        </div>
      </nav>

      <main>
        <section id="topo" className="mx-auto max-w-[1100px] px-4 pb-12 pt-16 text-center sm:pt-20">
          <span className="inline-block rounded-full bg-[#e9eae6] px-4 py-1.5 text-[13px] font-medium">
            EC 141 promulgada · 42h a partir de 15 de dezembro
          </span>
          <h1 className="mx-auto mt-6 mb-5 text-[44px] font-bold leading-[0.98] tracking-[-0.055em] sm:text-6xl lg:text-[72px]">
            Sua escala se remaneja sozinha.
          </h1>
          <p className="mx-auto max-w-[640px] text-lg leading-normal text-ink-muted sm:text-xl">
            Um agente que monta a escala dentro da lei e cobre faltas pelo WhatsApp antes de o gestor abrir o celular.
          </p>
          <div className="mt-8 flex flex-wrap justify-center gap-3">
            <Button href="/entrar">Testar a demo</Button>
            {wa && <Button href={wa} variant="secondary">Falar com o agente no WhatsApp</Button>}
          </div>
        </section>

        <HeroStory />

        <Section>
          <H2>Hoje, a escala vive numa planilha e as faltas, no WhatsApp do gerente.</H2>
          <div className="mt-10 grid gap-4 md:grid-cols-3">
            {PROBLEMS.map(([title, text], i) => (
              <Reveal key={title} delay={i * 80} className="rounded-card bg-surface p-7">
                <h3 className="mb-2 text-xl font-semibold tracking-[-0.03em]">{title}</h3>
                <p className="leading-normal text-ink-muted">{text}</p>
              </Reveal>
            ))}
          </div>
        </Section>

        <Section id="fim-da-6x1">
          <H2>A lei mudou. A escala de todo mundo vai ter que mudar.</H2>
          <Reveal>
            <ol className="mt-10 grid gap-4 md:grid-cols-3">
              {TIMELINE.map(([date, text], i) => (
                <li key={date} className="rounded-card border border-line-strong p-6">
                  <span className="tabular text-[13px] font-medium text-ink-subtle">{i + 1} · {date}</span>
                  <p className="mt-2 text-lg font-medium leading-snug tracking-[-0.02em]">{text}</p>
                </li>
              ))}
            </ol>
          </Reveal>
          <div className="mt-4 grid gap-4 md:grid-cols-3">
            <Reveal delay={0}><ImpactStat value="≈ 15 mi" label="de pessoas trabalham hoje em 6x1 (MTE)." /></Reveal>
            <Reveal delay={80}><ImpactStat value="≈ 10%" label="mais cara fica a hora, porque o salário não pode cair." /></Reveal>
            <Reveal delay={160}><ImpactStat value="2 folgas" label="por semana, uma preferencialmente no domingo." /></Reveal>
          </div>
          <p className="mt-5 text-[13px] text-ink-subtle">Datas e números conforme o texto da EC 141; confira o texto oficial.</p>
        </Section>

        <Section id="como-funciona">
          <H2>Como funciona</H2>
          <HowItWorks />
        </Section>

        <Section id="whatsapp">
          <Reveal className="flex flex-col items-start gap-10 rounded-panel bg-surface p-8 sm:p-12 md:flex-row md:items-center md:justify-between">
            <div className="max-w-xl">
              <h2 className="text-[34px] font-bold leading-[1.03] tracking-[-0.045em] sm:text-5xl">
                Teste agora: mande uma mensagem como se fosse a Joana.
              </h2>
              <p className="mt-4 text-lg leading-normal text-ink-muted">
                {wa
                  ? "Aponte a câmera do celular para o código. A mensagem já vai escrita; o agente responde como faria na loja."
                  : "Abra a demo e veja o agente cobrir a falta da Joana do começo ao fim."}
              </p>
              {wa && <Button href={wa} variant="secondary" className="mt-6">Abrir no WhatsApp</Button>}
            </div>
            {wa ? (
              <div className="rounded-card border border-line p-3"><WhatsAppQR href={wa} /></div>
            ) : (
              <Button href="/entrar">Testar a demo</Button>
            )}
          </Reveal>
        </Section>

        <Section>
          <Reveal>
            <p className="text-[13px] font-medium text-ink-subtle">Para quem</p>
            <p className="mt-3 max-w-[900px] text-[28px] font-medium leading-tight tracking-[-0.035em] sm:text-[36px]">
              Redes de varejo, food service e farmácia com 5 a 200 lojas que fazem escala em planilha.
            </p>
          </Reveal>
        </Section>

        <Section>
          <Reveal className="text-center">
            <h2 className="mx-auto max-w-[760px] text-[38px] font-bold leading-[1.02] tracking-[-0.05em] sm:text-[56px]">
              Sua próxima falta já pode chegar resolvida.
            </h2>
            <Button href="/entrar" className="mt-8">Testar a demo</Button>
          </Reveal>
        </Section>
      </main>

      <footer className="mx-auto flex max-w-[1180px] flex-col gap-4 border-t border-line px-4 py-10 text-[13px] text-ink-muted sm:flex-row sm:items-center sm:justify-between sm:px-6 lg:px-10">
        <Logo size={24} />
        <p>Feito no Converge Challenge powered by Tako · Recife, 2026</p>
        <p>Demo com dados sintéticos.</p>
      </footer>
    </>
  );
}
