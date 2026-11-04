import { useEffect, useRef, useState } from "react";
import { errorMessage } from "../api/client";
export function useOperation() {
  const active = useRef<AbortController | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => () => active.current?.abort(), []);
  async function run<T>(
    task: (signal: AbortSignal) => Promise<T>,
    success: (result: T) => void,
  ) {
    if (active.current) return;
    const controller = new AbortController();
    active.current = controller;
    setBusy(true);
    setError("");
    try {
      const result = await task(controller.signal);
      if (!controller.signal.aborted) success(result);
    } catch (reason) {
      if (!controller.signal.aborted) setError(errorMessage(reason));
    } finally {
      if (active.current === controller) active.current = null;
      if (!controller.signal.aborted) setBusy(false);
    }
  }
  return { busy, error, run };
}
