export type Role = "instructor" | "student";
export type AttemptStatus =
  | "processing"
  | "ai_checked"
  | "accepted"
  | "returned_for_revision"
  | "ai_failed";
export interface Profile {
  id: string;
  name: string;
  email: string;
  role: Role;
  course_id: string;
  Academic_group: string | null;
}
export interface Lab {
  id: string;
  course_id?: string;
  title: string;
  description: string | null;
  deadline: string | null;
  attempts_limit: number | null;
}
export interface Pagination {
  page: number;
  page_size: number;
  total_items: number;
  total_pages: number;
}
export interface Page<T> {
  items: T[];
  pagination: Pagination;
}
export interface FileInfo {
  id: string;
  name: string;
  size?: number;
  download_url?: string;
}
export interface Attempt {
  id: string;
  number: number;
  submitted_at: string;
  status: AttemptStatus;
  ai_score: number | null;
  ai_conclusion: string | null;
  teacher_comment: string | null;
  file: FileInfo | null;
}
export interface Criterion {
  name?: string;
  score?: number | null;
  max_score?: number | null;
  comment?: string;
}
export interface AIResult {
  attempt_id: string;
  status: AttemptStatus;
  score: number | null;
  max_score: number | null;
  conclusion: string | null;
  criteria: Criterion[];
  settings_version: number | null;
  checked_at: string | null;
}
export interface Student {
  id: string;
  name: string;
  Academic_group: string | null;
}
export interface SubmissionRow {
  attempt_id: string;
  student: Student;
  submitted_at: string;
  ai_score: number | null;
  status: AttemptStatus;
}
export interface SubmissionDetail {
  id: string;
  lab: Pick<Lab, "id" | "title" | "deadline" | "attempts_limit">;
  student: Student;
  files: FileInfo[];
  submitted_at: string;
  status: AttemptStatus;
  ai_score: number | null;
  ai_max_score: number | null;
  ai_conclusion: string | null;
  teacher_comment: string | null;
  actions: { can_accept: boolean; can_return_for_revision: boolean };
}
export interface Statistics {
  total_submitted: number;
  submitted_today: number;
  ai_checked: number;
  accepted: number;
  returned_for_revision: number;
  processing: number;
}
export type Decision = "accept" | "return_for_revision";
export type MaterialField =
  | "methodical_guide"
  | "grading_criteria"
  | "system_instructions"
  | "reference_work";
export type Material =
  { text: string; file_id?: never } | { file_id: string; text?: never };
export type Materials = Record<MaterialField, Material | null>;
export interface MaterialFile {
  file_id: string;
  field: MaterialField;
  name: string;
  size: number;
  content_type: string;
}
