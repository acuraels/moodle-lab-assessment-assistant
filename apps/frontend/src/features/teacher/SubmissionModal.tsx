import { useState } from "react";
import { Icon } from "../../components/ui/Icon";
import { Modal } from "../../components/ui/Modal";
import { CriteriaAssessment } from "../../components/ui/CriteriaAssessment";
import { lab, statusClass } from "../../data/mockData";
import type { Notify, Submission, SubmissionStatus } from "../../types";
export function SubmissionModal({
  submission,
  onClose,
  onDecide,
  toast,
}: {
  submission: Submission;
  onClose: () => void;
  onDecide: (status: SubmissionStatus, comment: string) => void;
  toast: Notify;
}) {
  const [comment, setComment] = useState(submission.comment ?? "");
  const labName = lab.name;
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
      <div className="eyebrow">ПРИМЕР ПРОВЕРКИ</div>
      <h2 id="submission-title">{submission.name}</h2>
      <p>
        {submission.group} · {labName}
      </p>
      <span className={`status ${statusClass[submission.status]}`}>
        <span />
        {submission.status}
      </span>
      <div className="detail-files">
        <h3>Файлы студента (пример)</h3>
        {Array.from({ length: submission.files }, (_, i) => (
          <button
            key={i}
            onClick={() =>
              toast(
                "Файл из тестовых данных недоступен для скачивания. Сервер не подключён.",
              )
            }
          >
            <Icon name="file" />
            <span>
              {i === 0 ? "Отчёт по лабораторной.pdf" : `Приложение ${i}.docx`}
            </span>
            <Icon name="download" size={17} />
          </button>
        ))}
      </div>
      <div className="ai-result">
        <h3>
          <Icon name="spark" />
          Заключение ИИ (пример){" "}
          <span>
            {submission.score !== null
              ? `${submission.score} / 100`
              : "Нет оценки"}
          </span>
        </h3>
        <p>
          {submission.score === null
            ? "Пример работы без оценки. Серверная проверка пока не подключена."
            : submission.score < 70
              ? "Основные требования выполнены частично. Необходимо дополнить описание алгоритма и добавить выводы."
              : "Работа соответствует основным критериям. Структура отчёта и реализация алгоритма корректны. Рекомендуется проверить оформление выводов."}
        </p>
        <small>
          Тестовые данные, не анализ файла. Решение и комментарий сохраняются
          только до перезагрузки.
        </small>
      </div>
      <CriteriaAssessment score={submission.score} />
      <label className="comment-label">
        Комментарий преподавателя
        <textarea
          value={comment}
          onChange={(e) => setComment(e.target.value)}
          rows={3}
          placeholder="Добавьте обратную связь студенту…"
        />
      </label>
      <div className="modal-actions">
        <button
          className="secondary-button"
          onClick={() => onDecide("На доработку", comment)}
        >
          На доработку
        </button>
        <button
          className="primary-button"
          onClick={() => onDecide("Принято", comment)}
        >
          <Icon name="check" size={17} />
          Принять работу
        </button>
      </div>
    </Modal>
  );
}
