"use client";

import { MoonIcon, SunIcon } from "lucide-react";

import { Button } from "@/components/ui/button";
import { useTema } from "@/hooks/use-tema";

export function TemaToggle() {
  const [tema, setTema] = useTema();
  const escuro = tema === "escuro";
  const rotulo = escuro ? "Mudar para tema claro" : "Mudar para tema escuro";
  return (
    <Button variant="ghost" size="icon-sm" onClick={() => setTema(escuro ? "claro" : "escuro")} aria-label={rotulo} title={rotulo}>
      {escuro ? <SunIcon /> : <MoonIcon />}
    </Button>
  );
}
