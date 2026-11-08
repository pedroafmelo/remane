import Link from "next/link";
import type { ReactNode } from "react";

type ButtonProps = { href: string; variant?: "primary" | "secondary"; children: ReactNode; className?: string };

const variants = {
  primary: "bg-ink text-white hover:bg-[#2a2c2f]",
  secondary: "border border-line-strong bg-surface text-ink hover:border-ink-subtle",
};

export function Button({ href, variant = "primary", children, className = "" }: ButtonProps) {
  const cls = `inline-flex h-11 items-center justify-center rounded-full px-5.5 text-[15px] font-medium transition-colors ${variants[variant]} ${className}`;
  // Rotas internas pelo Link; âncoras (#) e links externos como <a> comum.
  if (href.startsWith("/")) return <Link href={href} className={cls}>{children}</Link>;
  const external = href.startsWith("http");
  return (
    <a href={href} className={cls} {...(external && { target: "_blank", rel: "noopener noreferrer" })}>
      {children}
    </a>
  );
}
