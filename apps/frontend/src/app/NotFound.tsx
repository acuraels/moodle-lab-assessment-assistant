import { Link } from "react-router";

export function NotFound() {
  return (
    <section className="work-panel settings-panel">
      <h1>Страница не найдена</h1>
      <p className="muted small">
        Проверьте адрес или вернитесь к обзору лабораторных работ.
      </p>
      <div className="settings-footer">
        <Link className="primary-button" to="/teacher">
          Вернуться на главную
        </Link>
      </div>
    </section>
  );
}
