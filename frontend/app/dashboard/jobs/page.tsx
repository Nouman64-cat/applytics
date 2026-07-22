"use client";

import { useCallback, useEffect, useState, type FormEvent } from "react";
import { api, ApiError } from "@/lib/api";
import type { Job, JobSource, RemoteType } from "@/lib/types";
import Spinner from "@/components/Spinner";
import { remoteBadge } from "@/lib/ui";

// This page is deliberately light-theme-only, regardless of the rest of the app or the
// user's system preference — no `dark:` classes anywhere below. The wrapping div cancels
// the shared dashboard layout's padding and re-applies its own, with an opaque white
// background tall enough to cover the full content area, so it reads as a genuine light
// panel rather than a light box floating on a dark surface.
const PAGE_SIZE = 20;

const lInput =
  "w-full rounded-lg border border-zinc-200 bg-white px-3 py-2 text-sm text-zinc-900 placeholder:text-zinc-400 shadow-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/40 focus:border-indigo-400 transition-shadow";
const lLabel = "block text-xs font-medium text-zinc-500 mb-1.5";
const lBtn =
  "inline-flex items-center justify-center gap-2 rounded-lg bg-indigo-600 text-white px-3.5 py-2 text-sm font-medium shadow-sm hover:bg-indigo-700 active:bg-indigo-800 disabled:opacity-50 disabled:cursor-not-allowed transition-colors";
const lBtnSecondary =
  "inline-flex items-center justify-center gap-2 rounded-lg border border-zinc-200 bg-white px-3.5 py-2 text-sm font-medium text-zinc-700 shadow-sm hover:bg-zinc-50 hover:border-zinc-300 disabled:opacity-50 disabled:cursor-not-allowed transition-colors";
// No external logo assets/CDNs here — each source gets a simple colored monogram icon
// (brand-adjacent color, not an actual trademarked logo) so the jobs table is scannable
// at a glance without a network dependency.
const SOURCE_ICONS: Record<string, { letter: string; bg: string; text: string }> = {
  adzuna: { letter: "A", bg: "bg-teal-100", text: "text-teal-700" },
  linkedin: { letter: "in", bg: "bg-sky-100", text: "text-sky-700" },
  indeed: { letter: "I", bg: "bg-blue-100", text: "text-blue-700" },
  glassdoor: { letter: "G", bg: "bg-green-100", text: "text-green-700" },
  jobwright: { letter: "J", bg: "bg-purple-100", text: "text-purple-700" },
  jobright: { letter: "J", bg: "bg-purple-100", text: "text-purple-700" },
};

function LinkIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" strokeWidth={1.75} stroke="currentColor" className="h-4 w-4">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M13.5 6H5.25A2.25 2.25 0 0 0 3 8.25v10.5A2.25 2.25 0 0 0 5.25 21h10.5A2.25 2.25 0 0 0 18 18.75V10.5m-10.5 3L21 3m0 0h-5.25M21 3v5.25"
      />
    </svg>
  );
}

function SourceBadge({ name }: { name: string }) {
  const icon = SOURCE_ICONS[name.toLowerCase()] ?? { letter: "?", bg: "bg-zinc-100", text: "text-zinc-500" };
  return (
    <span className="inline-flex items-center gap-1.5">
      <span
        className={`flex h-5 w-5 shrink-0 items-center justify-center rounded-md text-[10px] font-bold ${icon.bg} ${icon.text}`}
      >
        {icon.letter}
      </span>
      <span className="text-sm text-zinc-700 capitalize">{name}</span>
    </span>
  );
}

export default function JobsPage() {
  const [sources, setSources] = useState<JobSource[]>([]);
  const [jobs, setJobs] = useState<Job[] | null>(null);
  const [total, setTotal] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [scrapeStatus, setScrapeStatus] = useState<string | null>(null);
  const [showScrapeForm, setShowScrapeForm] = useState(false);

  const [source, setSource] = useState("");
  const [keywords, setKeywords] = useState("");
  const [remoteOnly, setRemoteOnly] = useState(true);
  const [maxResults, setMaxResults] = useState(""); // blank = unlimited (until no new results)
  const [scraping, setScraping] = useState(false);

  const [filterSource, setFilterSource] = useState("");
  const [filterRemoteType, setFilterRemoteType] = useState<RemoteType | "">("");
  const [filterKeyword, setFilterKeyword] = useState("");
  const [postedAfter, setPostedAfter] = useState("");
  const [postedBefore, setPostedBefore] = useState("");
  const [page, setPage] = useState(1);

  const filterParams = {
    source: filterSource || undefined,
    remote_type: filterRemoteType || undefined,
    keyword: filterKeyword || undefined,
    posted_after: postedAfter || undefined,
    posted_before: postedBefore || undefined,
  };

  const refreshJobs = useCallback(() => {
    api.jobs
      .list({ ...filterParams, limit: PAGE_SIZE, offset: (page - 1) * PAGE_SIZE })
      .then(setJobs)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Failed to load jobs"));
    api.jobs
      .count(filterParams)
      .then((res) => setTotal(res.total))
      .catch(() => setTotal(0));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filterSource, filterRemoteType, filterKeyword, postedAfter, postedBefore, page]);

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

  // Reset to page 1 whenever a filter changes so the user isn't stranded on an empty page.
  useEffect(() => {
    setPage(1);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filterSource, filterRemoteType, filterKeyword, postedAfter, postedBefore]);

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
        max_results: maxResults ? Number(maxResults) : undefined,
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

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <div className="-m-6 min-h-[calc(100vh-3.5rem)] bg-white p-6 text-zinc-900">
      <div className="mx-auto max-w-none space-y-5">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-semibold tracking-tight text-zinc-900">Jobs</h1>
            <p className="text-sm text-zinc-500">Browse scraped listings and trigger new scrape runs.</p>
          </div>
          <button className={lBtnSecondary} onClick={() => setShowScrapeForm((v) => !v)}>
            {showScrapeForm ? "Hide scrape form" : "Trigger a scrape"}
          </button>
        </div>

        {showScrapeForm && (
          <section className="space-y-3 rounded-2xl border border-zinc-200/70 bg-white p-4 shadow-sm">
            <div className="flex flex-wrap gap-2">
              {sources.map((s) => (
                <span
                  key={s.id}
                  className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${
                    s.is_enabled ? "bg-emerald-50 text-emerald-700" : "bg-zinc-100 text-zinc-400"
                  }`}
                >
                  {s.name}: {s.is_enabled ? "enabled" : "disabled"}
                </span>
              ))}
            </div>
            <form onSubmit={handleScrape} className="grid grid-cols-2 gap-3 sm:grid-cols-5">
              <div>
                <label className={lLabel}>Source</label>
                <select className={lInput} value={source} onChange={(e) => setSource(e.target.value)} required>
                  <option value="">Select…</option>
                  {sources.map((s) => (
                    <option key={s.id} value={s.name} disabled={!s.is_enabled}>
                      {s.name} {s.is_enabled ? "" : "(disabled)"}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className={lLabel}>Keywords</label>
                <input
                  className={lInput}
                  value={keywords}
                  onChange={(e) => setKeywords(e.target.value)}
                  placeholder="backend engineer"
                />
              </div>
              <div>
                <label className={lLabel}>Max results</label>
                <input
                  className={lInput}
                  type="number"
                  min={1}
                  placeholder="Unlimited"
                  value={maxResults}
                  onChange={(e) => setMaxResults(e.target.value)}
                />
              </div>
              <div className="flex items-end">
                <label className="flex items-center gap-1.5 text-sm text-zinc-700">
                  <input type="checkbox" checked={remoteOnly} onChange={(e) => setRemoteOnly(e.target.checked)} />
                  Remote only
                </label>
              </div>
              <div className="flex items-end">
                <button type="submit" className={`${lBtn} w-full`} disabled={scraping || !source}>
                  {scraping && <Spinner />}
                  {scraping ? "Scraping…" : "Run scrape"}
                </button>
              </div>
            </form>
            <p className="text-xs text-zinc-500">
              Leave &quot;Max results&quot; blank to keep paginating until the source has no new results (capped
              internally as a safety limit) — otherwise it stops at the number you enter.
            </p>
            {scraping && (
              <div className="flex items-center gap-2 rounded-lg bg-indigo-50 p-2.5 text-sm text-indigo-700">
                <Spinner className="h-4 w-4" />
                Running the scraper — unlimited/headless-browser sources can take a while.
              </div>
            )}
            {scrapeStatus && <p className="text-sm text-zinc-600">{scrapeStatus}</p>}
          </section>
        )}

        {error && <p className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-600">{error}</p>}

        <section className="space-y-3 rounded-2xl border border-zinc-200/70 bg-white p-4 shadow-sm">
          <div className="flex flex-wrap items-end gap-2">
            <div className="w-32">
              <label className={lLabel}>Source</label>
              <select className={lInput} value={filterSource} onChange={(e) => setFilterSource(e.target.value)}>
                <option value="">All</option>
                {sources.map((s) => (
                  <option key={s.id} value={s.name}>
                    {s.name}
                  </option>
                ))}
              </select>
            </div>
            <div className="w-32">
              <label className={lLabel}>Remote type</label>
              <select
                className={lInput}
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
            <div className="w-40">
              <label className={lLabel}>Keyword</label>
              <input className={lInput} value={filterKeyword} onChange={(e) => setFilterKeyword(e.target.value)} />
            </div>
            <div className="w-36">
              <label className={lLabel}>Posted after</label>
              <input
                className={lInput}
                type="date"
                value={postedAfter}
                onChange={(e) => setPostedAfter(e.target.value)}
              />
            </div>
            <div className="w-36">
              <label className={lLabel}>Posted before</label>
              <input
                className={lInput}
                type="date"
                value={postedBefore}
                onChange={(e) => setPostedBefore(e.target.value)}
              />
            </div>
            <div className="ml-auto text-xs font-medium text-zinc-400">{total} job(s) found</div>
          </div>

          {jobs === null ? (
            <div className="flex items-center gap-2 py-8 text-sm text-zinc-500">
              <Spinner className="h-4 w-4" />
              Loading…
            </div>
          ) : jobs.length === 0 ? (
            <p className="py-8 text-center text-sm text-zinc-500">
              No jobs match these filters — try running a scrape above.
            </p>
          ) : (
            <div className="overflow-x-auto rounded-xl border border-zinc-200/70">
              <table className="w-full border-collapse text-sm">
                <thead>
                  <tr className="bg-zinc-50 text-left text-xs uppercase tracking-wide text-zinc-500">
                    <th className="px-3 py-2.5 font-medium">Source</th>
                    <th className="px-3 py-2.5 font-medium">Title</th>
                    <th className="px-3 py-2.5 font-medium">Company</th>
                    <th className="px-3 py-2.5 font-medium">Location</th>
                    <th className="px-3 py-2.5 font-medium">Remote</th>
                    <th className="px-3 py-2.5 font-medium">Posted</th>
                    <th className="px-3 py-2.5 font-medium text-right">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {jobs.map((j) => (
                    <tr key={j.id} className="border-t border-zinc-100 hover:bg-indigo-50/40">
                      <td className="whitespace-nowrap px-3 py-2.5">
                        <SourceBadge name={sourceName(j.job_source_id)} />
                      </td>
                      <td className="max-w-xs truncate px-3 py-2.5">
                        <a
                          href={j.apply_url ?? "#"}
                          target="_blank"
                          rel="noreferrer"
                          className="font-medium text-zinc-900 hover:text-indigo-600 hover:underline"
                          title={j.title}
                        >
                          {j.title}
                        </a>
                      </td>
                      <td className="max-w-[10rem] truncate px-3 py-2.5 text-zinc-600" title={j.company ?? undefined}>
                        {j.company ?? "—"}
                      </td>
                      <td
                        className="max-w-[10rem] truncate px-3 py-2.5 text-zinc-600"
                        title={j.location_raw ?? undefined}
                      >
                        {j.location_raw ?? "—"}
                      </td>
                      <td className="px-3 py-2.5">
                        <span className={remoteBadge(j.remote_type)}>{j.remote_type}</span>
                      </td>
                      <td className="whitespace-nowrap px-3 py-2.5 text-zinc-500">
                        {(j.posted_at ?? j.scraped_at).slice(0, 10)}
                      </td>
                      <td className="whitespace-nowrap px-3 py-2.5 text-right">
                        {j.apply_url ? (
                          <a
                            href={j.apply_url}
                            target="_blank"
                            rel="noreferrer"
                            title="Open job posting"
                            className="inline-flex h-7 w-7 items-center justify-center rounded-md text-zinc-400 hover:bg-indigo-50 hover:text-indigo-600"
                          >
                            <LinkIcon />
                          </a>
                        ) : (
                          <span className="inline-flex h-7 w-7 items-center justify-center text-zinc-200" title="No URL available">
                            <LinkIcon />
                          </span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {jobs !== null && jobs.length > 0 && (
            <div className="flex items-center justify-between border-t border-zinc-200/70 pt-3 text-sm">
              <span className="text-zinc-500">
                Page <span className="font-medium text-zinc-700">{page}</span> of {totalPages}
              </span>
              <div className="flex gap-2">
                <button
                  className={lBtnSecondary}
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page <= 1}
                >
                  Previous
                </button>
                <button
                  className={lBtnSecondary}
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                  disabled={page >= totalPages}
                >
                  Next
                </button>
              </div>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
