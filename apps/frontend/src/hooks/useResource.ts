import { useEffect, useState } from "react";
import { errorMessage } from "../api/client";

export function useResource<T>(
  load: (signal: AbortSignal) => Promise<T>,
  enabled: boolean,
  key: string,
) {
  const [revision, setRevision] = useState(0);
  const requestKey = `${key}:${revision}`;
  const [state, setState] = useState<{ key: string; data?: T; error?: string }>(
    { key: "" },
  );
  useEffect(() => {
    if (!enabled) return;
    const controller = new AbortController();
    load(controller.signal)
      .then((data) => {
        if (!controller.signal.aborted) setState({ key: requestKey, data });
      })
      .catch((error) => {
        if (!controller.signal.aborted)
          setState({ key: requestKey, error: errorMessage(error) });
      });
    return () => controller.abort();
  }, [load, enabled, requestKey]);
  const current = state.key === requestKey && enabled;
  return {
    data: current ? state.data : undefined,
    error: current ? state.error : undefined,
    loading: enabled && (!current || (!state.data && !state.error)),
    retry: () => setRevision((value) => value + 1),
  };
}
