import type { ReactNode } from "react";

type From = "person" | "agent" | "event" | "typing";

const styles: Record<From, string> = {
  person: "rounded-bubble rounded-tl-md bg-surface",
  agent: "rounded-bubble rounded-tr-md bg-[#d9f5e7]",
  event: "rounded-full bg-surface px-3.5! py-1.5! text-[13px] text-ink-muted",
  typing: "rounded-bubble bg-[#d9f5e7]",
};

const justify: Record<From, string> = {
  person: "justify-start",
  agent: "justify-end",
  event: "justify-center",
  typing: "justify-end",
};

export function ChatBubble({ from, children, attachment }: { from: From; children?: ReactNode; attachment?: string }) {
  return (
    <div className="bubble-in">
      <div className={`flex min-h-0 overflow-hidden pb-2.5 ${justify[from]}`}>
        <div className={`max-w-[86%] px-3.5 py-2.5 text-[14.5px] leading-snug ${styles[from]}`}>
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
      </div>
    </div>
  );
}
