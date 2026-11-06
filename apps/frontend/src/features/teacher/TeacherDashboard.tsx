import { Outlet, useNavigate } from "react-router";
import { useDemoSession } from "../../app/useDemoSession";
import { Icon } from "../../components/ui/Icon";
import { statusClass } from "../../data/mockData";
import { useRuntime } from "../../app/runtime";
import { RequestState } from "../../components/ui/RequestState";
import type { SubmissionStatus } from "../../types";
const filters = ["Все работы", "Проверено ИИ", "На доработку"] as const;
const PAGE_SIZE = 7;
export function TeacherDashboard() {
  const {
    students,
    query,
    setQuery,
    filter,
    setFilter,
    group,
    setGroup,
    checkedIds,
    setCheckedIds,
    currentPage,
    setCurrentPage,
    sortAscending,
    setSortAscending,
    setHelp,
    lab,
    teacher,
  } = useDemoSession();
  const { mode } = useRuntime();
  const demo = mode === "demo";
  const navigate = useNavigate();
  const openSubmission = (id: string) =>
    navigate("/teacher/submissions/" + encodeURIComponent(id), {
      state: { fromOverview: true },
    });
  const labName = lab.name;
  const filtered = students
    .filter(
      (s) =>
        !demo ||
        (s.name
          .toLocaleLowerCase("ru")
          .includes(query.trim().toLocaleLowerCase("ru")) &&
          (filter === "Все работы" || s.status === filter) &&
          (group === "Все группы" || s.group === group)),
    )
    .sort((a, b) =>
      sortAscending === null
        ? 0
        : a.name.localeCompare(b.name, "ru") * (sortAscending ? 1 : -1),
    );
  const pageCount = demo
    ? Math.max(1, Math.ceil(filtered.length / PAGE_SIZE))
    : Math.max(1, teacher.data?.list.pagination.total_pages || 1);
  const safePage = demo ? Math.min(currentPage, pageCount) : currentPage;
  const visible = !demo
    ? filtered
    : filtered.slice((safePage - 1) * PAGE_SIZE, safePage * PAGE_SIZE);
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
  const serverStats = teacher.data?.stats;
  const stats = !demo
    ? ([
        [
          "file",
          "Всего работ",
          serverStats?.total_submitted ?? "—",
          serverStats
            ? `+${serverStats.submitted_today} за сегодня (UTC)`
            : "Данные сервера",
          "neutral",
        ],
        [
          "spark",
          "Проверено ИИ",
          serverStats?.ai_checked ?? "—",
          "Ожидают вашего решения",
          "blue",
        ],
        [
          "check",
          "Принято",
          serverStats?.accepted ?? "—",
          "Решение преподавателя",
          "green",
        ],
        [
          "clock",
          "Требуют внимания",
          serverStats
            ? serverStats.returned_for_revision + serverStats.processing
            : "—",
          serverStats
            ? `${serverStats.returned_for_revision} на доработке · ${serverStats.processing} в обработке`
            : "Данные сервера",
          "orange",
        ],
      ] as const)
    : ([
        ["file", "Всего работ", students.length, "Тестовые работы", "neutral"],
        [
          "spark",
          "Проверено ИИ",
          count("Проверено ИИ"),
          "Ожидают вашего решения",
          "blue",
        ],
        [
          "check",
          "Принято",
          count("Принято"),
          "Решение преподавателя",
          "green",
        ],
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
      ] as const);
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
                {color === "neutral" && demo ? "демо" : ""}
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
            <span className="outline-tag">{demo ? "Активна" : "API"}</span>
          </div>
          <button
            aria-label="Настройки проверки"
            className="secondary-button settings-button"
            onClick={() => navigate("/teacher/settings")}
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
            {demo ? "Демонстрационный режим" : "Автопроверка пока недоступна"}
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
                  {!demo
                    ? ((f === "Все работы"
                        ? serverStats?.total_submitted
                        : f === "Проверено ИИ"
                          ? serverStats?.ai_checked
                          : serverStats?.returned_for_revision) ?? "—")
                    : f === "Все работы"
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
              {(demo ? ["ИВТ-221", "ИВТ-222"] : teacher.data?.groups || []).map(
                (value) => (
                  <option key={value}>{value}</option>
                ),
              )}
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
                    aria-label={
                      demo
                        ? "Сортировать по имени"
                        : "Сортировать текущую страницу по имени"
                    }
                    title={
                      demo ? undefined : "Сортировка только текущей страницы"
                    }
                  >
                    СТУДЕНТ{" "}
                    <span className="sort-arrow">
                      {sortAscending !== false ? "↓" : "↑"}
                    </span>
                  </button>
                </th>
                <th>ДАТА СДАЧИ</th>
                <th>ФАЙЛЫ</th>
                <th
                  title={
                    demo
                      ? "Демонстрационные оценки из тестовых данных"
                      : "Оценка и максимальный балл из результата сервера"
                  }
                >
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
                      onClick={() => openSubmission(s.id)}
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
                      onClick={() => openSubmission(s.id)}
                    >
                      <Icon name="file" size={16} />
                      {s.files === null
                        ? "Открыть"
                        : `${s.files} ${s.files === 1 ? "файл" : "файла"}`}
                    </button>
                  </td>
                  <td>
                    {s.score !== null ? (
                      <div
                        className={`score ${demo && s.score < 70 ? "low" : ""}`}
                      >
                        <strong>{s.score}</strong>
                        {(demo || s.maxScore != null) && (
                          <span>/ {demo ? 100 : s.maxScore}</span>
                        )}
                        {(demo || (s.maxScore != null && s.maxScore > 0)) && (
                          <i>
                            <b
                              style={{
                                width: `${Math.min(100, Math.max(0, (s.score / (demo ? 100 : s.maxScore!)) * 100))}%`,
                              }}
                            />
                          </i>
                        )}
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
                      onClick={() => openSubmission(s.id)}
                    >
                      <Icon name="arrow" size={17} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {!demo && (
            <RequestState
              loading={teacher.loading}
              error={teacher.error}
              retry={teacher.retry}
            />
          )}
          {!filtered.length &&
            (demo || (!teacher.loading && !teacher.error)) && (
              <div className="empty-state">
                Студенты не найдены. Попробуйте изменить фильтры.
              </div>
            )}
        </div>
        <div className="table-footer">
          <span>
            Показано {visible.length} из{" "}
            {demo
              ? filtered.length
              : (teacher.data?.list.pagination.total_items ?? "—")}{" "}
            работ
            {!demo &&
              sortAscending !== null &&
              " · сортировка текущей страницы"}
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
            {Array.from(
              { length: Math.max(3, Math.min(pageCount, 5)) },
              (_, index) => {
                const page =
                  Math.max(1, Math.min(safePage - 2, pageCount - 4)) + index;
                return (
                  <button
                    key={page}
                    className={safePage === page ? "current" : ""}
                    disabled={page > pageCount}
                    aria-current={safePage === page ? "page" : undefined}
                    onClick={() => setCurrentPage(page)}
                  >
                    {page}
                  </button>
                );
              },
            )}
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
            <h3>
              {demo
                ? "Пример проверки. Решение за вами."
                : "Результат проверки. Решение за вами."}
            </h3>
            <p>
              {demo
                ? "Откройте работу, чтобы изучить пример обратной связи."
                : "Откройте работу, чтобы изучить сохранённую обратную связь."}
              <br />
              Итоговое решение всегда остаётся за вами.
            </p>
          </div>
          <button className="text-button" onClick={() => setHelp(true)}>
            Как это работает
            <Icon name="arrow" size={15} />
          </button>
        </div>
        <div className="privacy-note">
          <span>
            <Icon name="shield" size={22} />
          </span>
          <div>
            <h3>
              {demo ? "Файлы остаются у вас" : "Файлы хранятся на сервере"}
            </h3>
            <p>
              {demo
                ? "Файлы не отправляются на сервер."
                : "Доступ определяется вашей сессией."}
              <br />
              {demo
                ? "LLM и Moodle пока не подключены."
                : "ML и публикация оценок пока не подключены."}
            </p>
          </div>
        </div>
      </div>
      <Outlet />
    </>
  );
}
