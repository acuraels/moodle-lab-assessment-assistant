import { useState } from "react";
import { Sidebar } from "../components/layout/Sidebar";
import { Icon } from "../components/ui/Icon";
import { HelpModal } from "../components/ui/HelpModal";
import { TeacherDashboard } from "../features/teacher/TeacherDashboard";
import { SettingsPanel } from "../features/teacher/SettingsPanel";
import { StudentWorkspace } from "../features/student/StudentWorkspace";
import { initialStudents, lab } from "../data/mockData";
import { useToast } from "../hooks/useToast";
import type { Page } from "../types";

export default function App() {
  const [page, setPage] = useState<Page>("dashboard");
  const [students, setStudents] = useState(initialStudents);
  const [help, setHelp] = useState(false);
  const { notice, toast, dismiss } = useToast();
  return (
    <div className="app">
      <Sidebar
        page={page}
        setPage={setPage}
        total={students.length}
        onHelp={() => setHelp(true)}
      />
      <div className="main-shell">
        <header className="topbar">
          <div className="breadcrumbs">
            <Icon name="book" size={17} />
            <strong>{lab.name}</strong>
          </div>
        </header>
        <main>
          <div className="page-heading">
            <div>
              <div className="eyebrow">
                <span /> {lab.name.toUpperCase()}
              </div>
              <h1>
                {page === "settings"
                  ? "Настройки ИИ-ассистента"
                  : page === "student"
                    ? "Моя лабораторная работа"
                    : "Обзор работ"}
              </h1>
              <p>
                {page === "settings"
                  ? "Настройте материалы и критерии в демонстрационном режиме."
                  : page === "student"
                    ? "Попробуйте проверку и изучите пример обратной связи."
                    : "Меньше рутины. Больше времени на главное — обучение."}
              </p>
            </div>
          </div>
          <TeacherDashboard
            active={page === "dashboard"}
            students={students}
            onUpdate={setStudents}
            setPage={setPage}
            onHelp={() => setHelp(true)}
            toast={toast}
          />
          <SettingsPanel active={page === "settings"} toast={toast} />
          <StudentWorkspace active={page === "student"} toast={toast} />
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
