import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
} from "react";
import { initialStudents, lab as demoLab } from "../data/mockData";
import { useRuntime } from "./runtime";
import { useResource } from "../hooks/useResource";
import {
  getGroups,
  getLab,
  getStatistics,
  getSubmissions,
} from "../api/endpoints";
import { formatDate, rowToSubmission } from "../api/format";
import { useLocation } from "react-router";
import { useToast } from "../hooks/useToast";
import type { SettingsTab, SubmissionStatus } from "../types";

// One session survives route unmounts. Nothing is persisted or sent to a server.
export function useSessionState() {
  const { mode, api, user, labId, labTitle, revision } = useRuntime();
  const { pathname } = useLocation();
  const [students, setStudents] = useState(initialStudents);
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState<"Все работы" | SubmissionStatus>(
    "Все работы",
  );
  const [group, setGroup] = useState("Все группы");
  const [checkedIds, setCheckedIds] = useState<string[]>([]);
  const [currentPage, setCurrentPage] = useState(1);
  const [sortAscending, setSortAscending] = useState<boolean | null>(null);
  const [settingsTab, setSettingsTab] = useState<SettingsTab>("Методичка");
  const [instructions, setInstructions] = useState<
    Partial<Record<SettingsTab, string>>
  >({});
  const [settingsFiles, setSettingsFiles] = useState<
    Partial<Record<SettingsTab, string>>
  >({});
  const [materialIds, setMaterialIds] = useState<
    Partial<Record<SettingsTab, string>>
  >({});
  const [uploaded, setUploaded] = useState<File | null>(null);
  const [submitted, setSubmitted] = useState(false);
  const [checking, setChecking] = useState(false);
  const [help, setHelp] = useState(false);
  const notifications = useToast();
  const timer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  useEffect(() => () => clearTimeout(timer.current), []);
  const startCheck = () => {
    if (mode !== "demo") return;
    if (!uploaded || checking) return;
    setChecking(true);
    timer.current = setTimeout(() => {
      setChecking(false);
      setSubmitted(true);
    }, 1600);
  };
  const loadLab = useCallback(
    (signal: AbortSignal) => getLab(api!, labId, signal),
    [api, labId],
  );
  const labResource = useResource(
    loadLab,
    mode === "api" && user?.role === "instructor",
    `${labId}:${revision}`,
  );
  const loadTeacher = useCallback(
    async (signal: AbortSignal) => {
      const status =
        filter === "Проверено ИИ"
          ? "ai_checked"
          : filter === "На доработку"
            ? "returned_for_revision"
            : "all";
      const params = new URLSearchParams({
        page: String(currentPage),
        page_size: "7",
        status,
      });
      if (query.trim()) params.set("student_name", query.trim());
      if (group !== "Все группы") params.set("Academic_group", group);
      const [list, stats, groups] = await Promise.all([
        getSubmissions(api!, labId, params, signal),
        getStatistics(api!, labId, signal),
        getGroups(api!, labId, signal),
      ]);
      return {
        list,
        stats: stats.statistics,
        groups: groups.items.map((item) => item.Academic_group),
      };
    },
    [api, labId, filter, currentPage, query, group],
  );
  const teacher = useResource(
    loadTeacher,
    mode === "api" && user?.role === "instructor",
    JSON.stringify([
      labId,
      revision,
      filter,
      currentPage,
      query,
      group,
      pathname,
    ]),
  );
  const lab =
    mode === "demo"
      ? demoLab
      : {
          name: labResource.data?.title || labTitle,
          description: labResource.data?.description || "Описание недоступно",
          subject: user?.course_id
            ? `Курс ${user.course_id}`
            : "Курс не указан",
          deadline: labResource.data
            ? formatDate(labResource.data.deadline)
            : "Нет данных",
        };
  return {
    students:
      mode === "demo"
        ? students
        : teacher.data?.list.items.map(rowToSubmission) || [],
    lab,
    labResource,
    teacher,
    materialIds,
    setMaterialIds,
    setStudents,
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
    settingsTab,
    setSettingsTab,
    instructions,
    setInstructions,
    settingsFiles,
    setSettingsFiles,
    uploaded,
    setUploaded,
    submitted,
    setSubmitted,
    checking,
    startCheck,
    help,
    setHelp,
    ...notifications,
  };
}

export const DemoSessionContext = createContext<ReturnType<
  typeof useSessionState
> | null>(null);

export function useDemoSession() {
  const session = useContext(DemoSessionContext);
  if (!session) throw new Error("DemoSessionContext is missing");
  return session;
}
