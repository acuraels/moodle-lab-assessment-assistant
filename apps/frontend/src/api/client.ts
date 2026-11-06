const baseURL = (import.meta.env.VITE_API_BASE_URL || "/api").replace(
  /\/$/,
  "",
);
const messages: Record<number, string> = {
  400: "Проверьте данные запроса.",
  401: "Сессия истекла или токен недействителен. Войдите снова.",
  403: "Недостаточно прав для этого действия.",
  404: "Запрошенные данные не найдены.",
  409: "Действие недоступно в текущем состоянии работы.",
  413: "Файл слишком большой. Допустимо до 20 МБ.",
  415: "Сервер не поддерживает формат или содержимое файла.",
  422: "Проверьте заполненные поля и формат файла.",
  500: "Не удалось выполнить запрос на сервере.",
  501: "Эта возможность пока не подключена.",
  502: "Сервер временно недоступен.",
  503: "Сервер временно недоступен.",
  504: "Сервер не ответил вовремя.",
};
const codes: Record<string, string> = {
  AI_SETTINGS_NOT_CONFIGURED:
    "Преподаватель ещё не настроил материалы проверки.",
  ATTEMPT_LIMIT_REACHED: "Достигнут лимит попыток для этой лабораторной.",
  INVALID_ATTEMPT_STATUS:
    "Статус работы изменился или действие недоступно. Обновите данные.",
  COMMENT_REQUIRED: "Для возврата на доработку нужен комментарий.",
  ATTEMPT_NOT_FOUND: "Работа не найдена или недоступна в этой сессии.",
  LAB_NOT_FOUND: "Лабораторная не найдена в текущей сессии.",
  INVALID_GROUP: "Группа больше недоступна. Выберите «Все группы».",
  SETTINGS_CHANGED:
    "Настройки изменились на сервере. Перезагрузите страницу перед редактированием; ваш черновик пока сохранён в форме.",
  SETTINGS_EMPTY: "Заполните материалы проверки.",
};
export class ApiError extends Error {
  constructor(
    public status: number,
    public code = "",
    public requestId: string | null = null,
  ) {
    super(
      codes[code] ||
        messages[status] ||
        "Не удалось связаться с сервером. Проверьте подключение.",
    );
    this.name = "ApiError";
  }
}
export function errorMessage(error: unknown) {
  return error instanceof ApiError
    ? error.message
    : "Не удалось выполнить действие. Попробуйте ещё раз.";
}
export function isAbort(error: unknown) {
  return error instanceof DOMException && error.name === "AbortError";
}
export class ApiClient {
  constructor(
    private token: string,
    private unauthorized: () => void,
  ) {}
  async request<T>(
    path: string,
    options: RequestInit = {},
    format: "json" | "blob" = "json",
  ): Promise<T> {
    const controller = new AbortController();
    const abort = () => controller.abort();
    options.signal?.addEventListener("abort", abort, { once: true });
    if (options.signal?.aborted) controller.abort();
    const timer = setTimeout(abort, 30000);
    const headers = new Headers(options.headers);
    headers.set("Authorization", `Bearer ${this.token}`);
    if (options.body && !(options.body instanceof FormData))
      headers.set("Content-Type", "application/json");
    try {
      const response = await fetch(`${baseURL}${path}`, {
        ...options,
        headers,
        signal: controller.signal,
        credentials: "omit",
        cache: "no-store",
        referrerPolicy: "no-referrer",
      });
      if (!response.ok) {
        const body = await response.json().catch(() => null);
        const code =
          typeof body?.error?.code === "string" ? body.error.code : "";
        if (response.status === 401 && !controller.signal.aborted)
          this.unauthorized();
        // Only safe metadata is retained; never log tokens, request bodies or server tracebacks.
        throw new ApiError(
          response.status,
          code,
          response.headers.get("x-request-id"),
        );
      }
      if (response.status === 204) return undefined as T;
      return (
        format === "blob" ? await response.blob() : await response.json()
      ) as T;
    } catch (error) {
      if (options.signal?.aborted)
        throw new DOMException("Cancelled", "AbortError");
      if (error instanceof ApiError) throw error;
      throw new ApiError(controller.signal.aborted ? 504 : 0);
    } finally {
      clearTimeout(timer);
      options.signal?.removeEventListener("abort", abort);
    }
  }
}
