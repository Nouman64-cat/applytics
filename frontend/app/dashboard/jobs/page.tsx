"use client";

import { useCallback, useEffect, useState, type FormEvent } from "react";
import { api, ApiError } from "@/lib/api";
import type { Job, JobSource, RemoteType } from "@/lib/types";
import { badge, btn, card, errorText, input, label, sectionTitle } from "@/lib/ui";

export default function JobsPage() {
  const [sources, setSources] = useState<JobSource[]>([]);
  const [jobs, setJobs] = useState<Job[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [scrapeStatus, setScrapeStatus] = useState<string | null>(null);

  const [source, setSource] = useState("");
  const [keywords, setKeywords] = useState("");
  const [remoteOnly, setRemoteOnly] = useState(true);
  const [maxResults, setMaxResults] = useState(20);
  const [scraping, setScraping] = useState(false);

  const [filterSource, setFilterSource] = useState("");
  const [filterRemoteType, setFilterRemoteType] = useState<RemoteType | "">("");
  const [filterKeyword, setFilterKeyword] = useState("");

  const refreshJobs = useCallback(() => {
    api.jobs
      .list({ source: filterSource || undefined, remote_type: filterRemoteType || undefined, keyword: filterKeyword || undefined, limit: 50 })
      .then(setJobs)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Failed to load jobs"));
  }, [filterSource, filterRemoteType, filterKeyword]);

  useEffect(() => {
    api.scrape
      .sources()
      .then((s) => {
        setSources(s);
        if (!source) {
          const firstEnabled = s.find((x) => x.is_enabled);
          if (firstEnabled) setSource(firstEnabled.name);
        }
      })
      .catch((err) => setError(err instanceof ApiError ? err.message : "Failed to load sources"));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(refreshJobs, [refreshJobs]);

  function sourceName(jobSourceId: string): string {
    return sources.find((s) => s.id === jobSourceId)?.name ?? "unknown";
  }

  async function handleScrape(e: FormEvent) {
    e.preventDefault();
    setScraping(true);
    setError(null);
    setScrapeStatus(null);
    try {
      const run = await api.scrape.trigger({
        source,
        keywords: keywords || undefined,
        remote_only: remoteOnly,
        max_results: maxResults,
      });
      setScrapeStatus(
        `Run ${run.status}: ${run.jobs_found_count} job(s) found${run.error_message ? ` — ${run.error_message}` : ""}`
      );
      refreshJobs();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Scrape failed");
    } finally {
      setScraping(false);
    }
  }

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold">Jobs</h1>

      <section className={`${card} space-y-3`}>
        <h2 className={sectionTitle}>Trigger a scrape</h2>
        <div className="flex flex-wrap gap-2">
          {sources.map((s) => (
            <span key={s.id} className={badge}>
              {s.name}: {s.is_enabled ? "enabled" : "disabled"}
            </span>
          ))}
        </div>
        <form onSubmit={handleScrape} className="grid grid-cols-1 gap-3 sm:grid-cols-4">
          <div>
            <label className={label}>Source</label>
            <select className={input} value={source} onChange={(e) => setSource(e.target.value)} required>
              <option value="">Select…</option>
              {sources.map((s) => (
                <option key={s.id} value={s.name} disabled={!s.is_enabled}>
                  {s.name} {s.is_enabled ? "" : "(disabled)"}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className={label}>Keywords</label>
            <input className={input} value={keywords} onChange={(e) => setKeywords(e.target.value)} placeholder="backend engineer" />
          </div>
          <div>
            <label className={label}>Max results</label>
            <input
              className={input}
              type="number"
              min={1}
              max={50}
              value={maxResults}
              onChange={(e) => setMaxResults(Number(e.target.value))}
            />
          </div>
          <div className="flex items-end gap-2">
            <label className="flex items-center gap-1.5 text-sm">
              <input type="checkbox" checked={remoteOnly} onChange={(e) => setRemoteOnly(e.target.checked)} />
              Remote only
            </label>
          </div>
          <div className="sm:col-span-4">
            <button type="submit" className={btn} disabled={scraping || !source}>
              {scraping ? "Scraping… (can take ~10-30s)" : "Run scrape"}
            </button>
          </div>
        </form>
        {scrapeStatus && <p className="text-sm text-zinc-600 dark:text-zinc-400">{scrapeStatus}</p>}
      </section>

      {error && <p className={errorText}>{error}</p>}

      <section className={`${card} space-y-3`}>
        <div className="flex flex-wrap items-end justify-between gap-3">
          <h2 className={sectionTitle}>Scraped jobs</h2>
          <div className="flex flex-wrap items-end gap-2">
            <div>
              <label className={label}>Source</label>
              <select className={input} value={filterSource} onChange={(e) => setFilterSource(e.target.value)}>
                <option value="">All</option>
                {sources.map((s) => (
                  <option key={s.id} value={s.name}>
                    {s.name}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className={label}>Remote type</label>
              <select
                className={input}
                value={filterRemoteType}
                onChange={(e) => setFilterRemoteType(e.target.value as RemoteType | "")}
              >
                <option value="">All</option>
                <option value="fully_remote">Fully remote</option>
                <option value="hybrid">Hybrid</option>
                <option value="onsite">Onsite</option>
                <option value="unknown">Unknown</option>
              </select>
            </div>
            <div>
              <label className={label}>Keyword</label>
              <input className={input} value={filterKeyword} onChange={(e) => setFilterKeyword(e.target.value)} />
            </div>
          </div>
        </div>

        {jobs === null ? (
          <p className="text-sm text-zinc-500">Loading…</p>
        ) : jobs.length === 0 ? (
          <p className="text-sm text-zinc-500">No jobs found yet — try running a scrape above.</p>
        ) : (
          <ul className="space-y-2">
            {jobs.map((j) => (
              <li key={j.id} className="rounded-md border border-zinc-200 p-3 text-sm dark:border-zinc-800">
                <div className="flex items-center justify-between">
                  <a href={j.apply_url ?? "#"} target="_blank" rel="noreferrer" className="font-medium hover:underline">
                    {j.title}
                  </a>
                  <div className="flex shrink-0 gap-1.5">
                    <span className={badge}>{sourceName(j.job_source_id)}</span>
                    <span className={badge}>{j.remote_type}</span>
                  </div>
                </div>
                <p className="text-zinc-500">
                  {j.company ?? "?"} {j.location_raw ? `· ${j.location_raw}` : ""}
                </p>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
