import { useState, type ReactNode } from "react";
import { matchPath, Navigate, useLocation } from "react-router";
import { useRuntime } from "./runtime";
import { Icon } from "../components/ui/Icon";

export function SessionGate({ children }: { children: ReactNode }) {
  const runtime = useRuntime();
  const [token, setToken] = useState("");
  const { pathname } = useLocation();
  if (runtime.mode === "demo") return children;
  if (runtime.user) {
    const target =
      runtime.user.role === "instructor" ? "/teacher" : "/student/check";
    if (
      pathname === "/" ||
      pathname === "/index.html" ||
      (runtime.user.role === "student" && pathname.startsWith("/teacher")) ||
      (runtime.user.role === "instructor" && pathname.startsWith("/student"))
    )
      return <Navigate to={target} replace />;
    return (
      <PostLoginRoute key={runtime.epoch} target={target}>
        {children}
      </PostLoginRoute>
    );
  }
  return (
    <div className="session-screen">
      <section className="work-panel session-panel">
        <span className="lab-icon">
          <Icon name="shield" />
        </span>
        <h1>Подключение к ассистенту</h1>
        <p className="muted">API-режим · роль и данные определяет сервер.</p>
        {runtime.loading ? (
          <p role="status">Проверяем сессию…</p>
        ) : (
          <>
            {runtime.error && <p role="alert">{runtime.error}</p>}
            {import.meta.env.DEV || import.meta.env.VITE_ENABLE_TEST_LOGIN === "true" ? (
              <form
                onSubmit={(event) => {
                  event.preventDefault();
                  runtime.connect(token);
                  setToken("");
                }}
              >
                <label>
                  Тестовый JWT
                  <input
                    type="password"
                    autoComplete="off"
                    spellCheck={false}
                    value={token}
                    onChange={(event) => setToken(event.target.value)}
                    required
                    aria-label="Тестовый JWT"
                  />
                </label>
                <p className="muted small">
                  Вход для локальной разработки. Токен проверяется сервером и
                  хранится только до закрытия вкладки.
                </p>
                <button className="primary-button" type="submit">
                  Подключиться
                </button>
              </form>
            ) : (
              <p>
                Откройте эту лабораторную из Moodle, чтобы войти в свою сессию.
              </p>
            )}
            <button className="secondary-button" onClick={runtime.demo}>
              Открыть демонстрацию без сервера
            </button>
          </>
        )}
      </section>
    </div>
  );
}

function PostLoginRoute({
  children,
  target,
}: {
  children: ReactNode;
  target: string;
}) {
  const location = useLocation();
  const [entryKey] = useState(location.key);
  const { freshSession } = useRuntime();
  const known = [
    "/teacher",
    "/teacher/settings",
    "/teacher/submissions/:id",
    "/student",
    "/student/check",
  ].some((path) => matchPath(path, location.pathname));
  // Only a fresh sign-in falls back from an unknown URL. Valid deep links survive,
  // and subsequent unknown navigation still reaches the normal 404 page.
  if (freshSession && location.key === entryKey && !known)
    return <Navigate to={target} replace />;
  return children;
}
