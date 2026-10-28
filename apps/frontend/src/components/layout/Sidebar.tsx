import { Link, NavLink, useLocation, useNavigate } from "react-router";
import { Icon } from "../ui/Icon";
import { useDemoSession } from "../../app/useDemoSession";

export function Sidebar({
  variant = "desktop",
  onNavigate,
}: {
  variant?: "desktop" | "drawer";
  onNavigate?: () => void;
}) {
  const { pathname } = useLocation();
  const navigate = useNavigate();
  const { students, setHelp } = useDemoSession();
  const student = pathname.startsWith("/student");
  const drawer = variant === "drawer";
  const navClass = ({ isActive }: { isActive: boolean }) =>
    isActive ? "nav-item active" : "nav-item";
  return (
    <aside
      className={drawer ? "sidebar drawer-sidebar" : "sidebar desktop-sidebar"}
    >
      <Link
        className="brand"
        to={student ? "/student/check" : "/teacher"}
        onClick={onNavigate}
        aria-label="Лаб.АИ — главная"
      >
        <span className="brand-symbol">
          <Icon name="spark" size={25} />
        </span>
        лаб<span className="brand-ai">.ai</span>
      </Link>
      <div className="nav-label single-lab-nav-label">ЛАБОРАТОРНАЯ РАБОТА</div>
      {(!student || drawer) && (
        <nav aria-label="Основная навигация">
          <NavLink
            to="/teacher"
            end={!pathname.startsWith("/teacher/submissions/")}
            className={navClass}
            aria-label="Обзор работ"
            title="Обзор работ"
            onClick={onNavigate}
          >
            <Icon name="grid" />
            Обзор работ<span className="nav-count">{students.length}</span>
          </NavLink>
          <NavLink
            to="/teacher/settings"
            className={navClass}
            aria-label="Настройки ИИ"
            title="Настройки ИИ"
            onClick={onNavigate}
          >
            <Icon name="spark" />
            Настройки ИИ
            <span className="tiny-blue-dot" />
          </NavLink>
        </nav>
      )}
      {drawer && (
        <NavLink to="/student/check" className={navClass} onClick={onNavigate}>
          <Icon name="book" />
          Режим студента
        </NavLink>
      )}
      <div className="sidebar-bottom">
        <button
          className="nav-item"
          aria-label="Как пользоваться"
          title="Как пользоваться"
          onClick={() => {
            onNavigate?.();
            setHelp(true);
          }}
        >
          <Icon name="help" />
          Как пользоваться
          <Icon name="arrow" size={15} />
        </button>
        <div
          className="profile"
          title={
            student
              ? "Елена Кузнецова — режим студента"
              : "Елена Кузнецова — преподаватель"
          }
        >
          <span className="avatar profile-avatar" aria-label="Елена Кузнецова">
            ЕК
          </span>
          <div>
            <strong>Елена Кузнецова</strong>
            <small>{student ? "Режим студента" : "Преподаватель"}</small>
          </div>
          <button
            className="icon-button"
            title="Переключить роль"
            aria-label="Переключить роль"
            onClick={() => {
              onNavigate?.();
              navigate(student ? "/teacher" : "/student/check");
            }}
          >
            <Icon name="down" size={17} />
          </button>
        </div>
      </div>
    </aside>
  );
}
