"use client";

import { useEffect, useState } from "react";
import { Pat } from "../Pat";

/**
 * O Pat trabalhando enquanto a execução roda no servidor. Mostra o que ele faz, na ordem, e o tempo decorrido medido no
 * navegador; não há barra de progresso porque o servidor não informa a etapa (seria inventar).
 */
export function PatWorking({ title, steps }: { title: string; steps: string[] }) {
  const [seconds, setSeconds] = useState(0);
  useEffect(() => {
    const started = Date.now();
    const id = setInterval(() => setSeconds(Math.floor((Date.now() - started) / 1000)), 1000);
    return () => clearInterval(id);
  }, []);

  return (
    <section aria-label={title} className="flex items-start gap-4 rounded-card bg-surface p-5 sm:p-6">
      <Pat estado="trabalhando" size={56} />
      <div className="flex flex-col gap-2">
        <h2 className="text-lg font-bold tracking-[-0.02em]">{title}</h2>
        <ol className="flex flex-col gap-1 text-[15px] text-ink-muted">
          {steps.map((s, i) => (
            <li key={s}>
              {i + 1}. {s}
            </li>
          ))}
        </ol>
        <p className="tabular text-[13px] text-ink-subtle" aria-hidden>
          {seconds} s
        </p>
      </div>
    </section>
  );
}
