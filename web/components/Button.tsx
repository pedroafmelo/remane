import Link from "next/link";
import type { ReactNode } from "react";

type Variant = "primary" | "secondary" | "warning";

type Common = { variant?: Variant; size?: "sm" | "md"; children: ReactNode; className?: string };
type LinkProps = Common & { href: string };
type ActionProps = Common & {
  href?: undefined;
  onClick?: () => void;
  type?: "button" | "submit";
  disabled?: boolean;
  "aria-busy"?: boolean;
};

const variants: Record<Variant, string> = {
  primary: "bg-ink text-white hover:bg-[#2a2c2f]",
  secondary: "border border-line-strong bg-surface text-ink hover:border-ink-subtle",
  // só dentro de um cartão de exceção, para a opção que custa dinheiro
  warning: "border border-warning bg-warning-soft text-warning-ink",
};

const sizes = { sm: "h-9 px-3.5 text-[13px]", md: "h-11 px-5.5 text-[15px]" };

export function Button(props: LinkProps | ActionProps) {
  const { variant = "primary", size = "md", children, className = "" } = props;
  const cls = `inline-flex items-center justify-center rounded-full font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-50 ${sizes[size]} ${variants[variant]} ${className}`;
  if (props.href === undefined) {
    return (
      <button type={props.type ?? "button"} className={cls} onClick={props.onClick} disabled={props.disabled} aria-busy={props["aria-busy"]}>
        {children}
      </button>
    );
  }
  const { href } = props;
  // Rotas internas pelo Link; âncoras (#) e links externos como <a> comum.
  if (href.startsWith("/")) return <Link href={href} className={cls}>{children}</Link>;
  const external = href.startsWith("http");
  return (
    <a href={href} className={cls} {...(external && { target: "_blank", rel: "noopener noreferrer" })}>
      {children}
    </a>
  );
}
