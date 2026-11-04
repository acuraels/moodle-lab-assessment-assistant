import { useDemoSession } from "../../app/useDemoSession";
import { Icon } from "../../components/ui/Icon";
import { settingsTabs, settingsPlaceholders } from "../../data/mockData";
import { isSupportedFile, openFilePicker } from "../../utils/files";
import { useState } from "react";
import { useRuntime } from "../../app/runtime";
import { useOperation } from "../../hooks/useOperation";
import {
  deleteMaterial,
  saveMaterials,
  uploadMaterial,
} from "../../api/endpoints";
import type { MaterialField, Materials } from "../../api/types";
import { RequestState } from "../../components/ui/RequestState";
import { Modal } from "../../components/ui/Modal";
import type { SettingsTab } from "../../types";
const fields: Record<SettingsTab, MaterialField> = {
  Методичка: "methodical_guide",
  "Критерии оценки": "grading_criteria",
  "Системные инструкции": "system_instructions",
  "Эталонная работа": "reference_work",
};
export function SettingsPanel() {
  const { mode, api, labId } = useRuntime();
  const demo = mode === "demo";
  const operation = useOperation();
  const [confirm, setConfirm] = useState<"save" | "delete" | null>(null);
  const [savedVersion, setSavedVersion] = useState<number | null>(null);
  const {
    settingsTab,
    setSettingsTab,
    instructions,
    setInstructions,
    settingsFiles,
    setSettingsFiles,
    toast,
    materialIds,
    setMaterialIds,
  } = useDemoSession();
  const complete = settingsTabs.every(
    (tab) => materialIds[tab] || instructions[tab]?.trim(),
  );
  const clearDraftFile = () => {
    setMaterialIds((values) => ({ ...values, [settingsTab]: undefined }));
    setSettingsFiles((values) => ({ ...values, [settingsTab]: undefined }));
  };
  const chooseFile = (file?: File) => {
    if (!file || operation.busy) return;
    if (!isSupportedFile(file, true)) {
      toast("Выберите файл PDF, DOCX или TXT");
      return;
    }
    if (demo)
      setSettingsFiles((files) => ({ ...files, [settingsTab]: file.name }));
    else {
      if (file.size > 20 * 1024 * 1024) {
        toast("Файл слишком большой. Допустимо до 20 МБ.");
        return;
      }
      const tab = settingsTab;
      void operation.run(
        (signal) => uploadMaterial(api!, labId, fields[tab], file, signal),
        (uploaded) => {
          setSettingsFiles((values) => ({ ...values, [tab]: uploaded.name }));
          setMaterialIds((values) => ({ ...values, [tab]: uploaded.file_id }));
          setInstructions((values) => ({ ...values, [tab]: "" }));
          toast(
            "Файл загружен. Он будет применён только после сохранения полного набора материалов.",
          );
        },
      );
    }
  };
  const apply = () => {
    if (confirm === "delete")
      void operation.run(
        (signal) => deleteMaterial(api!, labId, fields[settingsTab], signal),
        () => {
          clearDraftFile();
          setInstructions((values) => ({ ...values, [settingsTab]: "" }));
          setConfirm(null);
          toast(
            "Материал удалён из серверных настроек. Остальные материалы сохранены.",
          );
        },
      );
    else if (complete) {
      const materials = Object.fromEntries(
        settingsTabs.map((tab) => [
          fields[tab],
          materialIds[tab]
            ? { file_id: materialIds[tab] }
            : { text: instructions[tab]!.trim() },
        ]),
      ) as Materials;
      void operation.run(
        (signal) => saveMaterials(api!, labId, materials, signal),
        (response) => {
          setSavedVersion(response.version);
          setConfirm(null);
          toast(
            `Полный набор материалов сохранён. Версия ${response.version}.`,
          );
        },
      );
    }
  };
  return (
    <section className="settings-panel work-panel">
      <div className="section-intro">
        <span className="lab-icon">
          <Icon name="spark" size={24} />
        </span>
        <div>
          <h2>На что ориентироваться ассистенту?</h2>
          <p>
            {demo
              ? "Заполните хотя бы одно поле, чтобы сохранить настройки демо."
              : "Чтение сохранённых материалов пока недоступно в API."}
          </p>
        </div>
      </div>
      <div className="settings-tabs">
        {settingsTabs.map((t, i) => (
          <button
            key={t}
            disabled={operation.busy}
            className={settingsTab === t ? "selected" : ""}
            onClick={() => setSettingsTab(t)}
          >
            <span>0{i + 1}</span>
            {t}
            {(instructions[t]?.trim() || settingsFiles[t]) && (
              <Icon name="check" size={15} />
            )}
          </button>
        ))}
      </div>
      <h3>{settingsTab}</h3>
      <p className="muted">
        {demo
          ? "Добавьте текст или документ. В демо они не влияют на тестовый результат."
          : "Черновик нового набора: текст или файл для каждого материала. Текущие настройки сервера здесь не показаны."}
      </p>
      <label
        className="upload-zone"
        tabIndex={operation.busy ? -1 : 0}
        onKeyDown={openFilePicker}
        onDragOver={(e) => e.preventDefault()}
        onDrop={(e) => {
          e.preventDefault();
          chooseFile(e.dataTransfer.files[0]);
        }}
      >
        <Icon name="upload" size={29} />
        <strong>
          {settingsFiles[settingsTab] || "Нажмите, чтобы загрузить документ"}
        </strong>
        <span>PDF, DOCX или TXT</span>
        <input
          type="file"
          accept=".pdf,.docx,.txt"
          disabled={operation.busy}
          onChange={(e) => {
            chooseFile(e.target.files?.[0]);
            e.target.value = "";
          }}
        />
      </label>
      {!demo && materialIds[settingsTab] && (
        <div className="integration-actions">
          <button
            className="text-button"
            disabled={operation.busy}
            onClick={clearDraftFile}
          >
            Убрать файл из черновика
          </button>
        </div>
      )}
      <div className="or-divider">
        <span />
        или добавьте текст
        <span />
      </div>
      <textarea
        rows={6}
        aria-label={settingsTab}
        placeholder={settingsPlaceholders[settingsTab]}
        value={instructions[settingsTab] || ""}
        disabled={operation.busy || (!demo && !!materialIds[settingsTab])}
        onChange={(e) =>
          setInstructions({ ...instructions, [settingsTab]: e.target.value })
        }
      />
      {!demo && (
        <div className="ai-result integration-note">
          <p>
            Без чтения настроек нельзя безопасно сохранить одну вкладку. Для
            замены заполните все четыре материала и подтвердите полный набор.
            Остальные серверные материалы не изменяются при загрузке файла.
          </p>
          {savedVersion !== null && (
            <p>
              В этой сессии сервер подтвердил сохранение версии {savedVersion}.
              Отображается ваш черновик, не повторное чтение сервера.
            </p>
          )}
          <button
            className="text-button"
            disabled={operation.busy}
            onClick={() => setConfirm("delete")}
          >
            Удалить «{settingsTab}» на сервере
          </button>
        </div>
      )}
      {!confirm && <RequestState error={operation.error} />}
      <div className="settings-footer">
        <span>
          <Icon name="shield" size={16} />{" "}
          {demo
            ? "Демонстрационный режим преподавателя"
            : "Настройки преподавателя · API"}
        </span>
        <button
          className="primary-button"
          disabled={operation.busy || (!demo && !complete)}
          onClick={() =>
            !demo
              ? setConfirm("save")
              : Object.values(instructions).some((v) => v?.trim()) ||
                  Object.keys(settingsFiles).length
                ? toast(
                    "Настройки сохранены до перезагрузки страницы. Проверка использует тестовые данные.",
                  )
                : toast("Заполните хотя бы одно поле или загрузите файл")
          }
        >
          Сохранить настройки
          <Icon name="check" size={17} />
        </button>
      </div>
      {confirm && (
        <Modal
          titleId="settings-confirm"
          onClose={() => {
            if (!operation.busy) setConfirm(null);
          }}
        >
          <button
            className="close-modal"
            aria-label="Закрыть"
            disabled={operation.busy}
            onClick={() => setConfirm(null)}
          >
            ×
          </button>
          <h2 id="settings-confirm">
            {confirm === "save"
              ? "Заменить все материалы?"
              : `Удалить «${settingsTab}»?`}
          </h2>
          <p>
            {confirm === "save"
              ? "Все четыре материала на сервере будут заменены этим набором. Текущие значения сервер не позволяет прочитать."
              : "Будет удалён только этот материал из серверных настроек. Отменить удаление через API нельзя."}
          </p>
          {confirm === "save" && (
            <ul>
              {settingsTabs.map((tab) => (
                <li key={tab}>
                  {tab}:{" "}
                  {materialIds[tab]
                    ? settingsFiles[tab]
                    : `текст, ${instructions[tab]?.trim().length || 0} символов`}
                </li>
              ))}
            </ul>
          )}
          <RequestState error={operation.error} />
          <div className="modal-actions">
            <button
              className="secondary-button"
              disabled={operation.busy}
              onClick={() => setConfirm(null)}
            >
              Отмена
            </button>
            <button
              className="primary-button"
              disabled={operation.busy}
              onClick={apply}
            >
              {operation.busy
                ? "Сохраняем…"
                : confirm === "save"
                  ? "Заменить полный набор"
                  : "Удалить материал"}
            </button>
          </div>
        </Modal>
      )}
    </section>
  );
}
