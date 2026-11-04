import type { AttemptStatus, SubmissionDetail, SubmissionRow } from "./types";
import type { Submission, SubmissionStatus } from "../types";
export const statusLabels: Record<AttemptStatus, SubmissionStatus> = {
  processing: "В обработке",
  ai_checked: "Проверено ИИ",
  accepted: "Принято",
  returned_for_revision: "На доработку",
  ai_failed: "Ошибка проверки",
};
export const formatDate = (value: string | null) =>
  value
    ? new Date(value).toLocaleString("ru-RU", {
        dateStyle: "short",
        timeStyle: "short",
      })
    : "Не указан";
export const initials = (name: string) =>
  name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0])
    .join("");
export function rowToSubmission(row: SubmissionRow): Submission {
  return {
    id: row.attempt_id,
    name: row.student.name,
    initials: initials(row.student.name),
    group: row.student.Academic_group || "Группа не указана",
    date: formatDate(row.submitted_at),
    files: null,
    score: row.ai_score,
    maxScore: null,
    status: statusLabels[row.status] || "Ошибка проверки",
    color: "blue",
  };
}
export function detailToSubmission(row: SubmissionDetail): Submission {
  return {
    ...rowToSubmission({ ...row, attempt_id: row.id }),
    files: row.files.length,
    maxScore: row.ai_max_score,
    comment: row.teacher_comment || "",
  };
}
