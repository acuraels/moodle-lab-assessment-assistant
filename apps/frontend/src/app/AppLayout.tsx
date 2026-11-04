import { useEffect } from "react";
import { matchPath, Outlet, useLocation } from "react-router";
import { Sidebar } from "../components/layout/Sidebar";
import { MobileHeader } from "../components/layout/MobileHeader";
import { Icon } from "../components/ui/Icon";
import { HelpModal } from "../components/ui/HelpModal";
import { useMediaQuery } from "../hooks/useMediaQuery";
import { useDemoSession } from "./useDemoSession";
import { useRuntime } from "./runtime";
import { RequestState } from "../components/ui/RequestState";

export function AppLayout() {
  const { pathname } = useLocation();
  const path = pathname.replace(/\/+$/, "") || "/";
  const mobile = useMediaQuery("(max-width: 767px)");
  const { help, setHelp, notice, dismiss, lab, labResource } = useDemoSession();
  const { mode, leave } = useRuntime();
  const settings = path === "/teacher/settings";
  const student = path === "/student/check";
  const known =
    settings ||
    student ||
    path === "/teacher" ||
    !!matchPath("/teacher/submissions/:id", path);
  useEffect(() => {
    const closeHelp = () => setHelp(false);
    window.addEventListener("popstate", closeHelp);
    return () => window.removeEventListener("popstate", closeHelp);
  }, [setHelp]);
  return (
    <div className="app">
      <Sidebar />
      {mobile && <MobileHeader />}
      <div className="main-shell">
        <header className="topbar">
          <div className="breadcrumbs">
            <Icon name="book" size={17} />
            <strong>{lab.name}</strong>
          </div>
        </header>
        <main>
          {known && (
            <div className="page-heading">
              <div>
                <div className="eyebrow">
                  <span /> {lab.name.toUpperCase()}
                </div>
                <h1>
                  {settings
                    ? "Настройки ИИ-ассистента"
                    : student
                      ? "Моя лабораторная работа"
                      : "Обзор работ"}
                </h1>
                <p>
                  {settings
                    ? mode === "demo"
                      ? "Настройте материалы и критерии в демонстрационном режиме."
                      : "Материалы и критерии проверки лабораторной."
                    : student
                      ? mode === "demo"
                        ? "Попробуйте проверку и изучите пример обратной связи."
                        : "Загрузите работу и следите за состоянием попытки."
                      : "Меньше рутины. Больше времени на главное — обучение."}
                </p>
              </div>
            </div>
          )}
          {mode === "api" && (
            <RequestState error={labResource.error} retry={labResource.retry} />
          )}
          <Outlet />
          <footer className="page-footer">
            <span>лаб.ai — пространство для осознанного обучения</span>
            <span>
              <span className="connected-dot" />{" "}
              {mode === "demo"
                ? "Демонстрационный прототип"
                : "API · данные сервера"}
              {" · "}
              <button className="mode-switch" onClick={leave}>
                {mode === "demo" ? "Подключить API" : "Завершить сессию"}
              </button>
            </span>
          </footer>
        </main>
      </div>
      {notice && (
        <div className="toast" role="status">
          <Icon name="check" size={18} />
          {notice}
          <button onClick={dismiss} aria-label="Закрыть уведомление">
            ×
          </button>
        </div>
      )}
      {help && <HelpModal onClose={() => setHelp(false)} />}
    </div>
  );
}
