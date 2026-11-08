import type { ReactNode } from "react";
import { Logo } from "@/components/Logo";
import { Button } from "@/components/Button";
import { HeroStory } from "@/components/landing/HeroStory";
import { HowItWorks } from "@/components/landing/HowItWorks";
import { AnchorGlide } from "@/components/landing/AnchorGlide";
import { Reveal } from "@/components/landing/Reveal";
import { ChatBubble } from "@/components/ChatBubble";

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
  ["Hora extra que ninguém planejou", "Quem cobre a falta é quem atende o telefone, não quem sai mais barato."],
  ["Turno descoberto no horário de pico", "A falta só aparece quando a fila já está formada."],
  ["Regra trabalhista furada sem ninguém ver", "Uma troca no improviso pode furar descanso, jornada ou folga."],
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
          <a href="#teste" className="hidden hover:text-ink-muted md:inline">Teste agora</a>
          <Button href="/entrar">Testar a demo</Button>
        </div>
      </nav>

      <main>
        <section id="topo" className="mx-auto max-w-[1100px] px-4 pb-12 pt-16 text-center sm:pt-20">
          <span className="inline-block rounded-full bg-[#e9eae6] px-4 py-1.5 text-[13px] font-medium">
            Lei, convenção e política da empresa em cada turno
          </span>
          <h1 className="mx-auto mt-6 mb-5 text-[44px] font-bold leading-[0.98] tracking-[-0.055em] sm:text-6xl lg:text-[72px]">
            O engenheiro da sua escala de trabalho.
          </h1>
          <p className="mx-auto max-w-[640px] text-lg leading-normal text-ink-muted sm:text-xl">
            Do planejamento da semana à falta de última hora: o Remane monta, confere e ajusta a escala, e só chama você para decidir.
          </p>
          <div className="mt-8 flex flex-wrap justify-center gap-3">
            <Button href="/entrar">Testar a demo</Button>
          </div>
        </section>

        <HeroStory />

        <Section>
          <H2>Toda semana, alguém monta a escala na mão, e toda semana ela quebra.</H2>
          <div className="mt-10 grid gap-4 md:grid-cols-3">
            {PROBLEMS.map(([title, text], i) => (
              <Reveal key={title} delay={i * 80} className="rounded-card bg-surface p-7">
                <h3 className="mb-2 text-xl font-semibold tracking-[-0.03em]">{title}</h3>
                <p className="leading-normal text-ink-muted">{text}</p>
              </Reveal>
            ))}
          </div>
        </Section>

        <Section id="como-funciona">
          <H2>Como funciona</H2>
          <HowItWorks />
        </Section>

        <Section id="teste">
          <Reveal className="flex flex-col items-start gap-10 rounded-panel bg-surface p-8 sm:p-12 md:flex-row md:items-center md:justify-between">
            <div className="max-w-xl">
              <h2 className="text-[34px] font-bold leading-[1.03] tracking-[-0.045em] sm:text-5xl">
                Teste agora: avise uma falta e veja o Remane encontrar quem cobre.
              </h2>
              <p className="mt-4 text-lg leading-normal text-ink-muted">
                Na demo, um celular simulado faz o papel do WhatsApp: escolha alguém da equipe, mande a mensagem e acompanhe a escala
                mudando do lado do gestor.
              </p>
              <Button href="/entrar" className="mt-6">Testar a demo</Button>
            </div>
            <div className="w-full max-w-[320px] overflow-hidden rounded-card border border-line bg-surface-chat" aria-hidden="true">
              <div className="border-b border-line bg-surface px-4 py-3 text-[13px] font-medium">
                Celular simulado <span className="text-ink-muted">· Pedro, Loja Boa Viagem</span>
              </div>
              <div className="flex flex-col gap-2.5 p-4">
                <ChatBubble from="person">Bom dia, não vou conseguir ir hoje.</ChatBubble>
                <ChatBubble from="agent">Recebi, Pedro. Já estou procurando quem cubra seu turno das 14h.</ChatBubble>
              </div>
            </div>
          </Reveal>
        </Section>

        <Section>
          <Reveal className="text-center">
            <h2 className="mx-auto max-w-[760px] text-[38px] font-bold leading-[1.02] tracking-[-0.05em] sm:text-[56px]">
              Deixe a escala com quem entende de escala.
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
