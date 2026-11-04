import { Icon } from "../../components/ui/Icon";
import { RequestState } from "../../components/ui/RequestState";
import { statusLabels } from "../../api/format";
import type { useStudentAttempt } from "./useStudentAttempt";
export function AttemptFeedback({
  state,
}: {
  state: ReturnType<typeof useStudentAttempt>;
}) {
  const { attempt, result } = state;
  const canSubmit =
    attempt && ["ai_checked", "returned_for_revision"].includes(attempt.status);
  return (
    <>
      <RequestState
        loading={state.loading}
        error={state.error}
        retry={state.retry}
      />
      {!attempt && !state.loading && !state.error && (
        <>
          <p>Выберите попытку в истории или загрузите новый PDF/DOCX.</p>
          <div className="feedback-placeholder">
            <Icon name="file" size={43} />
            <span>Здесь появятся данные сервера</span>
          </div>
        </>
      )}
      {attempt && (
        <>
          <p>{statusLabels[attempt.status]}</p>
          {attempt.status === "ai_failed" ? (
            <div className="ai-result">
              <p>
                Автоматическая проверка пока недоступна. Работа сохранена, но
                обработать её с помощью ИИ не удалось.
              </p>
              <p>
                Это техническое ограничение, а не замечание к вашей работе.
                Отправка преподавателю для этой попытки недоступна.
              </p>
            </div>
          ) : attempt.status === "processing" ? (
            <div className="feedback-placeholder">
              <Icon name="clock" size={43} />
              <span>Ожидаем результат сервера…</span>
            </div>
          ) : (
            <>
              <div className="student-score-card">
                <span>Оценка из сохранённого результата</span>
                <div className="student-score-value">
                  <strong>{result?.score ?? "—"}</strong>
                  {result?.max_score != null && (
                    <span>/ {result.max_score} баллов</span>
                  )}
                </div>
                {result?.score != null &&
                  result.max_score != null &&
                  result.max_score > 0 && (
                    <progress
                      value={result.score}
                      max={result.max_score}
                      aria-label={`Оценка ${result.score} из ${result.max_score}`}
                    />
                  )}
                <p>{result?.conclusion || "Заключение отсутствует."}</p>
              </div>
              {!result?.criteria.length && (
                <p className="muted small">
                  Критерии и рекомендации сервером не предоставлены.
                </p>
              )}
              {result?.criteria.map((criterion, index) => (
                <div className="checklist" key={index}>
                  <Icon name="file" />
                  <div>
                    <strong>
                      {typeof criterion.name === "string"
                        ? criterion.name
                        : `Критерий ${index + 1}`}
                    </strong>
                    <p>
                      {typeof criterion.score === "number"
                        ? criterion.score
                        : "Нет балла"}
                      {typeof criterion.max_score === "number" &&
                        ` / ${criterion.max_score}`}
                    </p>
                    {typeof criterion.comment === "string" && (
                      <p>{criterion.comment}</p>
                    )}
                  </div>
                </div>
              ))}
            </>
          )}
          {attempt.teacher_comment && (
            <div className="ai-result">
              <h3>Комментарий преподавателя</h3>
              <p>{attempt.teacher_comment}</p>
            </div>
          )}
          <button
            className="secondary-button"
            disabled={
              !canSubmit || state.operation.busy || state.sent || !!state.error
            }
            onClick={state.submit}
          >
            {state.sent
              ? "Отправлено преподавателю"
              : "Отправить преподавателю"}
            <Icon name="arrow" size={16} />
          </button>
          {!state.sent && canSubmit && (
            <p className="muted small">
              Сервер не сообщает, отправлялась ли эта попытка ранее. Повторное
              нажатие не создаёт новую попытку.
            </p>
          )}
          {!state.loading && (
            <div className="integration-actions">
              <button className="text-button" onClick={state.retry}>
                Обновить статус
              </button>
            </div>
          )}
        </>
      )}
    </>
  );
}
