import { useDemoSession } from "../../app/useDemoSession";
import { Icon } from "../../components/ui/Icon";
import { demoResult, lab } from "../../data/mockData";
import { isSupportedFile, openFilePicker } from "../../utils/files";
export function StudentWorkspace() {
  const {
    uploaded,
    setUploaded,
    submitted,
    setSubmitted,
    checking,
    startCheck,
    toast,
  } = useDemoSession();
  const labName = lab.name;
  const upload = (file?: File) => {
    if (!file || checking) return;
    if (!isSupportedFile(file)) {
      toast("Выберите файл PDF или DOCX");
      return;
    }
    setUploaded(file);
    setSubmitted(false);
  };
  return (
    <div className="student-layout student-layout-stacked">
      <section className="work-panel submission-panel">
        <span className="outline-tag">Демонстрационный режим</span>
        <h2>{labName}</h2>
        <p>{lab.description}</p>
        <div className="lab-meta">
          <span>
            <Icon name="clock" size={16} />
            До {lab.deadline}
          </span>
          <span>Попытки не ограничены</span>
        </div>
        <h3>{submitted ? "Пример проверки готов" : "Загрузите вашу работу"}</h3>
        <label
          className="upload-zone"
          tabIndex={checking ? -1 : 0}
          onKeyDown={openFilePicker}
          aria-disabled={checking}
          onDragOver={(e) => e.preventDefault()}
          onDrop={(e) => {
            e.preventDefault();
            if (!checking) upload(e.dataTransfer.files[0]);
          }}
        >
          <Icon name={submitted ? "file" : "upload"} size={32} />
          <strong>
            {uploaded
              ? uploaded.name
              : "Перетащите файл или нажмите для загрузки"}
          </strong>
          <span>Отчёт в формате PDF или DOCX</span>
          <input
            type="file"
            accept=".pdf,.docx"
            disabled={checking}
            onChange={(e) => {
              upload(e.target.files?.[0]);
              e.target.value = "";
            }}
          />
        </label>
        {submitted ? (
          <button
            className="primary-button"
            onClick={() => {
              setUploaded(null);
              setSubmitted(false);
            }}
          >
            <Icon name="plus" size={18} />
            Начать новую попытку
          </button>
        ) : (
          <button
            className="primary-button"
            disabled={!uploaded || checking}
            onClick={startCheck}
          >
            <Icon name="spark" size={18} />
            {checking ? "Готовим пример…" : "Запустить демопроверку"}
          </button>
        )}
        <p className="muted small">
          {submitted
            ? "Это тестовый результат, не анализ файла. Можно начать новую попытку."
            : "Файл не анализируется и не отправляется на сервер. Результат — из тестовых данных."}
        </p>
      </section>
      <section className="work-panel feedback-panel" aria-live="polite">
        <span className="feedback-icon">
          <Icon name="spark" size={26} />
        </span>
        <h2>
          {submitted
            ? "Результаты самопроверки (демо)"
            : "Как выглядит результат проверки"}
        </h2>
        {submitted ? (
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
