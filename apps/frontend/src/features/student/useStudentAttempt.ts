import { useCallback, useEffect, useState } from "react";
import { useRuntime } from "../../app/runtime";
import {
  createAttempt,
  getAttempt,
  getAttempts,
  getResult,
  submitAttempt,
} from "../../api/endpoints";
import { useResource } from "../../hooks/useResource";
import { useOperation } from "../../hooks/useOperation";
import { errorMessage } from "../../api/client";
import type { AIResult, Attempt } from "../../api/types";

export function useStudentAttempt(notify: (message: string) => void) {
  const { mode, api, labId } = useRuntime();
  const enabled = mode === "api";
  const [page, setPage] = useState(1);
  const [selection, setSelection] = useState<string | null | undefined>(
    undefined,
  );
  const [historyRevision, setHistoryRevision] = useState(0);
  const [pollRevision, setPollRevision] = useState(0);
  const [sent, setSent] = useState<string[]>([]);
  const [state, setState] = useState<{
    key: string;
    attempt?: Attempt;
    result?: AIResult;
    error?: string;
  }>({ key: "" });
  const operation = useOperation();
  const loadHistory = useCallback(
    async (signal: AbortSignal) => {
      const response = await getAttempts(api!, labId, page, signal);
      if (!signal.aborted)
        setSelection((current) =>
          current === undefined ? response.items[0]?.id || null : current,
        );
      return response;
    },
    [api, labId, page],
  );
  const history = useResource(
    loadHistory,
    enabled,
    `${labId}:${page}:${historyRevision}`,
  );
  const key = `${selection}:${pollRevision}`;
  useEffect(() => {
    if (!enabled || !api || !selection) return;
    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout> | undefined;
    const deadline = Date.now() + 120000;
    async function poll() {
      try {
        const [attempt, result] = await Promise.all([
          getAttempt(api!, selection!, controller.signal),
          getResult(api!, selection!, controller.signal),
        ]);
        if (controller.signal.aborted) return;
        const current = { ...attempt, status: result.status };
        if (result.status === "processing" && Date.now() >= deadline) {
          setState({
            key,
            attempt: current,
            result,
            error:
              "Ожидание проверки завершено. Работа сохранена. Обновите статус позднее.",
          });
          return;
        }
        setState({ key, attempt: current, result });
        if (result.status === "processing")
          timer = setTimeout(() => void poll(), 3000);
        else setHistoryRevision((value) => value + 1);
      } catch (error) {
        if (!controller.signal.aborted)
          setState((previous) => ({
            ...(previous.key === key ? previous : {}),
            key,
            error: errorMessage(error),
          }));
      }
    }
    void poll();
    return () => {
      controller.abort();
      clearTimeout(timer);
    };
  }, [api, enabled, selection, key]);
  const current = state.key === key ? state : undefined;
  const upload = (file: File) => {
    if (!api) return;
    void operation.run(
      (signal) => createAttempt(api, labId, file, signal),
      (attempt) => {
        setSelection(attempt.id);
        setPage(1);
        setHistoryRevision((value) => value + 1);
        setState({ key: `${attempt.id}:${pollRevision}`, attempt });
        notify(
          "Работа сохранена на сервере. Ожидаем состояние автоматической проверки.",
        );
      },
    );
  };
  const submit = () => {
    if (
      !api ||
      !selection ||
      !current?.attempt ||
      !["ai_checked", "returned_for_revision"].includes(current.attempt.status)
    )
      return;
    void operation.run(
      (signal) => submitAttempt(api, selection, signal),
      () => {
        setSent((ids) => [...ids, selection]);
        notify("Сервер подтвердил отправку преподавателю.");
        setHistoryRevision((value) => value + 1);
      },
    );
  };
  return {
    history,
    page,
    changePage: (next: number) => {
      setSelection(undefined);
      setPage(next);
    },
    selection,
    select: (id: string) => setSelection(id),
    newAttempt: () => setSelection(null),
    upload,
    submit,
    operation,
    attempt: current?.attempt,
    result: current?.result,
    error: current?.error,
    loading: enabled && !!selection && !current?.attempt && !current?.error,
    retry: () => setPollRevision((value) => value + 1),
    sent: !!selection && sent.includes(selection),
  };
}
