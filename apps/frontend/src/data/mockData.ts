import type {
  AssessmentCriterion,
  SettingsTab,
  Submission,
  SubmissionStatus,
} from "../types";
export const initialStudents: Submission[] = [
  {
    id: "submission-1",
    name: "Александров Иван",
    initials: "ИА",
    group: "ИВТ-221",
    date: "Сегодня, 10:42",
    files: 2,
    score: 92,
    status: "Проверено ИИ",
    color: "blue",
  },
  {
    id: "submission-2",
    name: "Смирнова Анна",
    initials: "АС",
    group: "ИВТ-221",
    date: "Сегодня, 10:18",
    files: 1,
    score: 98,
    status: "Принято",
    color: "purple",
  },
  {
    id: "submission-3",
    name: "Козлов Дмитрий",
    initials: "ДК",
    group: "ИВТ-222",
    date: "Сегодня, 09:56",
    files: 3,
    score: 64,
    status: "На доработку",
    color: "orange",
  },
  {
    id: "submission-4",
    name: "Морозова Мария",
    initials: "ММ",
    group: "ИВТ-221",
    date: "Сегодня, 09:34",
    files: 2,
    score: 87,
    status: "Проверено ИИ",
    color: "pink",
  },
  {
    id: "submission-5",
    name: "Волков Артём",
    initials: "АВ",
    group: "ИВТ-222",
    date: "Сегодня, 09:12",
    files: 1,
    score: null,
    status: "В обработке",
    color: "teal",
  },
  {
    id: "submission-6",
    name: "Соколова Елена",
    initials: "ЕС",
    group: "ИВТ-221",
    date: "Вчера, 18:45",
    files: 2,
    score: 95,
    status: "Принято",
    color: "purple",
  },
  {
    id: "submission-7",
    name: "Попов Максим",
    initials: "МП",
    group: "ИВТ-222",
    date: "Вчера, 17:22",
    files: 2,
    score: 81,
    status: "Проверено ИИ",
    color: "blue",
  },
];
export const statusClass: Record<SubmissionStatus, string> = {
  "Проверено ИИ": "ai",
  Принято: "accepted",
  "На доработку": "revision",
  "В обработке": "processing",
};

export const assessmentCriteria: AssessmentCriterion[] = [
  {
    title: "Структура и оформление отчёта",
    max: 20,
    good: "Основные разделы присутствуют, отчёт оформлен последовательно.",
    improve: "Проверьте полноту разделов и оформление таблиц и иллюстраций.",
  },
  {
    title: "Описание алгоритма",
    max: 25,
    good: "Шаги алгоритма описаны и соответствуют реализации.",
    improve:
      "Дополните описание шагов алгоритма и обоснуйте выбор метода сортировки.",
  },
  {
    title: "Корректность реализации",
    max: 35,
    good: "Реализация решает поставленную задачу, результаты корректны.",
    improve:
      "Добавьте проверку граничных случаев и примеры для разных входных данных.",
  },
  {
    title: "Анализ результатов и выводы",
    max: 20,
    good: "Выводы связаны с результатами и целью работы.",
    improve:
      "Дополните выводы: сравните результаты сортировки и оцените эффективность алгоритма.",
  },
];

export const lab = {
  name: "Лабораторная работа № 3",
  description: "Работа с массивами и сортировка данных",
  subject: "Программирование",
  deadline: "28 мая, 23:59",
};
export const settingsTabs: SettingsTab[] = [
  "Методичка",
  "Критерии оценки",
  "Системные инструкции",
  "Эталонная работа",
];
export const settingsPlaceholders: Record<SettingsTab, string> = {
  Методичка: "Введите текст методички…",
  "Критерии оценки": "Перечислите критерии оценки…",
  "Системные инструкции": "Введите инструкции для ассистента…",
  "Эталонная работа": "Введите текст эталонной работы…",
};
export const demoResult = {
  score: 82,
  checklist: [
    { text: "Структура отчёта соответствует методичке", needsRevision: false },
    { text: "Описание алгоритма присутствует", needsRevision: false },
    { text: "Добавьте выводы к результатам сортировки", needsRevision: true },
  ],
};
