import { cn } from "@/lib/utils";

/** Símbolo oficial da V4 Company (vetorizado do material da marca). Usa a cor do texto. */
export function SimboloV4({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 259 260" aria-hidden className={cn("shrink-0", className)}>
      <path
        fill="currentColor"
        fillRule="evenodd"
        d="M0 0h31v103l78-78h39L21.5 151.5 0 130zM31 167 173 25h45v140h41v49h-41v46h-47v-46H31zm140-75-73 73h73z"
      />
    </svg>
  );
}

/** Selo da marca: símbolo branco sobre o vermelho V4 (a marca não usa o símbolo vermelho sobre fundo escuro). */
export function SeloV4({ className, simbolo }: { className?: string; simbolo?: string }) {
  return (
    <span aria-hidden className={cn("flex items-center justify-center bg-primary text-white", className)}>
      <SimboloV4 className={cn("size-[55%]", simbolo)} />
    </span>
  );
}
