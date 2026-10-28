import { Icon } from "./Icon";
import { Modal } from "./Modal";
export function HelpModal({ onClose }: { onClose: () => void }) {
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
        2. Студент: переключитесь в режим студента, загрузите PDF или DOCX и
        запустите проверку.
      </p>
      <p>
        3. Результат: изучите чек-лист, замечания и рекомендации по доработке
        работы.
      </p>
      <div className="ai-result">
        <Icon name="shield" />
        <p>
          Сейчас это демонстрационный прототип. Загруженные файлы не
          анализируются: оценки и замечания формируются из тестовых данных.
          Moodle, серверная обработка и локальная LLM пока не подключены.
        </p>
      </div>
      <button className="primary-button" onClick={() => onClose()}>
        Понятно
      </button>
    </Modal>
  );
}
