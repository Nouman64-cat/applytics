import type { ComparisonRun } from "@/lib/types";

export default function ComparisonResultView({
  comparisonResult,
  labelFor,
}: {
  comparisonResult: ComparisonRun;
  labelFor: (profileId: string) => string;
}) {
  return (
    <div className="space-y-3 rounded bg-zinc-50 p-3 text-sm dark:bg-zinc-800/50">
      <p className="font-medium">Status: {comparisonResult.status}</p>
      {comparisonResult.result_summary && <p>{comparisonResult.result_summary}</p>}

      {comparisonResult.result_detail?.profile_scores && comparisonResult.result_detail.profile_scores.length > 0 && (
        <div className="space-y-2">
          <p className="font-medium">Ranking</p>
          {[...comparisonResult.result_detail.profile_scores]
            .sort((a, b) => b.score - a.score)
            .map((ps, i) => {
              const isWinner = ps.profile_id === comparisonResult.winner_profile_id;
              return (
                <div key={ps.profile_id} className="border-t border-zinc-200 pt-2 dark:border-zinc-700">
                  <p className="font-medium">
                    #{i + 1} {labelFor(ps.profile_id)} — {ps.score}/100
                    {isWinner && <span className="ml-1 text-xs text-green-600 dark:text-green-500">(top pick)</span>}
                  </p>
                  {ps.strengths.length > 0 && <p className="text-xs">Strengths: {ps.strengths.join("; ")}</p>}
                  {ps.weaknesses.length > 0 && <p className="text-xs">Weaknesses: {ps.weaknesses.join("; ")}</p>}
                </div>
              );
            })}
        </div>
      )}

      {comparisonResult.result_detail?.bottlenecks && comparisonResult.result_detail.bottlenecks.length > 0 && (
        <div className="border-t border-zinc-200 pt-2 dark:border-zinc-700">
          <p className="font-medium">Why the weaker resume(s) may fail with US employers</p>
          <ul className="list-disc pl-4 text-xs">
            {comparisonResult.result_detail.bottlenecks.map((b, i) => (
              <li key={i}>{b}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
