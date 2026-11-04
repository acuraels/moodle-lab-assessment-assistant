export type SubmissionStatus =
  | "Проверено ИИ"
  | "Принято"
  | "На доработку"
  | "В обработке"
  | "Ошибка проверки";
export type Submission = {
  id: string;
  name: string;
  initials: string;
  group: string;
  date: string;
  files: number | null;
  score: number | null;
  maxScore?: number | null;
  status: SubmissionStatus;
  color: string;
  comment?: string;
};
export type AssessmentCriterion = {
  title: string;
  max: number;
  good: string;
  improve: string;
};
export type SettingsTab =
  "Методичка" | "Критерии оценки" | "Системные инструкции" | "Эталонная работа";
export type Notify = (message: string) => void;
