import { useEffect } from "react";
import { matchPath, Outlet, useLocation } from "react-router";
import { Sidebar } from "../components/layout/Sidebar";
import { MobileHeader } from "../components/layout/MobileHeader";
import { Icon } from "../components/ui/Icon";
import { HelpModal } from "../components/ui/HelpModal";
import { useMediaQuery } from "../hooks/useMediaQuery";
import { useDemoSession } from "./useDemoSession";
import { lab } from "../data/mockData";

export function AppLayout() {
  const { pathname } = useLocation();
  const path = pathname.replace(/\/+$/, "") || "/";
  const mobile = useMediaQuery("(max-width: 767px)");
  const { help, setHelp, notice, dismiss } = useDemoSession();
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
                    ? "Настройте материалы и критерии в демонстрационном режиме."
                    : student
                      ? "Попробуйте проверку и изучите пример обратной связи."
                      : "Меньше рутины. Больше времени на главное — обучение."}
                </p>
              </div>
            </div>
          )}
          <Outlet />
          <footer className="page-footer">
            <span>лаб.ai — пространство для осознанного обучения</span>
            <span>
              <span className="connected-dot" /> Демонстрационный прототип
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
