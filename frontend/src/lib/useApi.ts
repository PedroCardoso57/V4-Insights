import { useCallback, useEffect, useState } from "react";

// Carrega dados assíncronos com estados de loading/erro e função de recarga.
// `deps` determina quando o loader é executado novamente.
export function useApi<T>(loader: () => Promise<T>, deps: unknown[]) {
  const [data, setData] = useState<T | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [carregando, setCarregando] = useState(true);
  const [versao, setVersao] = useState(0);
  const chave = JSON.stringify(deps);

  useEffect(() => {
    let ativo = true;
    setCarregando(true);
    setErro(null);
    loader()
      .then((d) => ativo && setData(d))
      .catch((e: Error) => ativo && setErro(e.message))
      .finally(() => ativo && setCarregando(false));
    return () => {
      ativo = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [chave, versao]);

  const recarregar = useCallback(() => setVersao((v) => v + 1), []);
  return { data, erro, carregando, recarregar, setData };
}
