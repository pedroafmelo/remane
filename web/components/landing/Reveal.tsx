"use client";
import { useEffect, useRef, type ReactNode } from "react";

// Sobe e aparece uma vez ao entrar na tela. Só esconde o que ainda está abaixo
// da dobra, então sem JS (ou já visível) nada fica invisível.
export function Reveal({ children, delay = 0, className = "" }: { children: ReactNode; delay?: number; className?: string }) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const el = ref.current;
    if (!el || el.getBoundingClientRect().top < innerHeight) return;
    if (matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    el.classList.add("reveal");
    el.style.transitionDelay = `${delay}ms`;
    const io = new IntersectionObserver(
      ([entry]) => {
        if (!entry.isIntersecting) return;
        el.classList.add("in");
        io.disconnect();
      },
      { threshold: 0.15 },
    );
    io.observe(el);
    return () => io.disconnect();
  }, [delay]);
  return (
    <div ref={ref} className={className}>
      {children}
    </div>
  );
}
