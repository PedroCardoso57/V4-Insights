import createClient, { type Middleware } from "openapi-fetch";

import type { components, paths } from "./schema";

/** Tipos dos contratos da API, gerados de openapi.json (npm run gen:api). */
export type Schemas = components["schemas"];

export const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "";
const CSRF_COOKIE = "v4_csrf";

/** Erro no envelope comum `{error: {code, message, request_id}}` (SPEC-08). */
export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly requestId?: string;
  readonly details?: { loc: string[]; msg: string }[];

  constructor(status: number, code: string, message: string, requestId?: string, details?: ApiError["details"]) {
    super(message);
    this.status = status;
    this.code = code;
    this.requestId = requestId;
    this.details = details;
  }
}

function readCookie(name: string): string | null {
  if (typeof document === "undefined") return null;
  const match = document.cookie.split("; ").find((c) => c.startsWith(`${name}=`));
  return match ? decodeURIComponent(match.slice(name.length + 1)) : null;
}

const csrf: Middleware = {
  onRequest({ request }) {
    if (request.method !== "GET" && request.method !== "HEAD") {
      const token = readCookie(CSRF_COOKIE);
      if (token) request.headers.set("X-CSRF-Token", token);
    }
    return request;
  },
};

export const api = createClient<paths>({ baseUrl: API_BASE, credentials: "include" });
api.use(csrf);

interface ErrorEnvelope {
  error?: { code?: string; message?: string; request_id?: string; details?: ApiError["details"] };
}

export async function toApiError(response: Response, body: unknown): Promise<ApiError> {
  const env = (body ?? {}) as ErrorEnvelope;
  const rid = env.error?.request_id ?? response.headers.get("x-request-id") ?? undefined;
  return new ApiError(
    response.status,
    env.error?.code ?? `HTTP_${response.status}`,
    env.error?.message ?? "Não foi possível concluir a operação.",
    rid,
    env.error?.details,
  );
}

/** Desembrulha a resposta do openapi-fetch lançando ApiError em caso de erro. */
export async function unwrap<T>(p: Promise<{ data?: T; error?: unknown; response: Response }>): Promise<T> {
  const { data, error, response } = await p;
  if (!response.ok) throw await toApiError(response, error);
  return data as T;
}

export const loginUrl = () => `${API_BASE}/api/v1/auth/google/login`;
