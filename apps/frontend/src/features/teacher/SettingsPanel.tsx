import { useDemoSession } from "../../app/useDemoSession";
import { Icon } from "../../components/ui/Icon";
import { settingsTabs, settingsPlaceholders } from "../../data/mockData";
import { isSupportedFile, openFilePicker } from "../../utils/files";
import { useCallback, useState } from "react";
import { useResource } from "../../hooks/useResource";
import { ApiError } from "../../api/client";
import { useRuntime } from "../../app/runtime";
import { useOperation } from "../../hooks/useOperation";
import {
  deleteMaterial,
  downloadFile,
  getMaterials,
  saveMaterials,
  uploadMaterial,
} from "../../api/endpoints";
import type { AISettings, MaterialField, Materials } from "../../api/types";
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
  const load = useCallback(
    (signal: AbortSignal) => getMaterials(api!, labId, signal),
    [api, labId],
  );
  const resource = useResource(load, mode === "api", labId);
  if (mode === "api" && !resource.data)
    return (
      <section className="settings-panel work-panel">
        <RequestState
          loading={resource.loading}
          error={resource.error}
          retry={resource.retry}
        />
      </section>
    );
  return <SettingsEditor key={`${mode}:${labId}`} initial={resource.data} />;
}

function settingsDraft(initial?: AISettings) {
  const text: Partial<Record<SettingsTab, string>> = {};
  const files: Partial<Record<SettingsTab, string>> = {};
  const ids: Partial<Record<SettingsTab, string>> = {};
  for (const tab of settingsTabs) {
    const material = initial?.[fields[tab]];
    text[tab] = material?.text ?? "";
    files[tab] = material?.file?.name;
    ids[tab] = material?.file?.file_id;
  }
  return { text, files, ids };
}

function SettingsEditor({ initial }: { initial?: AISettings }) {
  const { mode, api, labId } = useRuntime();
  const demo = mode === "demo";
  const operation = useOperation();
  const [confirm, setConfirm] = useState<"save" | "delete" | null>(null);
  const [savedVersion, setSavedVersion] = useState(initial?.version ?? 0);
  const [apiInstructions, setApiInstructions] = useState(
    () => settingsDraft(initial).text,
  );
  const [apiFiles, setApiFiles] = useState(() => settingsDraft(initial).files);
  const [apiIds, setApiIds] = useState(() => settingsDraft(initial).ids);
  const session = useDemoSession();
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
  } = demo
    ? session
    : {
        ...session,
        instructions: apiInstructions,
        setInstructions: setApiInstructions,
        settingsFiles: apiFiles,
        setSettingsFiles: setApiFiles,
        materialIds: apiIds,
        setMaterialIds: setApiIds,
      };
  const complete = settingsTabs.some(
    (tab) => materialIds[tab] || instructions[tab]?.trim(),
  );
  const checkVersion = async (signal: AbortSignal) => {
    const latest = await getMaterials(api!, labId, signal);
    if (latest.version !== savedVersion)
      throw new ApiError(409, "SETTINGS_CHANGED");
  };
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
        async (signal) => {
          await checkVersion(signal);
          await deleteMaterial(api!, labId, fields[settingsTab], signal);
          return getMaterials(api!, labId, signal);
        },
        (response) => {
          setSavedVersion(response.version);
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
            : instructions[tab]?.trim()
              ? { text: instructions[tab]! }
              : null,
        ]),
      ) as Materials;
      void operation.run(
        async (signal) => {
          await checkVersion(signal);
          return saveMaterials(api!, labId, materials, signal);
        },
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
              : "Сохранённые материалы загружены. Можно изменить любую вкладку."}
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
          : "Добавьте текст или замените документ. Изменения применятся после сохранения."}
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
            onClick={() =>
              void operation.run(
                (signal) =>
                  downloadFile(
                    api!,
                    materialIds[settingsTab]!,
                    settingsFiles[settingsTab]!,
                    signal,
                  ),
                () => toast("Файл получен. Скачивание начато."),
              )
            }
          >
            Скачать материал
          </button>
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
            Сохраняется весь набор: изменённые вкладки вместе с остальными
            загруженными материалами. Пустая вкладка удаляет соответствующий
            материал при сохранении. Хотя бы один материал должен остаться.
          </p>
          {savedVersion !== null && (
            <p>
              Версия на момент загрузки или последнего сохранения:{" "}
              {savedVersion}. Несохранённые изменения находятся только в этой
              форме.
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
              ? "Сохранить настройки?"
              : `Удалить «${settingsTab}»?`}
          </h2>
          <p>
            {confirm === "save"
              ? "Будет сохранён показанный набор. Неизменённые вкладки сохранят загруженные значения."
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
                  ? "Подтвердить сохранение"
                  : "Удалить материал"}
            </button>
          </div>
        </Modal>
      )}
    </section>
  );
}
