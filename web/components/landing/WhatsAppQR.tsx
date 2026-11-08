"use client";
import { QRCodeSVG } from "qrcode.react";

export function WhatsAppQR({ href }: { href: string }) {
  return <QRCodeSVG value={href} size={176} fgColor="#17181a" bgColor="#ffffff" marginSize={2} title="QR code para abrir a conversa com o agente no WhatsApp" />;
}
