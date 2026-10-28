import { assessmentCriteria } from "../data/mockData";
// Proportional allocation is only for consistent demonstration data.
export function getCriterionScores(score: number | null) {
  let allocated = 0;
  let cumulativeMax = 0;
  return assessmentCriteria.map((criterion) => {
    cumulativeMax += criterion.max;
    const cumulativeScore =
      score === null ? 0 : Math.round((score * cumulativeMax) / 100);
    const points = cumulativeScore - allocated;
    allocated = cumulativeScore;
    return { ...criterion, points };
  });
}
