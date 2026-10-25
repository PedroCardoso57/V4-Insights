"use client";

import * as React from "react";
import type { FieldError } from "react-hook-form";

import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";

/** Campo de formulário acessível: label associado, erro anunciado e descrito no input. */
export function Field({
  id,
  label,
  error,
  hint,
  className,
  children,
}: {
  id: string;
  label: string;
  error?: FieldError | { message?: string };
  hint?: string;
  className?: string;
  children: (a11y: { id: string; "aria-invalid": boolean; "aria-describedby"?: string }) => React.ReactNode;
}) {
  const desc = error?.message ? `${id}-erro` : hint ? `${id}-dica` : undefined;
  return (
    <div className={cn("grid gap-1.5", className)}>
      <Label htmlFor={id}>{label}</Label>
      {children({ id, "aria-invalid": !!error?.message, "aria-describedby": desc })}
      {error?.message ? (
        <p id={`${id}-erro`} role="alert" className="text-xs text-destructive">
          {error.message}
        </p>
      ) : hint ? (
        <p id={`${id}-dica`} className="text-xs text-muted-foreground">
          {hint}
        </p>
      ) : null}
    </div>
  );
}
