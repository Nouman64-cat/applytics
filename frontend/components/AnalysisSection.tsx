"use client";

import { useState } from "react";
import { api, ApiError } from "@/lib/api";
import type { ComparisonRun, LocationAnalysis, Profile, TargetRole } from "@/lib/types";
import { btn, card, errorText, input, label, sectionTitle } from "@/lib/ui";
import Spinner from "@/components/Spinner";
import ComparisonResultView from "@/components/ComparisonResultView";

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

  const resumeProfiles = profiles.filter((p) => p.type === "resume");

  async function runComparison() {
    if (selectedProfileIds.length < 2) {
      setError("Select at least 2 resumes to compare");
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
          <button className={`${btn} gap-2`} onClick={runLocationAnalysis} disabled={locationLoading}>
            {locationLoading && <Spinner />}
            {locationLoading ? "Analyzing…" : "Analyze location"}
          </button>
        </div>
        {locationLoading && (
          <div className="flex items-center gap-2 rounded-lg bg-indigo-50 p-3 text-sm text-indigo-700">
            <Spinner className="h-4 w-4" />
            Assessing location impact on remote-hiring odds…
          </div>
        )}
        {locationResult && !locationLoading && (
          <div className="rounded-lg bg-zinc-50 p-3 text-sm">
            <p>
              Location penalty score: <strong className="text-zinc-900">{locationResult.location_penalty_score}</strong> / 100
            </p>
            <p className="mt-1 text-zinc-600">{locationResult.recommendation}</p>
          </div>
        )}
      </div>

      <div className="space-y-2 border-t border-zinc-200/70 pt-4">
        <h3 className="text-sm font-medium">Compare resumes &amp; rank them</h3>
        {resumeProfiles.length < 2 ? (
          <p className="text-sm text-zinc-500">Add at least 2 resumes to this client to run a comparison.</p>
        ) : (
          <>
            <div className="flex flex-wrap gap-3">
              {resumeProfiles.map((p) => (
                <label key={p.id} className="flex items-center gap-1.5 text-sm">
                  <input
                    type="checkbox"
                    checked={selectedProfileIds.includes(p.id)}
                    onChange={() => toggleProfile(p.id)}
                  />
                  Variant {p.variant_label}
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
              <button className={`${btn} gap-2`} onClick={runComparison} disabled={compareLoading}>
                {compareLoading && <Spinner />}
                {compareLoading ? "Comparing… (can take ~10-20s)" : "Compare selected"}
              </button>
            </div>
          </>
        )}

        {compareLoading && (
          <div className="flex items-center gap-2 rounded-lg bg-indigo-50 p-3 text-sm text-indigo-700">
            <Spinner className="h-4 w-4" />
            Running the comparison agent across selected profiles — this can take 10-20 seconds…
          </div>
        )}
        {comparisonResult && !compareLoading && (
          <ComparisonResultView
            comparisonResult={comparisonResult}
            labelFor={(profileId) => {
              const variantLabel = resumeProfiles.find((p) => p.id === profileId)?.variant_label;
              return variantLabel ? `Variant ${variantLabel}` : profileId;
            }}
          />
        )}
      </div>
    </section>
  );
}
