"use client";

import { Pat } from "@/components/Pat";
import { Shell } from "@/components/plataforma/Shell";
import { SessionGate, useSession } from "@/components/plataforma/session";
import { Card } from "@/components/plataforma/ui";

export default function ColaboradorPage() {
  const session = useSession("colaborador");
  if (!session.me) return <SessionGate session={session} />;
  return (
    <Shell who={session.who} onLogout={session.logout}>
      <h1 className="text-[32px] font-semibold leading-[1.1] tracking-[-0.035em]">Sua escala</h1>
      <Card title="Em construção" id="em-construcao">
        <div className="flex items-center gap-4">
          <Pat estado="trabalhando" size={48} />
          <p className="text-[15px] leading-relaxed text-ink-muted">O celular simulado, com a sua escala e o aviso de falta ao Pat, chega aqui.</p>
        </div>
      </Card>
    </Shell>
  );
}
