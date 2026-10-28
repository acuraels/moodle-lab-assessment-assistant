import { useCallback, useEffect, useRef, useState } from "react";

export function useToast() {
  const [notice, setNotice] = useState("");
  const timer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const dismiss = useCallback(() => {
    clearTimeout(timer.current);
    setNotice("");
  }, []);
  const toast = useCallback((message: string) => {
    clearTimeout(timer.current);
    setNotice(message);
    timer.current = setTimeout(() => setNotice(""), 6000);
  }, []);
  useEffect(() => () => clearTimeout(timer.current), []);
  return { notice, toast, dismiss };
}
