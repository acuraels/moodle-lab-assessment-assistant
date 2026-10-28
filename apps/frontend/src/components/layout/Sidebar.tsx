import { Icon } from "../ui/Icon";
import type { Page } from "../../types";
export function Sidebar({
  page,
  setPage,
  total,
  onHelp,
}: {
  page: Page;
  setPage: (page: Page) => void;
  total: number;
  onHelp: () => void;
}) {
  return (
    <aside className="sidebar">
      <a
        className="brand"
        href="#"
        onClick={(e) => {
          e.preventDefault();
          if (page !== "student") setPage("dashboard");
        }}
      >
        <span className="brand-symbol">
          <Icon name="spark" size={25} />
        </span>
        лаб<span className="brand-ai">.ai</span>
      </a>
      <div className="nav-label single-lab-nav-label">ЛАБОРАТОРНАЯ РАБОТА</div>
      {page !== "student" && (
        <nav>
          <button
            aria-label="Обзор работ"
            className={page === "dashboard" ? "nav-item active" : "nav-item"}
            onClick={() => setPage("dashboard")}
          >
            <Icon name="grid" />
            Обзор работ<span className="nav-count">{total}</span>
          </button>
          <button
            aria-label="Настройки ИИ"
            className={page === "settings" ? "nav-item active" : "nav-item"}
            onClick={() => setPage("settings")}
          >
            <Icon name="spark" />
            Настройки ИИ
            <span className="tiny-blue-dot" />
          </button>
        </nav>
      )}
      <div className="sidebar-bottom">
        <button
          className="nav-item"
          aria-label="Как пользоваться"
          onClick={() => onHelp()}
        >
          <Icon name="help" />
          Как пользоваться
          <Icon name="arrow" size={15} />
        </button>
        <div className="profile">
          <span className="avatar profile-avatar">ЕК</span>
          <div>
            <strong>Елена Кузнецова</strong>
            <small>
              {page === "student" ? "Режим студента" : "Преподаватель"}
            </small>
          </div>
          <button
            className="icon-button"
            title="Переключить роль"
            aria-label="Переключить роль"
            onClick={() =>
              setPage(page === "student" ? "dashboard" : "student")
            }
          >
            <Icon name="down" size={17} />
          </button>
        </div>
      </div>
    </aside>
  );
}
