import { useLocation, useNavigate, useParams } from "react-router";
import { useDemoSession } from "../../app/useDemoSession";
import { SubmissionModal } from "./SubmissionModal";
import { Modal } from "../../components/ui/Modal";
import type { SubmissionStatus } from "../../types";

export function SubmissionRoute() {
  const { id } = useParams();
  const { students, setStudents, toast } = useDemoSession();
  const location = useLocation();
  const navigate = useNavigate();
  const submission = students.find((item) => item.id === id);
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
        <h2 id="missing-submission">Работа не найдена</h2>
        <p>В демонстрационных данных нет работы с таким ID.</p>
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
    />
  );
}
