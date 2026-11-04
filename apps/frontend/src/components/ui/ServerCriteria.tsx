import type { AIResult } from "../../api/types";
export function ServerCriteria({ result }: { result?: AIResult }) {
  return (
    <section className="criteria-assessment" aria-labelledby="criteria-heading">
      <div className="criteria-heading">
        <h3 id="criteria-heading">Оценка по критериям</h3>
      </div>
      {!result?.criteria.length && (
        <p className="criteria-caption">
          Сервер не вернул оценку по критериям.
        </p>
      )}
      {result?.criteria.map((row, index) => (
        <div className="criterion-row" key={index}>
          <div className="criterion-title">
            <h4>
              {typeof row.name === "string"
                ? row.name
                : `Критерий ${index + 1}`}
            </h4>
            <span>
              {typeof row.score === "number" ? row.score : "—"}
              {typeof row.max_score === "number" && (
                <small> / {row.max_score}</small>
              )}
            </span>
          </div>
          {typeof row.score === "number" &&
            typeof row.max_score === "number" &&
            row.max_score > 0 && (
              <progress
                value={row.score}
                max={row.max_score}
                aria-label={row.name || `Критерий ${index + 1}`}
              />
            )}
          {typeof row.comment === "string" && <p>{row.comment}</p>}
        </div>
      ))}
    </section>
  );
}
