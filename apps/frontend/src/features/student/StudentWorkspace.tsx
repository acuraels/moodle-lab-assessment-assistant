import { useDemoSession } from "../../app/useDemoSession";
import { Icon } from "../../components/ui/Icon";
import { demoResult } from "../../data/mockData";
import { isSupportedFile, openFilePicker } from "../../utils/files";
import { useRuntime } from "../../app/runtime";
import { useStudentAttempt } from "./useStudentAttempt";
import { AttemptFeedback } from "./AttemptFeedback";
import { RequestState } from "../../components/ui/RequestState";
import { formatDate, statusLabels } from "../../api/format";
import { downloadFile } from "../../api/endpoints";
export function StudentWorkspace() {
  const {
    uploaded,
    setUploaded,
    submitted,
    setSubmitted,
    checking,
    startCheck,
    toast,
    lab,
  } = useDemoSession();
  const { mode, api } = useRuntime();
  const demo = mode === "demo";
  const state = useStudentAttempt(toast);
  const busy = demo ? checking : state.operation.busy;
  const hasAttempt = demo ? submitted : !!state.selection;
  const labName = lab.name;
  const upload = (file?: File) => {
    if (!file || busy) return;
    if (!isSupportedFile(file)) {
      toast("Выберите файл PDF или DOCX");
      return;
    }
    if (!demo && file.size > 20 * 1024 * 1024) {
      toast("Файл слишком большой. Допустимо до 20 МБ.");
      return;
    }
    if (!demo) state.newAttempt();
    setUploaded(file);
    setSubmitted(false);
  };
  return (
    <div className="student-layout student-layout-stacked">
      <section className="work-panel submission-panel">
        <span className="outline-tag">
          {demo
            ? "Демонстрационный режим"
            : "API · файлы сохраняются на сервере"}
        </span>
        <h2>{labName}</h2>
        <p>{lab.description}</p>
        <div className="lab-meta">
          <span>
            <Icon name="clock" size={16} />
            {demo ? `До ${lab.deadline}` : "Срок сдачи недоступен в API"}
          </span>
          <span>
            {demo ? "Попытки не ограничены" : "Лимит попыток проверяет сервер"}
          </span>
        </div>
        {!demo && (
          <div className="attempt-history">
            <h3>История попыток</h3>
            <RequestState
              loading={state.history.loading}
              error={state.history.error}
              retry={state.history.retry}
            />
            {state.history.data && (
              <>
                {state.history.data.items.length ? (
                  <select
                    aria-label="Попытка"
                    value={state.selection || ""}
                    disabled={busy}
                    onChange={(event) => {
                      state.select(event.target.value);
                      setUploaded(null);
                    }}
                  >
                    <option value="" disabled>
                      Выберите попытку
                    </option>
                    {state.selection &&
                      !state.history.data.items.some(
                        (item) => item.id === state.selection,
                      ) && (
                        <option value={state.selection}>Текущая попытка</option>
                      )}
                    {state.history.data.items.map((item) => (
                      <option key={item.id} value={item.id}>
                        № {item.number} · {formatDate(item.submitted_at)} ·{" "}
                        {statusLabels[item.status]}
                      </option>
                    ))}
                  </select>
                ) : (
                  <p className="muted">Сохранённых попыток пока нет.</p>
                )}
                <div className="integration-actions">
                  <button
                    className="secondary-button"
                    disabled={busy || state.page <= 1}
                    onClick={() => state.changePage(state.page - 1)}
                  >
                    Назад
                  </button>
                  <span>
                    {state.page} /{" "}
                    {Math.max(1, state.history.data.pagination.total_pages)}
                  </span>
                  <button
                    className="secondary-button"
                    disabled={
                      busy ||
                      state.page >= state.history.data.pagination.total_pages
                    }
                    onClick={() => state.changePage(state.page + 1)}
                  >
                    Далее
                  </button>
                </div>
              </>
            )}
          </div>
        )}
        <h3>
          {demo && submitted
            ? "Пример проверки готов"
            : hasAttempt
              ? "Сохранённая работа"
              : "Загрузите вашу работу"}
        </h3>
        <label
          className="upload-zone"
          tabIndex={busy ? -1 : 0}
          onKeyDown={openFilePicker}
          aria-disabled={busy}
          onDragOver={(e) => e.preventDefault()}
          onDrop={(e) => {
            e.preventDefault();
            if (!busy) upload(e.dataTransfer.files[0]);
          }}
        >
          <Icon name={hasAttempt ? "file" : "upload"} size={32} />
          <strong>
            {!demo && state.attempt?.file
              ? state.attempt.file.name
              : uploaded
                ? uploaded.name
                : "Перетащите файл или нажмите для загрузки"}
          </strong>
          <span>Отчёт в формате PDF или DOCX</span>
          <input
            type="file"
            accept=".pdf,.docx"
            disabled={busy}
            onChange={(e) => {
              upload(e.target.files?.[0]);
              e.target.value = "";
            }}
          />
        </label>
        {hasAttempt ? (
          <button
            className="primary-button"
            disabled={busy}
            onClick={() => {
              setUploaded(null);
              setSubmitted(false);
              if (!demo) state.newAttempt();
            }}
          >
            <Icon name="plus" size={18} />
            Начать новую попытку
          </button>
        ) : (
          <button
            className="primary-button"
            disabled={!uploaded || busy}
            onClick={() => {
              if (demo) startCheck();
              else if (uploaded) state.upload(uploaded);
            }}
          >
            <Icon name="spark" size={18} />
            {demo
              ? checking
                ? "Готовим пример…"
                : "Запустить демопроверку"
              : busy
                ? "Отправляем…"
                : "Загрузить и проверить"}
          </button>
        )}
        <p className="muted small">
          {!demo
            ? `${hasAttempt ? "Работа сохранена на сервере." : "Файл будет сохранён на сервере."} ML пока не подключён; успешная автоматическая оценка недоступна.`
            : submitted
              ? "Это тестовый результат, не анализ файла. Можно начать новую попытку."
              : "Файл не анализируется и не отправляется на сервер. Результат — из тестовых данных."}
        </p>
        {!demo && state.attempt?.file && (
          <button
            className="text-button"
            disabled={busy}
            onClick={() => {
              const file = state.attempt!.file!;
              void state.operation.run(
                (signal) => downloadFile(api!, file.id, file.name, signal),
                () => toast("Файл получен. Скачивание начато."),
              );
            }}
          >
            Скачать сохранённый файл
          </button>
        )}
        {!demo && <RequestState error={state.operation.error} />}
      </section>
      <section className="work-panel feedback-panel" aria-live="polite">
        <span className="feedback-icon">
          <Icon name="spark" size={26} />
        </span>
        <h2>
          {!demo
            ? "Результат попытки"
            : submitted
              ? "Результаты самопроверки (демо)"
              : "Как выглядит результат проверки"}
        </h2>
        {!demo ? (
          <AttemptFeedback state={state} />
        ) : submitted ? (
          <>
            <div className="student-score-card">
              <span>Демонстрационная оценка</span>
              <div className="student-score-value">
                <strong>{demoResult.score}</strong>
                <span>/ 100 баллов</span>
              </div>
              <progress
                value={demoResult.score}
                max={100}
                aria-label={`Демонстрационная оценка: ${demoResult.score} из 100`}
              />
              <p>Нужна небольшая доработка</p>
            </div>
            <p className="muted small">
              Оценка и замечания — пример. Они не связаны с содержимым вашего
              файла.
            </p>
            {demoResult.checklist.map(({ text, needsRevision }) => (
              <div
                className={`checklist ${needsRevision ? "warning" : ""}`}
                key={text}
              >
                <Icon name={needsRevision ? "clock" : "check"} />
                <div>
                  <strong>{needsRevision ? "Доработать" : "Выполнено"}</strong>
                  <p>{text}</p>
                </div>
              </div>
            ))}
            <button
              className="secondary-button"
              onClick={() =>
                toast(
                  "Отправка недоступна: сервер и Moodle не подключены. Файл остаётся у вас.",
                )
              }
            >
              Отправить преподавателю
              <Icon name="arrow" size={16} />
            </button>
          </>
        ) : (
          <>
            <p>
              {checking
                ? "Готовим демонстрационный результат. Содержимое файла не анализируется."
                : "Выберите PDF или DOCX и запустите демопроверку, чтобы увидеть пример оценки, замечаний и рекомендаций."}
            </p>
            <div className="feedback-placeholder">
              <Icon name={checking ? "clock" : "file"} size={43} />
              <span>
                {checking
                  ? "Готовим тестовый результат…"
                  : "Здесь появятся результаты проверки"}
              </span>
            </div>
          </>
        )}
      </section>
    </div>
  );
}
