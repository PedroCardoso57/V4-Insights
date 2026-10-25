"use client";

import { ShieldAlertIcon } from "lucide-react";
import { useSearchParams } from "next/navigation";

import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { loginUrl } from "@/services/api/client";

const MOTIVOS: Record<string, string> = {
  acesso_negado: "Sua conta Google não está autorizada. Peça a um administrador para cadastrar seu e-mail.",
  token_invalido: "Não foi possível validar sua identidade no Google. Tente novamente.",
  state_invalido: "O login expirou ou foi reaproveitado. Inicie novamente.",
  autorizacao_cancelada: "O login foi cancelado na tela do Google.",
};

export function LoginCard() {
  const erro = useSearchParams().get("erro");
  return (
    <Card className="w-full max-w-sm">
      <CardHeader className="flex-col items-start">
        <CardTitle className="text-2xl">
          V4 <span className="text-primary">Insights</span>
        </CardTitle>
        <CardDescription>Acesso exclusivo para colaboradores cadastrados.</CardDescription>
      </CardHeader>
      <CardContent className="grid gap-4">
        {erro && (
          <Alert variant="destructive">
            <ShieldAlertIcon />
            <span>{MOTIVOS[erro] ?? "Não foi possível entrar."}</span>
          </Alert>
        )}
        <Button asChild size="lg" className="w-full">
          <a href={loginUrl()}>Entrar com Google</a>
        </Button>
        <p className="text-center text-xs text-muted-foreground">Não há cadastro público: o acesso é concedido por convite.</p>
      </CardContent>
    </Card>
  );
}
