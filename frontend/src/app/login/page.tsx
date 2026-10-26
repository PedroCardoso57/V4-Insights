import type { Metadata } from "next";
import { Suspense } from "react";

import { LoginCard } from "@/features/auth/login-card";

export const metadata: Metadata = { title: "Entrar" };

export default function LoginPage() {
  return (
    <main className="relative flex min-h-screen w-full items-center justify-center overflow-hidden bg-[#0b0d11] p-4 sm:p-6">
      <div aria-hidden className="absolute inset-0 scale-[1.01] bg-[url('/v4-office.webp')] bg-cover bg-center bg-no-repeat" />
      <div
        aria-hidden
        className="absolute inset-0"
        style={{
          background:
            "radial-gradient(circle at 50% 45%, rgba(10,10,14,0.52) 0%, rgba(6,7,10,0.84) 75%, rgba(4,4,7,0.92) 100%)",
        }}
      />
      <div aria-hidden className="pointer-events-none absolute -top-28 left-1/2 h-48 w-[620px] -translate-x-1/2 bg-[#e50914]/20 blur-[110px]" />
      <Suspense>
        <LoginCard />
      </Suspense>
    </main>
  );
}
