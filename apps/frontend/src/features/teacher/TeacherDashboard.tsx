import { useState } from "react";
import { Icon } from "../../components/ui/Icon";
import { lab, statusClass } from "../../data/mockData";
import { SubmissionModal } from "./SubmissionModal";
import type { Notify, Page, Submission, SubmissionStatus } from "../../types";
const filters = ["Все работы", "Проверено ИИ", "На доработку"] as const;
const PAGE_SIZE = 7;
export function TeacherDashboard({
  active,
  students,
  onUpdate,
  setPage,
  onHelp,
  toast,
}: {
  active: boolean;
  students: Submission[];
  onUpdate: (students: Submission[]) => void;
  setPage: (page: Page) => void;
  onHelp: () => void;
  toast: Notify;
}) {
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState<(typeof filters)[number]>("Все работы");
  const [group, setGroup] = useState("Все группы");
  const [selected, setSelected] = useState<Submission | null>(null);
  const [checkedIds, setCheckedIds] = useState<string[]>([]);
  const [currentPage, setCurrentPage] = useState(1);
  const [sortAscending, setSortAscending] = useState<boolean | null>(null);
  const labName = lab.name;
  const filtered = students
    .filter(
      (s) =>
        s.name
          .toLocaleLowerCase("ru")
          .includes(query.trim().toLocaleLowerCase("ru")) &&
        (filter === "Все работы" || s.status === filter) &&
        (group === "Все группы" || s.group === group),
    )
    .sort((a, b) =>
      sortAscending === null
        ? 0
        : a.name.localeCompare(b.name, "ru") * (sortAscending ? 1 : -1),
    );
  const pageCount = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const safePage = Math.min(currentPage, pageCount);
  const visible = filtered.slice(
    (safePage - 1) * PAGE_SIZE,
    safePage * PAGE_SIZE,
  );
  const allChecked =
    visible.length > 0 && visible.every((s) => checkedIds.includes(s.id));
  const someChecked = visible.some((s) => checkedIds.includes(s.id));
  const toggleVisible = (checked: boolean) =>
    setCheckedIds((ids) =>
      checked
        ? [...new Set([...ids, ...visible.map((s) => s.id)])]
        : ids.filter((id) => !visible.some((s) => s.id === id)),
    );
  const count = (status: SubmissionStatus) =>
    students.filter((s) => s.status === status).length;
  const stats = [
    ["file", "Всего работ", students.length, "Тестовые работы", "neutral"],
    [
      "spark",
      "Проверено ИИ",
      count("Проверено ИИ"),
      "Ожидают вашего решения",
      "blue",
    ],
    ["check", "Принято", count("Принято"), "Решение преподавателя", "green"],
    [
      "clock",
      "Требуют внимания",
      count("На доработку") + count("В обработке"),
      count("На доработку") +
        " на доработке · " +
        count("В обработке") +
        " в обработке",
      "orange",
    ],
  ] as const;
  const decide = (status: SubmissionStatus, comment: string) => {
    if (!selected) return;
    onUpdate(
      students.map((s) =>
        s.id === selected.id ? { ...s, status, comment } : s,
      ),
    );
    setSelected(null);
    toast(
      "Демо: решение и комментарий сохранены до перезагрузки. Студенту ничего не отправлено.",
    );
  };
  if (!active) return null;
  return (
    <>
      <div className="stats-grid">
        {stats.map(([icon, label, value, sub, color]) => (
          <div className="stat-card" key={label}>
            <div className="stat-top">
              <span>{label}</span>
              <span className={`stat-icon ${color}`}>
                <Icon name={icon} size={19} />
              </span>
            </div>
            <div className="stat-value">
              {value}
              <span className={`stat-trend ${color}`}>
                {color === "neutral" ? "демо" : ""}
              </span>
            </div>
            <div
              className={`stat-caption ${color === "neutral" ? "green-text" : ""}`}
            >
              {sub}
            </div>
          </div>
        ))}
      </div>
      <section className="work-panel">
        <div className="panel-heading">
          <div className="lab-heading">
            <span className="lab-icon">
              <Icon name="book" size={22} />
            </span>
            <div>
              <h2>{labName}</h2>
              <p>{lab.description}</p>
            </div>
            <span className="outline-tag">Активна</span>
          </div>
          <button
            aria-label="Настройки проверки"
            className="secondary-button settings-button"
            onClick={() => setPage("settings")}
          >
            <Icon name="settings" size={16} />
            Настройки проверки
          </button>
        </div>
        <div className="lab-meta">
          <span>
            <Icon name="book" size={15} />
            {lab.subject}
          </span>
          <span>
            <Icon name="clock" size={15} />
            Срок сдачи: {lab.deadline}
          </span>
          <span className="ai-enabled">
            <Icon name="spark" size={15} />
            Демонстрационный режим
          </span>
        </div>
        <div className="table-tools">
          <div className="tabs">
            {filters.map((f) => (
              <button
                className={filter === f ? "tab selected" : "tab"}
                key={f}
                onClick={() => {
                  setFilter(f);
                  setCurrentPage(1);
                }}
              >
                {f}
                <span>
                  {f === "Все работы"
                    ? students.length
                    : students.filter((s) => s.status === f).length}
                </span>
              </button>
            ))}
          </div>
          <div className="table-filters">
            <label className="search-box">
              <Icon name="search" size={17} />
              <input
                aria-label="Найти студента"
                placeholder="Найти студента"
                value={query}
                onChange={(e) => {
                  setQuery(e.target.value);
                  setCurrentPage(1);
                }}
              />
            </label>
            <select
              aria-label="Группа"
              value={group}
              onChange={(e) => {
                setGroup(e.target.value);
                setCurrentPage(1);
              }}
            >
              <option>Все группы</option>
              <option>ИВТ-221</option>
              <option>ИВТ-222</option>
            </select>
          </div>
        </div>
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th className="checkbox-cell">
                  <input
                    type="checkbox"
                    aria-label="Выбрать все работы"
                    checked={allChecked}
                    ref={(element) => {
                      if (element)
                        element.indeterminate = someChecked && !allChecked;
                    }}
                    onChange={(e) => toggleVisible(e.target.checked)}
                  />
                </th>
                <th
                  aria-sort={
                    sortAscending === null
                      ? "none"
                      : sortAscending
                        ? "ascending"
                        : "descending"
                  }
                >
                  <button
                    onClick={() => setSortAscending((value) => !value)}
                    aria-label="Сортировать по имени"
                  >
                    СТУДЕНТ{" "}
                    <span className="sort-arrow">
                      {sortAscending !== false ? "↓" : "↑"}
                    </span>
                  </button>
                </th>
                <th>ДАТА СДАЧИ</th>
                <th>ФАЙЛЫ</th>
                <th title="Демонстрационные оценки из тестовых данных">
                  ОЦЕНКА ИИ <Icon name="help" size={13} />
                </th>
                <th>СТАТУС</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {visible.map((s) => (
                <tr key={s.id}>
                  <td>
                    <input
                      type="checkbox"
                      aria-label={`Выбрать ${s.name}`}
                      checked={checkedIds.includes(s.id)}
                      onChange={(e) =>
                        setCheckedIds((ids) =>
                          e.target.checked
                            ? [...ids, s.id]
                            : ids.filter((id) => id !== s.id),
                        )
                      }
                    />
                  </td>
                  <td>
                    <button
                      className="student-cell"
                      onClick={() => setSelected(s)}
                    >
                      <span className={`avatar ${s.color}`}>{s.initials}</span>
                      <span>
                        <strong>{s.name}</strong>
                        <small>{s.group}</small>
                      </span>
                    </button>
                  </td>
                  <td className="date-cell">{s.date}</td>
                  <td>
                    <button
                      className="file-count"
                      onClick={() => setSelected(s)}
                    >
                      <Icon name="file" size={16} />
                      {s.files} {s.files === 1 ? "файл" : "файла"}
                    </button>
                  </td>
                  <td>
                    {s.score !== null ? (
                      <div className={`score ${s.score < 70 ? "low" : ""}`}>
                        <strong>{s.score}</strong>
                        <span>/ 100</span>
                        <i>
                          <b style={{ width: `${s.score}%` }} />
                        </i>
                      </div>
                    ) : (
                      <span className="no-score">—</span>
                    )}
                  </td>
                  <td>
                    <span className={`status ${statusClass[s.status]}`}>
                      <span />
                      {s.status}
                    </span>
                  </td>
                  <td>
                    <button
                      className="row-arrow icon-button"
                      title="Открыть работу"
                      aria-label={`Открыть работу: ${s.name}`}
                      onClick={() => setSelected(s)}
                    >
                      <Icon name="arrow" size={17} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {!filtered.length && (
            <div className="empty-state">
              Студенты не найдены. Попробуйте изменить фильтры.
            </div>
          )}
        </div>
        <div className="table-footer">
          <span>
            Показано {visible.length} из {filtered.length} работ
          </span>
          <div className="pagination">
            <button
              className="icon-button"
              aria-label="Предыдущая страница"
              disabled={safePage === 1}
              onClick={() => setCurrentPage(safePage - 1)}
            >
              <Icon name="back" size={15} />
            </button>
            {Array.from({ length: Math.max(3, pageCount) }, (_, index) => (
              <button
                key={index}
                className={safePage === index + 1 ? "current" : ""}
                disabled={index + 1 > pageCount}
                aria-current={safePage === index + 1 ? "page" : undefined}
                onClick={() => setCurrentPage(index + 1)}
              >
                {index + 1}
              </button>
            ))}
            <button
              className="icon-button"
              aria-label="Следующая страница"
              disabled={safePage === pageCount}
              onClick={() => setCurrentPage(safePage + 1)}
            >
              <Icon name="arrow" size={15} />
            </button>
          </div>
        </div>
      </section>
      <div className="bottom-grid">
        <div className="assistant-banner">
          <div className="assistant-art">
            <Icon name="spark" size={32} />
            <span className="orbit orbit-one" />
            <span className="orbit orbit-two" />
          </div>
          <div>
            <h3>Пример проверки. Решение за вами.</h3>
            <p>
              Откройте работу, чтобы изучить пример обратной связи.
              <br />
              Итоговое решение всегда остаётся за вами.
            </p>
          </div>
          <button className="text-button" onClick={() => onHelp()}>
            Как это работает
            <Icon name="arrow" size={15} />
          </button>
        </div>
        <div className="privacy-note">
          <span>
            <Icon name="shield" size={22} />
          </span>
          <div>
            <h3>Файлы остаются у вас</h3>
            <p>
              Файлы не отправляются на сервер.
              <br />
              LLM и Moodle пока не подключены.
            </p>
          </div>
        </div>
      </div>
      {selected && (
        <SubmissionModal
          key={selected.id}
          submission={selected}
          onClose={() => setSelected(null)}
          onDecide={decide}
          toast={toast}
        />
      )}
    </>
  );
}
