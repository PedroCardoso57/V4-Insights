import { cva, type VariantProps } from "class-variance-authority";
import * as React from "react";

import { cn } from "@/lib/utils";

const alertVariants = cva("relative flex w-full items-start gap-3 rounded-xl border px-4 py-3 text-[13px] [&>svg]:mt-0.5 [&>svg]:size-4 [&>svg]:shrink-0", {
  variants: {
    variant: {
      default: "bg-card text-card-foreground",
      destructive: "border-transparent bg-destructive-soft text-destructive",
      warning: "border-transparent bg-warning-soft text-warning",
      info: "border-border bg-subtle text-text-secondary [&>svg]:text-info",
    },
  },
  defaultVariants: { variant: "default" },
});

function Alert({ className, variant, ...props }: React.ComponentProps<"div"> & VariantProps<typeof alertVariants>) {
  return <div role="alert" className={cn(alertVariants({ variant }), className)} {...props} />;
}

export { Alert };
