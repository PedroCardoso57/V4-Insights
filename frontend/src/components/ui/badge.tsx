import { cva, type VariantProps } from "class-variance-authority";
import * as React from "react";

import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-[11px] font-medium whitespace-nowrap [&_svg]:size-3",
  {
    variants: {
      variant: {
        default: "border-transparent bg-primary-soft text-primary-ink",
        secondary: "border-border bg-subtle text-muted-foreground",
        success: "border-transparent bg-success-soft text-success",
        warning: "border-transparent bg-warning-soft text-warning",
        destructive: "border-transparent bg-destructive-soft text-destructive",
        info: "border-transparent bg-info-soft text-info",
        outline: "border-border text-text-secondary",
      },
    },
    defaultVariants: { variant: "secondary" },
  },
);

const PONTO: Record<string, string> = {
  default: "bg-primary",
  secondary: "bg-faint",
  success: "bg-success",
  warning: "bg-warning",
  destructive: "bg-destructive",
  info: "bg-info animate-pulse",
  outline: "bg-faint",
};

function Badge({
  className,
  variant,
  ponto = false,
  children,
  ...props
}: React.ComponentProps<"span"> & VariantProps<typeof badgeVariants> & { ponto?: boolean }) {
  return (
    <span data-slot="badge" className={cn(badgeVariants({ variant }), className)} {...props}>
      {ponto && <span aria-hidden className={cn("size-1.5 shrink-0 rounded-full", PONTO[variant ?? "secondary"])} />}
      {children}
    </span>
  );
}

export { Badge, badgeVariants };
