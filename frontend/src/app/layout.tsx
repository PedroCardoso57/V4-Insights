import type { Metadata, Viewport } from "next";
import type { ReactNode } from "react";

import { Providers } from "@/components/providers";
import { SCRIPT_TEMA } from "@/lib/tema";

import "./globals.css";

export const metadata: Metadata = {
  title: { default: "V4 Insights", template: "%s · V4 Insights" },
  description: "Plataforma interna de performance de mídia paga — uso exclusivo de colaboradores.",
  robots: { index: false, follow: false },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#f6f7f9" },
    { media: "(prefers-color-scheme: dark)", color: "#09060b" },
  ],
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="pt-BR" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: SCRIPT_TEMA }} />
      </head>
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
