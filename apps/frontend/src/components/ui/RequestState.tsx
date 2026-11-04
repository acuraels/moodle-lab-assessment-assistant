export function RequestState({
  loading,
  error,
  retry,
}: {
  loading?: boolean;
  error?: string;
  retry?: () => void;
}) {
  if (loading)
    return (
      <div className="empty-state" role="status">
        Загружаем данные…
      </div>
    );
  if (error)
    return (
      <div className="empty-state" role="alert">
        <p>{error}</p>
        {retry && (
          <button className="secondary-button" onClick={retry}>
            Повторить
          </button>
        )}
      </div>
    );
  return null;
}
