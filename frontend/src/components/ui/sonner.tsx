"use client";

import { Toaster as Sonner } from "sonner";

export function Toaster() {
  return (
    <Sonner
      position="bottom-right"
      closeButton
      toastOptions={{
        classNames: {
          toast: "!rounded-xl !border-white/15 !bg-[#110c10] !text-white !text-xs !shadow-2xl",
          description: "!text-white/70",
          success: "[&_[data-icon]]:!text-[#22c55e]",
          error: "[&_[data-icon]]:!text-[#ef4444]",
        },
      }}
    />
  );
}
