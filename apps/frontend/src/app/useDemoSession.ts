import { createContext, useContext, useEffect, useRef, useState } from "react";
import { initialStudents } from "../data/mockData";
import { useToast } from "../hooks/useToast";
import type { SettingsTab, SubmissionStatus } from "../types";

// One session survives route unmounts. Nothing is persisted or sent to a server.
export function useSessionState() {
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
  const [uploaded, setUploaded] = useState<File | null>(null);
  const [submitted, setSubmitted] = useState(false);
  const [checking, setChecking] = useState(false);
  const [help, setHelp] = useState(false);
  const notifications = useToast();
  const timer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  useEffect(() => () => clearTimeout(timer.current), []);
  const startCheck = () => {
    if (!uploaded || checking) return;
    setChecking(true);
    timer.current = setTimeout(() => {
      setChecking(false);
      setSubmitted(true);
    }, 1600);
  };
  return {
    students,
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
