import type { Metadata } from "next";
import { Suspense } from "react";

import { LoginCard } from "@/features/auth/login-card";

export const metadata: Metadata = { title: "Entrar" };

export default function LoginPage() {
  return (
    <main className="grid min-h-screen place-items-center bg-sidebar p-4">
      <Suspense>
        <LoginCard />
      </Suspense>
    </main>
  );
}
