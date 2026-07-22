import type { ComparisonRun } from "@/lib/types";

export default function ComparisonResultView({
  comparisonResult,
  labelFor,
}: {
  comparisonResult: ComparisonRun;
  labelFor: (profileId: string) => string;
}) {
  return (
    <div className="space-y-4 rounded-2xl border border-zinc-200/70 bg-white p-4 text-sm shadow-sm">
      <div className="flex items-center gap-2">
        <span className="rounded-full bg-indigo-50 px-2 py-0.5 text-xs font-medium text-indigo-600">
          {comparisonResult.status}
        </span>
      </div>
      {comparisonResult.result_summary && <p className="text-zinc-700">{comparisonResult.result_summary}</p>}

      {comparisonResult.result_detail?.profile_scores && comparisonResult.result_detail.profile_scores.length > 0 && (
        <div className="space-y-2">
          <p className="text-xs font-semibold uppercase tracking-wide text-zinc-400">Ranking</p>
          {[...comparisonResult.result_detail.profile_scores]
            .sort((a, b) => b.score - a.score)
            .map((ps, i) => {
              const isWinner = ps.profile_id === comparisonResult.winner_profile_id;
              return (
                <div
                  key={ps.profile_id}
                  className={`rounded-xl border p-3 ${
                    isWinner ? "border-indigo-200 bg-indigo-50/40" : "border-zinc-200/70"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <p className="font-medium text-zinc-900">
                      #{i + 1} {labelFor(ps.profile_id)}
                      {isWinner && (
                        <span className="ml-2 rounded-full bg-emerald-50 px-2 py-0.5 text-xs font-medium text-emerald-700">
                          top pick
                        </span>
                      )}
                    </p>
                    <span className="text-sm font-semibold text-zinc-900">{ps.score}/100</span>
                  </div>
                  <div className="mt-1.5 h-1.5 w-full overflow-hidden rounded-full bg-zinc-100">
                    <div
                      className={`h-full rounded-full ${isWinner ? "bg-indigo-600" : "bg-zinc-300"}`}
                      style={{ width: `${Math.max(0, Math.min(100, ps.score))}%` }}
                    />
                  </div>
                  {ps.strengths.length > 0 && (
                    <p className="mt-2 text-xs text-zinc-600">
                      <span className="font-medium text-zinc-500">Strengths:</span> {ps.strengths.join("; ")}
                    </p>
                  )}
                  {ps.weaknesses.length > 0 && (
                    <p className="mt-1 text-xs text-zinc-600">
                      <span className="font-medium text-zinc-500">Weaknesses:</span> {ps.weaknesses.join("; ")}
                    </p>
                  )}
                </div>
              );
            })}
        </div>
      )}

      {comparisonResult.result_detail?.bottlenecks && comparisonResult.result_detail.bottlenecks.length > 0 && (
        <div className="rounded-xl border border-amber-200 bg-amber-50/50 p-3">
          <p className="text-xs font-semibold uppercase tracking-wide text-amber-700">
            Why the weaker resume(s) may fail with US employers
          </p>
          <ul className="mt-1.5 list-disc space-y-0.5 pl-4 text-xs text-zinc-700">
            {comparisonResult.result_detail.bottlenecks.map((b, i) => (
              <li key={i}>{b}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
