import { getCriterionScores } from "../../utils/assessment";
export function CriteriaAssessment({ score }: { score: number | null }) {
  const rows = getCriterionScores(score);

  return (
    <section className="criteria-assessment" aria-labelledby="criteria-heading">
      <div className="criteria-heading">
        <h3 id="criteria-heading">Оценка по критериям</h3>
        <span>
          {score === null ? "Нет оценки" : `${score} / 100 баллов`}
        </span>
      </div>
      <p className="criteria-caption">
        {score === null
          ? "Пример работы без оценки. Автоматическая проверка не подключена."
          : "Пример разбора: баллы распределены из тестовой оценки."}
      </p>
      {rows.map((row) => (
        <div className="criterion-row" key={row.title}>
          <div className="criterion-title">
            <h4>{row.title}</h4>
            <span>
              {score === null ? "—" : row.points}
              <small> / {row.max}</small>
            </span>
          </div>
          {score !== null && (
            <>
              <progress
                value={row.points}
                max={row.max}
                aria-label={`${row.title}: ${row.points} из ${row.max}`}
              />
              <p>{row.points === row.max ? row.good : row.improve}</p>
            </>
          )}
        </div>
      ))}
    </section>
  );
}
