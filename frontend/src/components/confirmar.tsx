"use client";

import type { ReactNode } from "react";

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { buttonVariants } from "@/components/ui/button";

export function Confirmar({
  aberto,
  onAberto,
  titulo,
  descricao,
  acao,
  perigo,
  onConfirmar,
}: {
  aberto: boolean;
  onAberto: (v: boolean) => void;
  titulo: string;
  descricao: ReactNode;
  acao: string;
  perigo?: boolean;
  onConfirmar: () => void;
}) {
  return (
    <AlertDialog open={aberto} onOpenChange={onAberto}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>{titulo}</AlertDialogTitle>
          <AlertDialogDescription>{descricao}</AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>Cancelar</AlertDialogCancel>
          <AlertDialogAction className={perigo ? buttonVariants({ variant: "destructive" }) : undefined} onClick={onConfirmar}>
            {acao}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
