"use client";

import { Pat } from "../Pat";
import { Shell, type Area } from "./Shell";
import { SessionGate, useSession } from "./session";
import { Card } from "./ui";

/** Tela provisória de uma área do gestor, até a área ganhar o conteúdo dela. */
export function AreaPlaceholder({ area, title, text }: { area: Area; title: string; text: string }) {
  const session = useSession("gestor");
  if (!session.me) return <SessionGate session={session} />;
  return (
    <Shell who={session.who} area={area} onLogout={session.logout}>
      <h1 className="text-[32px] font-semibold leading-[1.1] tracking-[-0.035em]">{title}</h1>
      <Card title="Em construção" id="em-construcao">
        <div className="flex items-center gap-4">
          <Pat estado="trabalhando" size={48} />
          <p className="text-[15px] leading-relaxed text-ink-muted">{text}</p>
        </div>
      </Card>
    </Shell>
  );
}
