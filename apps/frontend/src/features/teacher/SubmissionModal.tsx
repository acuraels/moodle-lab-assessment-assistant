import { useState } from "react";
import { Icon } from "../../components/ui/Icon";
import { Modal } from "../../components/ui/Modal";
import { CriteriaAssessment } from "../../components/ui/CriteriaAssessment";
import { statusClass } from "../../data/mockData";
import type { Notify, Submission, SubmissionStatus } from "../../types";
import type { AIResult, SubmissionDetail } from "../../api/types";
import { useRuntime } from "../../app/runtime";
import { useDemoSession } from "../../app/useDemoSession";
import { downloadFile } from "../../api/endpoints";
import { useOperation } from "../../hooks/useOperation";
import { ServerCriteria } from "../../components/ui/ServerCriteria";
import { RequestState } from "../../components/ui/RequestState";
export function SubmissionModal({
  submission,
  onClose,
  onDecide,
  toast,
  detail,
  result,
  resultError,
  busy,
  error,
  retry,
}: {
  submission: Submission;
  onClose: () => void;
  onDecide: (status: SubmissionStatus, comment: string) => void;
  toast: Notify;
  detail?: SubmissionDetail;
  result?: AIResult;
  resultError?: string;
  busy?: boolean;
  error?: string;
  retry?: () => void;
}) {
  const [comment, setComment] = useState(submission.comment ?? "");
  const { lab } = useDemoSession();
  const { mode, api } = useRuntime();
  const demo = mode === "demo";
  const download = useOperation();
  const labName = detail?.lab.title || lab.name;
  const files = demo
    ? Array.from({ length: submission.files || 0 }, (_, index) => ({
        id: String(index),
        name:
          index === 0
            ? "Отчёт по лабораторной.pdf"
            : `Приложение ${index}.docx`,
      }))
    : detail?.files || [];
  return (
    <Modal
      titleId="submission-title"
      className="detail-modal"
      onClose={onClose}
    >
      <button
        className="close-modal"
        onClick={() => onClose()}
        aria-label="Закрыть"
      >
        ×
      </button>
      <div className="eyebrow">
        {demo ? "ПРИМЕР ПРОВЕРКИ" : "РЕЗУЛЬТАТ ПРОВЕРКИ"}
      </div>
      <h2 id="submission-title">{submission.name}</h2>
      <p>
        {submission.group} · {labName}
        {!demo && ` · ${submission.date}`}
      </p>
      <span className={`status ${statusClass[submission.status]}`}>
        <span />
        {submission.status}
      </span>
      <div className="detail-files">
        <h3>{demo ? "Файлы студента (пример)" : "Файлы студента"}</h3>
        {files.map((file) => (
          <button
            key={file.id}
            disabled={download.busy}
            onClick={() =>
              demo
                ? toast(
                    "Файл из тестовых данных недоступен для скачивания. Сервер не подключён.",
                  )
                : void download.run(
                    (signal) => downloadFile(api!, file.id, file.name, signal),
                    () => toast("Файл получен. Скачивание начато."),
                  )
            }
          >
            <Icon name="file" />
            <span>{file.name}</span>
            <Icon name="download" size={17} />
          </button>
        ))}
      </div>
      <RequestState error={download.error} />
      <div className="ai-result">
        <h3>
          <Icon name="spark" />
          {demo ? "Заключение ИИ (пример)" : "Заключение ИИ"}{" "}
          <span>
            {submission.score !== null
              ? `${submission.score}${demo ? " / 100" : submission.maxScore != null ? ` / ${submission.maxScore}` : ""}`
              : "Нет оценки"}
          </span>
        </h3>
        <p>
          {!demo
            ? detail?.status === "ai_failed"
              ? "Автоматическая проверка недоступна. Это не оценка качества работы."
              : detail?.ai_conclusion || "Заключение пока отсутствует."
            : submission.score === null
              ? "Пример работы без оценки. Серверная проверка пока не подключена."
              : submission.score < 70
                ? "Основные требования выполнены частично. Необходимо дополнить описание алгоритма и добавить выводы."
                : "Работа соответствует основным критериям. Структура отчёта и реализация алгоритма корректны. Рекомендуется проверить оформление выводов."}
        </p>
        <small>
          {demo
            ? "Тестовые данные, не анализ файла. Решение и комментарий сохраняются только до перезагрузки."
            : "Сохранённый результат сервера. Новые автоматические проверки пока недоступны."}
        </small>
      </div>
      {demo ? (
        <CriteriaAssessment score={submission.score} />
      ) : (
        <>
          <RequestState error={resultError} retry={retry} />
          <ServerCriteria result={result} />
        </>
      )}
      <label className="comment-label">
        Комментарий преподавателя
        <textarea
          value={comment}
          onChange={(e) => setComment(e.target.value)}
          rows={3}
          maxLength={10000}
          disabled={busy}
          placeholder="Добавьте обратную связь студенту…"
        />
      </label>
      <RequestState error={error} />
      <div className="modal-actions">
        <button
          className="secondary-button"
          disabled={
            busy ||
            (!demo &&
              (!detail?.actions.can_return_for_revision || !comment.trim()))
          }
          title={
            !demo && !comment.trim()
              ? "Для возврата нужен комментарий"
              : undefined
          }
          onClick={() => onDecide("На доработку", comment)}
        >
          На доработку
        </button>
        <button
          className="primary-button"
          disabled={busy || (!demo && !detail?.actions.can_accept)}
          onClick={() => onDecide("Принято", comment)}
        >
          <Icon name="check" size={17} />
          Принять работу
        </button>
      </div>
    </Modal>
  );
}
