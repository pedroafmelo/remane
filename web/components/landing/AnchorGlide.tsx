"use client";
import { useEffect } from "react";
import { glideStart } from "@/lib/glide";

// Links "#secao": em vez de atravessar a história do hero, salta para perto
// do destino e desliza só o último trecho (uma tela), sem corte seco.
export function AnchorGlide() {
  useEffect(() => {
    const onClick = (e: MouseEvent) => {
      if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
      const a = (e.target as Element).closest<HTMLAnchorElement>('a[href^="#"]');
      const id = a?.getAttribute("href")?.slice(1);
      const el = id ? document.getElementById(id) : null;
      if (!el) return;
      e.preventDefault();

      const margin = parseFloat(getComputedStyle(el).scrollMarginTop) || 0;
      const target = el.getBoundingClientRect().top + scrollY - margin;
      if (matchMedia("(prefers-reduced-motion: reduce)").matches) {
        scrollTo(0, target);
      } else {
        scrollTo(0, glideStart(scrollY, target, innerHeight));
        scrollTo({ top: target, behavior: "smooth" });
      }
      history.pushState(null, "", `#${id}`);
      el.setAttribute("tabindex", "-1");
      el.focus({ preventScroll: true });
    };
    document.addEventListener("click", onClick);
    return () => document.removeEventListener("click", onClick);
  }, []);
  return null;
}
