"use client";

import { useState } from "react";
import { api, ApiError } from "@/lib/api";
import type { ComparisonRun, JobMatchRun, LocationAnalysis, Profile, TargetRole } from "@/lib/types";
import { btn, card, errorText, input, label, remoteBadge, sectionTitle } from "@/lib/ui";
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

  const [matchProfileId, setMatchProfileId] = useState("");
  const [matchResult, setMatchResult] = useState<JobMatchRun | null>(null);
  const [matchLoading, setMatchLoading] = useState(false);

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

  async function runJobMatch() {
    if (!matchProfileId) {
      setError("Select a resume to match against scraped jobs");
      return;
    }
    setMatchLoading(true);
    setError(null);
    try {
      setMatchResult(await api.analysis.matchJobs(matchProfileId));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Job matching failed");
    } finally {
      setMatchLoading(false);
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

      <div className="space-y-2 border-t border-zinc-200/70 pt-4">
        <h3 className="text-sm font-medium">Match resume to scraped jobs</h3>
        {resumeProfiles.length === 0 ? (
          <p className="text-sm text-zinc-500">Add a resume to this client to find matching jobs.</p>
        ) : (
          <div className="flex flex-wrap items-end gap-2">
            <div>
              <label className={label}>Resume</label>
              <select className={input} value={matchProfileId} onChange={(e) => setMatchProfileId(e.target.value)}>
                <option value="">Select…</option>
                {resumeProfiles.map((p) => (
                  <option key={p.id} value={p.id}>
                    Variant {p.variant_label}
                  </option>
                ))}
              </select>
            </div>
            <button className={`${btn} gap-2`} onClick={runJobMatch} disabled={matchLoading || !matchProfileId}>
              {matchLoading && <Spinner />}
              {matchLoading ? "Matching… (can take ~10-20s)" : "Find matching jobs"}
            </button>
          </div>
        )}

        {matchLoading && (
          <div className="flex items-center gap-2 rounded-lg bg-indigo-50 p-3 text-sm text-indigo-700">
            <Spinner className="h-4 w-4" />
            Scoring recently scraped jobs against this resume — this can take 10-20 seconds…
          </div>
        )}

        {matchResult && !matchLoading && (
          matchResult.matches.length === 0 ? (
            <p className="text-sm text-zinc-500">
              No strong matches found among recently scraped jobs — try running a fresh scrape first.
            </p>
          ) : (
            <div className="space-y-2">
              {matchResult.matches.map((m) => (
                <div key={m.job_id} className="rounded-xl border border-zinc-200/70 p-3">
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <a
                        href={m.apply_url ?? "#"}
                        target="_blank"
                        rel="noreferrer"
                        className="truncate font-medium text-zinc-900 hover:text-indigo-600 hover:underline"
                      >
                        {m.title}
                      </a>
                      <p className="mt-0.5 flex flex-wrap items-center gap-1.5 text-xs text-zinc-500">
                        <span className="truncate">
                          {m.company ?? "—"}
                          {m.location_raw ? ` · ${m.location_raw}` : ""}
                        </span>
                        <span className={remoteBadge(m.remote_type)}>{m.remote_type}</span>
                      </p>
                    </div>
                    <span className="shrink-0 text-sm font-semibold text-zinc-900">{m.score}/100</span>
                  </div>
                  <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-zinc-100">
                    <div
                      className="h-full rounded-full bg-indigo-600"
                      style={{ width: `${Math.max(0, Math.min(100, m.score))}%` }}
                    />
                  </div>
                  <p className="mt-2 text-xs text-zinc-600">{m.rationale}</p>
                </div>
              ))}
            </div>
          )
        )}
      </div>
    </section>
  );
}
