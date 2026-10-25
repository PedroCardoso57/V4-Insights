import { z } from "zod";

// Espelha a política do backend (app/core/senhas.py); a API é a autoridade.
export const SENHA_MINIMO = 10;

export const novaSenha = z
  .string()
  .min(SENHA_MINIMO, `A senha precisa ter pelo menos ${SENHA_MINIMO} caracteres.`)
  .max(128, "A senha pode ter no máximo 128 caracteres.")
  .refine((s) => s.trim().length > 0, "A senha não pode ser só espaços.");
