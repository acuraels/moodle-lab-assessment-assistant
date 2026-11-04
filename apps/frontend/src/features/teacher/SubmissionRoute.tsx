import { useLocation, useNavigate, useParams } from "react-router";
import { useDemoSession } from "../../app/useDemoSession";
import { SubmissionModal } from "./SubmissionModal";
import { Modal } from "../../components/ui/Modal";
import type { SubmissionStatus } from "../../types";
import { useCallback } from "react";
import { useRuntime } from "../../app/runtime";
import { useResource } from "../../hooks/useResource";
import { useOperation } from "../../hooks/useOperation";
import { getResult, getSubmission, review } from "../../api/endpoints";
import { errorMessage, isAbort } from "../../api/client";
import { detailToSubmission } from "../../api/format";
import { RequestState } from "../../components/ui/RequestState";

export function SubmissionRoute() {
  const { id } = useParams();
  const { students, setStudents, toast } = useDemoSession();
  const { mode, api, refresh } = useRuntime();
  const operation = useOperation();
  const load = useCallback(
    async (signal: AbortSignal) => {
      const detail = await getSubmission(api!, id!, signal);
      try {
        return {
          detail,
          result: await getResult(api!, id!, signal),
          resultError: "",
        };
      } catch (error) {
        if (isAbort(error)) throw error;
        return { detail, result: undefined, resultError: errorMessage(error) };
      }
    },
    [api, id],
  );
  const resource = useResource(load, mode === "api" && !!id, id || "");
  const location = useLocation();
  const navigate = useNavigate();
  const submission =
    mode === "demo"
      ? students.find((item) => item.id === id)
      : resource.data
        ? detailToSubmission(resource.data.detail)
        : undefined;
  const historyState: unknown = location.state;
  const close = () => {
    // The ID always comes from the URL; history state only controls the return path.
    if (
      historyState &&
      typeof historyState === "object" &&
      "fromOverview" in historyState &&
      historyState.fromOverview === true
    )
      navigate(-1);
    else navigate("/teacher", { replace: true });
  };
  const decide = (status: SubmissionStatus, comment: string) => {
    if (!submission) return;
    if (mode === "api") {
      if (status === "На доработку" && !comment.trim()) {
        toast("Добавьте комментарий для возврата на доработку.");
        return;
      }
      void operation.run(
        (signal) =>
          review(
            api!,
            submission.id,
            status === "Принято" ? "accept" : "return_for_revision",
            comment,
            signal,
          ),
        () => {
          refresh();
          toast("Решение и комментарий сохранены на сервере.");
          close();
        },
      );
      return;
    }
    setStudents((items) =>
      items.map((item) =>
        item.id === id ? { ...item, status, comment } : item,
      ),
    );
    close();
    toast(
      "Демо: решение и комментарий сохранены до перезагрузки. Студенту ничего не отправлено.",
    );
  };
  if (!submission)
    return (
      <Modal titleId="missing-submission" onClose={close}>
        <button className="close-modal" aria-label="Закрыть" onClick={close}>
          ×
        </button>
        <h2 id="missing-submission">
          {mode === "api" ? "Карточка работы" : "Работа не найдена"}
        </h2>
        {mode === "api" ? (
          <RequestState
            loading={resource.loading}
            error={resource.error}
            retry={resource.retry}
          />
        ) : (
          <p>В демонстрационных данных нет работы с таким ID.</p>
        )}
        <button className="primary-button" onClick={close}>
          Вернуться к обзору
        </button>
      </Modal>
    );
  return (
    <SubmissionModal
      key={submission.id}
      submission={submission}
      onClose={close}
      onDecide={decide}
      toast={toast}
      detail={resource.data?.detail}
      result={resource.data?.result}
      resultError={resource.data?.resultError}
      busy={operation.busy}
      error={operation.error}
      retry={resource.retry}
    />
  );
}
