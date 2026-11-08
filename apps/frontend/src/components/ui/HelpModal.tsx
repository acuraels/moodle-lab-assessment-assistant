import { Icon } from "./Icon";
import { Modal } from "./Modal";
import { useRuntime } from "../../app/runtime";
export function HelpModal({ onClose }: { onClose: () => void }) {
  const { mode } = useRuntime();
  return (
    <Modal titleId="help-title" onClose={onClose}>
      <button
        className="close-modal"
        aria-label="Закрыть"
        onClick={() => onClose()}
      >
        ×
      </button>
      <span className="lab-icon">
        <Icon name="spark" />
      </span>
      <h2 id="help-title">Как пользоваться ассистентом</h2>
      <p>
        1. Преподаватель: настройте критерии проверки и просматривайте
        результаты лабораторных работ.
      </p>
      <p>
        {mode === "demo"
          ? "2. Студент: переключитесь в режим студента, загрузите PDF или DOCX и запустите проверку."
          : "2. Студент: загрузите PDF или DOCX в своей сессии и выберите попытку в истории."}
      </p>
      <p>
        3. Результат: изучите чек-лист, замечания и рекомендации по доработке
        работы.
      </p>
      <div className="ai-result">
        <Icon name="shield" />
        <p>
          {mode === "demo"
            ? "Сейчас это демонстрационный прототип. Загруженные файлы не анализируются: оценки и замечания формируются из тестовых данных. Moodle, серверная обработка и локальная LLM пока не подключены."
            : "Файлы и решения сохраняются на сервере. Проверка выполняется в фоне; её результат доступен в истории попыток. При сбое будет показана причина, если она доступна. Без заданной шкалы ИИ может дать замечания без числовой оценки. Окончательное решение принимает преподаватель. Публикация оценок в Moodle не подключена."}
        </p>
      </div>
      <button className="primary-button" onClick={() => onClose()}>
        Понятно
      </button>
    </Modal>
  );
}
