import type { Metadata } from "next";
import type { ReactNode } from "react";
import { GeistSans } from "geist/font/sans";
import "./globals.css";

export const metadata: Metadata = {
  title: "Remane · sua escala se remaneja sozinha",
  description:
    "Um agente que monta a escala dentro da lei e cobre faltas pelo WhatsApp antes de o gestor abrir o celular.",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="pt-BR" className={GeistSans.variable}>
      <body className="bg-paper font-sans text-ink antialiased">{children}</body>
    </html>
  );
}
