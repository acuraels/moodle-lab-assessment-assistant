import { useDemoSession } from "../../app/useDemoSession";
import { Icon } from "../../components/ui/Icon";
import { settingsTabs, settingsPlaceholders } from "../../data/mockData";
import { isSupportedFile, openFilePicker } from "../../utils/files";
export function SettingsPanel() {
  const {
    settingsTab,
    setSettingsTab,
    instructions,
    setInstructions,
    settingsFiles,
    setSettingsFiles,
    toast,
  } = useDemoSession();
  const chooseFile = (file?: File) => {
    if (!file) return;
    if (!isSupportedFile(file, true)) {
      toast("Выберите файл PDF, DOCX или TXT");
      return;
    }
    setSettingsFiles((files) => ({ ...files, [settingsTab]: file.name }));
  };
  return (
    <section className="settings-panel work-panel">
      <div className="section-intro">
        <span className="lab-icon">
          <Icon name="spark" size={24} />
        </span>
        <div>
          <h2>На что ориентироваться ассистенту?</h2>
          <p>Заполните хотя бы одно поле, чтобы сохранить настройки демо.</p>
        </div>
      </div>
      <div className="settings-tabs">
        {settingsTabs.map((t, i) => (
          <button
            key={t}
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
        Добавьте текст или документ. В демо они не влияют на тестовый результат.
      </p>
      <label
        className="upload-zone"
        tabIndex={0}
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
          onChange={(e) => {
            chooseFile(e.target.files?.[0]);
            e.target.value = "";
          }}
        />
      </label>
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
        onChange={(e) =>
          setInstructions({ ...instructions, [settingsTab]: e.target.value })
        }
      />
      <div className="settings-footer">
        <span>
          <Icon name="shield" size={16} /> Демонстрационный режим преподавателя
        </span>
        <button
          className="primary-button"
          onClick={() =>
            Object.values(instructions).some((v) => v.trim()) ||
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
    </section>
  );
}
