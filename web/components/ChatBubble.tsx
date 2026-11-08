import type { ReactNode } from "react";

type From = "person" | "agent" | "event" | "typing";

const styles: Record<From, string> = {
  person: "self-start rounded-bubble rounded-tl-md bg-surface",
  agent: "self-end rounded-bubble rounded-tr-md bg-[#d9f5e7]",
  event: "self-center rounded-full bg-surface px-3.5! py-1.5! text-[13px] text-ink-muted",
  typing: "self-end rounded-bubble bg-[#d9f5e7]",
};

export function ChatBubble({ from, children, attachment }: { from: From; children?: ReactNode; attachment?: string }) {
  return (
    <div className={`max-w-[86%] animate-rise px-3.5 py-2.5 text-[14.5px] leading-snug ${styles[from]}`}>
      {from === "typing" ? (
        <span className="flex gap-1 py-1" aria-label="digitando">
          {[0, 150, 300].map((d) => (
            <i key={d} className="size-1.5 animate-pulse rounded-full bg-accent-strong" style={{ animationDelay: `${d}ms` }} />
          ))}
        </span>
      ) : (
        children
      )}
      {attachment && <div className="mt-2 rounded-lg bg-surface-chat px-2.5 py-1.5 text-[13px] text-ink-muted">{attachment}</div>}
    </div>
  );
}
