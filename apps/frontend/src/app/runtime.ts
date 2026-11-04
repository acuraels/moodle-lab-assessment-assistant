import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import { ApiClient, errorMessage, isAbort } from "../api/client";
import { getProfile } from "../api/endpoints";
import type { Profile } from "../api/types";

type Session = {
  token: string;
  labId: string;
  title: string;
  expiresAt?: number;
  fresh: boolean;
};
const storageKey = "lab-ai.session";
function store(session: Session | null) {
  try {
    if (session)
      sessionStorage.setItem(
        storageKey,
        JSON.stringify({ ...session, fresh: false }),
      );
    else sessionStorage.removeItem(storageKey);
  } catch {
    /* The current tab still works when iframe storage is unavailable. */
  }
}
function parseSession(token: string, labId?: string): Session {
  const encoded = token.trim().split(".")[1];
  const bytes = Uint8Array.from(
    atob(encoded.replace(/-/g, "+").replace(/_/g, "/")),
    (char) => char.charCodeAt(0),
  );
  const claims = JSON.parse(new TextDecoder().decode(bytes));
  // Claims supply context only. /me must validate this token before any protected UI renders.
  if (
    typeof claims.lab_id !== "string" ||
    !claims.lab_id ||
    (labId && claims.lab_id !== labId)
  )
    throw new Error("Invalid context");
  return {
    token: token.trim(),
    fresh: true,
    labId: claims.lab_id,
    title:
      typeof claims.lab_title === "string"
        ? claims.lab_title
        : "Лабораторная работа",
    expiresAt:
      typeof claims.exp === "number" && Number.isFinite(claims.exp)
        ? claims.exp * 1000
        : undefined,
  };
}
function bootstrap(): { session: Session | null; error: string } {
  const url = new URL(window.location.href);
  const token = url.searchParams.get("token");
  const labId = url.searchParams.get("lab_id");
  if (url.searchParams.has("token")) {
    url.searchParams.delete("token");
    url.searchParams.delete("lab_id");
    window.history.replaceState(
      window.history.state,
      "",
      url.pathname + url.search + url.hash,
    );
    store(null);
    try {
      return {
        session: parseSession(token || "", labId || undefined),
        error: "",
      };
    } catch {
      return {
        session: null,
        error:
          "Не удалось прочитать контекст запуска. Откройте приложение из Moodle заново.",
      };
    }
  }
  try {
    const saved = JSON.parse(sessionStorage.getItem(storageKey) || "null");
    if (saved && typeof saved.token === "string")
      return {
        session: { ...parseSession(saved.token), fresh: false },
        error: "",
      };
  } catch {
    store(null);
  }
  return { session: null, error: "" };
}
// Read and scrub launch parameters once, before BrowserRouter or a redirect can run.
const initial = bootstrap();
export function useRuntimeState() {
  const [mode, setMode] = useState<"api" | "demo">("api");
  const [session, setSession] = useState<Session | null>(initial.session);
  const [verified, setVerified] = useState<{
    session: Session;
    user: Profile;
  } | null>(null);
  const [error, setError] = useState(initial.error);
  const [epoch, setEpoch] = useState(0);
  const [revision, setRevision] = useState(0);
  const expire = useCallback(() => {
    store(null);
    setSession(null);
    setVerified(null);
    setEpoch((value) => value + 1);
    setError("Сессия истекла или токен недействителен. Войдите снова.");
  }, []);
  const api = useMemo(
    () => (session ? new ApiClient(session.token, expire) : null),
    [session, expire],
  );
  useEffect(() => {
    if (!session || !api || mode !== "api") return;
    const controller = new AbortController();
    getProfile(api, controller.signal)
      .then((user) => {
        if (controller.signal.aborted) return;
        if (user.role !== "instructor" && user.role !== "student")
          throw new Error("Role not supported");
        store(session);
        setVerified({ session, user });
        setError("");
      })
      .catch((reason) => {
        if (isAbort(reason) || controller.signal.aborted) return;
        store(null);
        setSession(null);
        setVerified(null);
        setError(errorMessage(reason));
      });
    return () => controller.abort();
  }, [api, session, mode]);
  useEffect(() => {
    if (!session?.expiresAt || verified?.session !== session) return;
    let timer: ReturnType<typeof setTimeout>;
    const checkExpiry = () => {
      const remaining = session.expiresAt! - Date.now();
      if (remaining <= 0) expire();
      else timer = setTimeout(checkExpiry, Math.min(remaining, 2147483647));
    };
    timer = setTimeout(
      checkExpiry,
      Math.max(0, Math.min(session.expiresAt - Date.now(), 2147483647)),
    );
    return () => clearTimeout(timer);
  }, [session, verified, expire]);
  const connect = (token: string) => {
    try {
      const next = parseSession(token);
      store(null);
      setVerified(null);
      setError("");
      setMode("api");
      setSession(next);
      setEpoch((value) => value + 1);
    } catch {
      setError(
        "Не удалось прочитать JWT. Проверьте токен, не добавляя слово Bearer.",
      );
    }
  };
  const leave = () => {
    store(null);
    setSession(null);
    setVerified(null);
    setError("");
    setMode("api");
    setEpoch((value) => value + 1);
  };
  const demo = () => {
    leave();
    setMode("demo");
  };
  const user = verified?.session === session ? verified.user : null;
  return {
    mode,
    api,
    user,
    freshSession: session?.fresh || false,
    labId: session?.labId || "",
    labTitle: session?.title || "Лабораторная работа",
    loading: mode === "api" && !!session && !user,
    error,
    connect,
    leave,
    demo,
    epoch,
    revision,
    refresh: () => setRevision((value) => value + 1),
  };
}
export const RuntimeContext = createContext<ReturnType<
  typeof useRuntimeState
> | null>(null);
export function useRuntime() {
  const value = useContext(RuntimeContext);
  if (!value) throw new Error("Runtime context missing");
  return value;
}
