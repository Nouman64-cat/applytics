"use client";

import { useState } from "react";
import { api, ApiError } from "@/lib/api";
import type { ComparisonRun, LocationAnalysis, Profile, TargetRole } from "@/lib/types";
import { btn, card, errorText, input, label, sectionTitle } from "@/lib/ui";

export default function AnalysisSection({
  clientId,
  targetRoles,
  profiles,
}: {
  clientId: string;
  targetRoles: TargetRole[];
  profiles: Profile[];
}) {
  const [locationTargetRoleId, setLocationTargetRoleId] = useState("");
  const [locationResult, setLocationResult] = useState<LocationAnalysis | null>(null);
  const [locationLoading, setLocationLoading] = useState(false);

  const [compareTargetRoleId, setCompareTargetRoleId] = useState("");
  const [selectedProfileIds, setSelectedProfileIds] = useState<string[]>([]);
  const [comparisonResult, setComparisonResult] = useState<ComparisonRun | null>(null);
  const [compareLoading, setCompareLoading] = useState(false);

  const [error, setError] = useState<string | null>(null);

  async function runLocationAnalysis() {
    setLocationLoading(true);
    setError(null);
    try {
      setLocationResult(await api.analysis.location(clientId, locationTargetRoleId || undefined));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Location analysis failed");
    } finally {
      setLocationLoading(false);
    }
  }

  function toggleProfile(id: string) {
    setSelectedProfileIds((prev) => (prev.includes(id) ? prev.filter((p) => p !== id) : [...prev, id]));
  }

  async function runComparison() {
    if (selectedProfileIds.length < 2) {
      setError("Select at least 2 profiles to compare");
      return;
    }
    setCompareLoading(true);
    setError(null);
    try {
      setComparisonResult(
        await api.analysis.compare(clientId, selectedProfileIds, compareTargetRoleId || undefined)
      );
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Comparison failed");
    } finally {
      setCompareLoading(false);
    }
  }

  return (
    <section className={`${card} space-y-6`}>
      <h2 className={sectionTitle}>AI analysis</h2>
      {error && <p className={errorText}>{error}</p>}

      <div className="space-y-2">
        <h3 className="text-sm font-medium">Location impact</h3>
        <div className="flex flex-wrap items-end gap-2">
          <div>
            <label className={label}>Target role (optional)</label>
            <select
              className={input}
              value={locationTargetRoleId}
              onChange={(e) => setLocationTargetRoleId(e.target.value)}
            >
              <option value="">None</option>
              {targetRoles.map((tr) => (
                <option key={tr.id} value={tr.id}>
                  {tr.title}
                </option>
              ))}
            </select>
          </div>
          <button className={btn} onClick={runLocationAnalysis} disabled={locationLoading}>
            {locationLoading ? "Analyzing…" : "Analyze location"}
          </button>
        </div>
        {locationResult && (
          <div className="rounded bg-zinc-50 p-3 text-sm dark:bg-zinc-800/50">
            <p>
              Location penalty score: <strong>{locationResult.location_penalty_score}</strong> / 100
            </p>
            <p className="mt-1 text-zinc-600 dark:text-zinc-400">{locationResult.recommendation}</p>
          </div>
        )}
      </div>

      <div className="space-y-2 border-t border-zinc-200 pt-4 dark:border-zinc-800">
        <h3 className="text-sm font-medium">Compare profile variants (A/B test)</h3>
        {profiles.length < 2 ? (
          <p className="text-sm text-zinc-500">Add at least 2 profiles to run a comparison.</p>
        ) : (
          <>
            <div className="flex flex-wrap gap-3">
              {profiles.map((p) => (
                <label key={p.id} className="flex items-center gap-1.5 text-sm">
                  <input
                    type="checkbox"
                    checked={selectedProfileIds.includes(p.id)}
                    onChange={() => toggleProfile(p.id)}
                  />
                  {p.type} · {p.variant_label}
                </label>
              ))}
            </div>
            <div className="flex flex-wrap items-end gap-2">
              <div>
                <label className={label}>Target role (optional)</label>
                <select
                  className={input}
                  value={compareTargetRoleId}
                  onChange={(e) => setCompareTargetRoleId(e.target.value)}
                >
                  <option value="">None</option>
                  {targetRoles.map((tr) => (
                    <option key={tr.id} value={tr.id}>
                      {tr.title}
                    </option>
                  ))}
                </select>
              </div>
              <button className={btn} onClick={runComparison} disabled={compareLoading}>
                {compareLoading ? "Comparing… (can take ~10-20s)" : "Compare selected"}
              </button>
            </div>
          </>
        )}

        {comparisonResult && (
          <div className="space-y-2 rounded bg-zinc-50 p-3 text-sm dark:bg-zinc-800/50">
            <p className="font-medium">Status: {comparisonResult.status}</p>
            {comparisonResult.result_summary && <p>{comparisonResult.result_summary}</p>}
            {comparisonResult.winner_profile_id && (
              <p>
                Winner profile:{" "}
                <span className="font-mono text-xs">{comparisonResult.winner_profile_id}</span>
              </p>
            )}
            {comparisonResult.result_detail?.profile_scores?.map((ps) => (
              <div key={ps.profile_id} className="border-t border-zinc-200 pt-2 dark:border-zinc-700">
                <p className="font-mono text-xs text-zinc-500">{ps.profile_id}</p>
                <p>Score: {ps.score}/100</p>
                {ps.strengths.length > 0 && <p className="text-xs">Strengths: {ps.strengths.join("; ")}</p>}
                {ps.weaknesses.length > 0 && <p className="text-xs">Weaknesses: {ps.weaknesses.join("; ")}</p>}
              </div>
            ))}
            {comparisonResult.result_detail?.bottlenecks && comparisonResult.result_detail.bottlenecks.length > 0 && (
              <div className="border-t border-zinc-200 pt-2 dark:border-zinc-700">
                <p className="font-medium">Bottlenecks</p>
                <ul className="list-disc pl-4 text-xs">
                  {comparisonResult.result_detail.bottlenecks.map((b, i) => (
                    <li key={i}>{b}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </div>
    </section>
  );
}
