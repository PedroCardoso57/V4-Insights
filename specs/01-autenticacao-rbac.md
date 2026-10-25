# SPEC-01 — Autenticação Google e permissões

## Fluxo
1. Administrador cadastra colaborador ativo, e-mail e papel.
2. Usuário clica em **Entrar com Google**; backend inicia Authorization Code Flow com state e nonce, usando PKCE quando suportado.
3. Callback valida token ID via biblioteca OIDC (assinatura, issuer, audience, exp, nonce, `email_verified`) e vincula `sub` ao usuário pré-cadastrado; e-mail normalizado serve apenas à identificação inicial, não substitui `sub` após vínculo.
4. Sessão de servidor em cookie `Secure`, `HttpOnly`, `SameSite=Lax`, expiração e revogação no logout; em operações mutáveis exigir CSRF e Origin/Referer apropriados.
5. Login negado a contas não cadastradas, inativas ou cujo `sub` não corresponda ao vínculo salvo.

## Perfis
- **admin**: usuários, clientes, integrações, relatórios, auditoria e configurações.
- **gestor**: clientes atribuídos, gestão de clientes conforme regra de carteira, relatórios, integrações, auditoria restrita.
- **analista**: leitura dos clientes atribuídos, manutenção de integrações, dashboards e relatórios desses clientes.
- **visualizador**: somente leitura de dashboards e relatórios de clientes atribuídos.

A permissão de criar cliente é admin/gestor; somente admin pode atribuir acesso a clientes fora da própria carteira. Auditoria deve ser filtrada por clientes autorizados.

## Endpoints
`GET /auth/google/login`, `GET /auth/google/callback`, `GET /auth/me`, `POST /auth/logout`; `GET/POST /usuarios`, `GET/PATCH /usuarios/{id}`, `PUT /usuarios/{id}/clientes/{cliente_id}`, `DELETE /usuarios/{id}/clientes/{cliente_id}`.

## Critérios de aceite
- Usuário autorizado entra e acessa apenas seus clientes.
- Conta Google válida mas não cadastrada recebe 403 sem criar usuário.
- Usuário inativo, token inválido, callback com state/nonce incorreto e troca de `sub` são recusados.
- Analista/visualizador não criam usuários; tentativas por API retornam 403.
- Logout invalida sessão no servidor; cookie não expõe tokens.
