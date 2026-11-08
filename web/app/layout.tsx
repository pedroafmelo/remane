import type { Metadata } from "next";
import type { ReactNode } from "react";
import { GeistSans } from "geist/font/sans";
import "./globals.css";

export const metadata: Metadata = {
  title: "Remane · o engenheiro da sua escala de trabalho",
  description:
    "Do planejamento da semana à falta de última hora: o Remane monta, confere e ajusta a escala, e só chama você para decidir.",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="pt-BR" className={GeistSans.variable}>
      <body className="bg-paper font-sans text-ink antialiased">{children}</body>
    </html>
  );
}
