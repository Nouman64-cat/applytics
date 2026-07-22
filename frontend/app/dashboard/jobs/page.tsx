"use client";

import { useCallback, useEffect, useState, type FormEvent, type KeyboardEvent } from "react";
import { api, ApiError } from "@/lib/api";
import type { Job, JobSource, RemoteType } from "@/lib/types";
import Spinner from "@/components/Spinner";
import ConfirmDialog from "@/components/ConfirmDialog";
import Switch from "@/components/Switch";
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
const lTagInputWrap =
  "flex min-h-[2.375rem] w-full flex-wrap items-center gap-1.5 rounded-lg border border-zinc-200 bg-white px-2 py-1.5 shadow-sm focus-within:ring-2 focus-within:ring-indigo-500/40 focus-within:border-indigo-400 transition-shadow";
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

function TrashIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" strokeWidth={1.75} stroke="currentColor" className="h-4 w-4">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="m14.74 9-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 0 1-2.244 2.077H8.084a2.25 2.25 0 0 1-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 0 0-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 0 1 3.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 0 0-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 0 0-7.5 0"
      />
    </svg>
  );
}

function SourceIcon({ name, className = "h-5 w-5 text-[10px]" }: { name: string; className?: string }) {
  const icon = SOURCE_ICONS[name.toLowerCase()] ?? { letter: "?", bg: "bg-zinc-100", text: "text-zinc-500" };
  return (
    <span className={`flex shrink-0 items-center justify-center rounded-md font-bold ${icon.bg} ${icon.text} ${className}`}>
      {icon.letter}
    </span>
  );
}

function SourceBadge({ name }: { name: string }) {
  return (
    <span className="inline-flex items-center gap-1.5">
      <SourceIcon name={name} />
      <span className="text-sm text-zinc-700 capitalize">{name}</span>
    </span>
  );
}

function SparklesIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" strokeWidth={1.75} stroke="currentColor" className="h-4 w-4">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M9.813 15.904 9 18.75l-.813-2.846a4.5 4.5 0 0 0-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 0 0 3.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 0 0 3.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 0 0-3.09 3.09ZM18.259 8.715 18 9.75l-.259-1.035a3.375 3.375 0 0 0-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 0 0 2.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 0 0 2.456 2.456L21.75 6l-1.035.259a3.375 3.375 0 0 0-2.456 2.456Z"
      />
    </svg>
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
  const [position, setPosition] = useState("");
  const [keywordTags, setKeywordTags] = useState<string[]>([]);
  const [keywordInput, setKeywordInput] = useState("");
  const [remoteOnly, setRemoteOnly] = useState(true);
  const [maxResults, setMaxResults] = useState(""); // blank = unlimited (until no new results)
  const [scraping, setScraping] = useState(false);
  const [keywordSuggestions, setKeywordSuggestions] = useState<string[]>([]);
  const [suggestingKeywords, setSuggestingKeywords] = useState(false);

  const [filterSource, setFilterSource] = useState("");
  const [filterRemoteType, setFilterRemoteType] = useState<RemoteType | "">("");
  const [filterKeyword, setFilterKeyword] = useState("");
  const [postedAfter, setPostedAfter] = useState("");
  const [postedBefore, setPostedBefore] = useState("");
  const [page, setPage] = useState(1);

  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [bulkDeleting, setBulkDeleting] = useState(false);
  const [bulkDeleteNotice, setBulkDeleteNotice] = useState<string | null>(null);
  const [confirmTarget, setConfirmTarget] = useState<
    { kind: "single"; job: Job } | { kind: "bulk"; count: number } | null
  >(null);

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

  // Selection is scoped to the currently visible page/filter set — clear it whenever either changes.
  useEffect(() => {
    setSelectedIds(new Set());
  }, [page, filterSource, filterRemoteType, filterKeyword, postedAfter, postedBefore]);

  function toggleSelected(id: string) {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function toggleSelectAll() {
    if (!jobs) return;
    setSelectedIds((prev) => (prev.size === jobs.length ? new Set() : new Set(jobs.map((j) => j.id))));
  }

  async function handleToggleUsed(job: Job, value: boolean) {
    setJobs((prev) => prev && prev.map((j) => (j.id === job.id ? { ...j, is_used: value } : j)));
    try {
      await api.jobs.setUsed(job.id, value);
    } catch (err) {
      setJobs((prev) => prev && prev.map((j) => (j.id === job.id ? { ...j, is_used: !value } : j)));
      setError(err instanceof ApiError ? err.message : "Failed to update job");
    }
  }

  async function handleDeleteJob(job: Job) {
    setDeletingId(job.id);
    setError(null);
    try {
      await api.jobs.delete(job.id);
      setSelectedIds((prev) => {
        const next = new Set(prev);
        next.delete(job.id);
        return next;
      });
      refreshJobs();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to delete job");
    } finally {
      setDeletingId(null);
      setConfirmTarget(null);
    }
  }

  async function handleBulkDelete() {
    if (selectedIds.size === 0) return;
    setBulkDeleting(true);
    setError(null);
    setBulkDeleteNotice(null);
    try {
      const result = await api.jobs.bulkDelete([...selectedIds]);
      setSelectedIds(new Set());
      refreshJobs();
      setBulkDeleteNotice(
        result.skipped > 0
          ? `Deleted ${result.deleted} job(s). Skipped ${result.skipped} — they have an application logged against them.`
          : `Deleted ${result.deleted} job(s).`
      );
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Bulk delete failed");
    } finally {
      setBulkDeleting(false);
      setConfirmTarget(null);
    }
  }

  function sourceName(jobSourceId: string): string {
    return sources.find((s) => s.id === jobSourceId)?.name ?? "unknown";
  }

  function addKeywordTag(raw: string) {
    const tag = raw.trim();
    if (!tag) return;
    setKeywordTags((prev) => (prev.includes(tag) ? prev : [...prev, tag]));
  }

  function removeKeywordTag(tag: string) {
    setKeywordTags((prev) => prev.filter((t) => t !== tag));
  }

  function handleKeywordInputKeyDown(e: KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter" || e.key === ",") {
      e.preventDefault();
      addKeywordTag(keywordInput);
      setKeywordInput("");
    } else if (e.key === "Backspace" && keywordInput === "" && keywordTags.length > 0) {
      setKeywordTags((prev) => prev.slice(0, -1));
    }
  }

  function handleKeywordInputPaste(raw: string) {
    if (!raw.includes(",")) {
      setKeywordInput(raw);
      return;
    }
    const parts = raw.split(",");
    parts.slice(0, -1).forEach(addKeywordTag);
    setKeywordInput(parts[parts.length - 1].trimStart());
  }

  // Includes whatever's still sitting in the text box but not yet committed as a tag,
  // so hitting "Run scrape" (or "AI suggest") without pressing Enter/comma first still works.
  function effectiveKeywords(): string[] {
    const pending = keywordInput.trim();
    return pending ? [...keywordTags, pending] : keywordTags;
  }

  // Position (the job title being searched for) is kept as its own field but folded into
  // the single search-query string sent to each job board, since none of the scrapers
  // support separate title/keyword query params — it's placed first as the primary term.
  function combinedSearchQuery(): string {
    return [position.trim(), ...effectiveKeywords()].filter(Boolean).join(" ");
  }

  async function handleScrape(e: FormEvent) {
    e.preventDefault();
    setScraping(true);
    setError(null);
    setScrapeStatus(null);
    try {
      const query = combinedSearchQuery();
      const run = await api.scrape.trigger({
        source,
        keywords: query || undefined,
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

  async function handleSuggestKeywords() {
    setSuggestingKeywords(true);
    setError(null);
    try {
      const result = await api.jobs.suggestKeywords({
        seed: position.trim() || effectiveKeywords().join(" "),
        platform: source || undefined,
        remote_only: remoteOnly,
      });
      setKeywordSuggestions(result.keywords);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Keyword suggestion failed");
    } finally {
      setSuggestingKeywords(false);
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
            <form onSubmit={handleScrape} className="grid grid-cols-2 gap-3 sm:grid-cols-6">
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
                <label className={lLabel}>Position</label>
                <input
                  className={lInput}
                  value={position}
                  onChange={(e) => setPosition(e.target.value)}
                  placeholder="Backend Engineer"
                />
              </div>
              <div>
                <div className="flex items-center justify-between">
                  <label className={lLabel}>Keywords</label>
                  <button
                    type="button"
                    onClick={handleSuggestKeywords}
                    disabled={suggestingKeywords}
                    className="mb-1.5 inline-flex items-center gap-1 text-xs font-medium text-indigo-600 hover:text-indigo-700 disabled:opacity-50"
                  >
                    {suggestingKeywords ? <Spinner className="h-3 w-3" /> : <SparklesIcon />}
                    {suggestingKeywords ? "Thinking…" : "AI suggest"}
                  </button>
                </div>
                <div className={lTagInputWrap}>
                  {keywordTags.map((tag) => (
                    <span
                      key={tag}
                      className="inline-flex items-center gap-1 rounded-full bg-indigo-50 px-2 py-0.5 text-xs font-medium text-indigo-600"
                    >
                      {tag}
                      <button
                        type="button"
                        onClick={() => removeKeywordTag(tag)}
                        className="text-indigo-400 hover:text-indigo-700"
                        aria-label={`Remove ${tag}`}
                      >
                        ×
                      </button>
                    </span>
                  ))}
                  <input
                    className="min-w-[6rem] flex-1 border-none bg-transparent p-0 text-sm text-zinc-900 placeholder:text-zinc-400 focus:outline-none focus:ring-0"
                    value={keywordInput}
                    onChange={(e) => handleKeywordInputPaste(e.target.value)}
                    onKeyDown={handleKeywordInputKeyDown}
                    placeholder={keywordTags.length === 0 ? "backend engineer, remote…" : ""}
                  />
                </div>
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
              {keywordSuggestions.length > 0 && (
                <div className="col-span-2 flex flex-wrap items-center gap-1.5 sm:col-span-6">
                  <span className="text-xs text-zinc-400">Suggestions:</span>
                  {keywordSuggestions.map((k) => (
                    <button
                      key={k}
                      type="button"
                      onClick={() => {
                        addKeywordTag(k);
                        setKeywordSuggestions((prev) => prev.filter((s) => s !== k));
                      }}
                      className="rounded-full bg-indigo-50 px-2.5 py-1 text-xs font-medium text-indigo-600 hover:bg-indigo-100"
                    >
                      + {k}
                    </button>
                  ))}
                </div>
              )}
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
          <div className="flex flex-wrap gap-1.5 border-b border-zinc-200/70 pb-3">
            <button
              onClick={() => setFilterSource("")}
              className={`inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm font-medium transition-colors ${
                filterSource === "" ? "bg-indigo-50 text-indigo-600" : "text-zinc-500 hover:bg-zinc-50 hover:text-zinc-900"
              }`}
            >
              All platforms
            </button>
            {sources.map((s) => (
              <button
                key={s.id}
                onClick={() => setFilterSource(s.name)}
                className={`inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm font-medium capitalize transition-colors ${
                  filterSource === s.name
                    ? "bg-indigo-50 text-indigo-600"
                    : "text-zinc-500 hover:bg-zinc-50 hover:text-zinc-900"
                }`}
              >
                <SourceIcon name={s.name} className="h-4 w-4 text-[9px]" />
                {s.name}
              </button>
            ))}
          </div>
          <div className="flex flex-wrap items-end gap-2">
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

          {selectedIds.size > 0 && (
            <div className="flex items-center gap-3 rounded-lg bg-indigo-50 px-3 py-2 text-sm text-indigo-700">
              <span className="font-medium">{selectedIds.size} selected</span>
              <button
                className="inline-flex items-center gap-1.5 rounded-md bg-white px-2.5 py-1 text-sm font-medium text-red-600 shadow-sm hover:bg-red-50 disabled:opacity-50"
                onClick={() => setConfirmTarget({ kind: "bulk", count: selectedIds.size })}
                disabled={bulkDeleting}
              >
                {bulkDeleting ? <Spinner className="h-3.5 w-3.5" /> : <TrashIcon />}
                {bulkDeleting ? "Deleting…" : "Delete selected"}
              </button>
              <button className="text-indigo-600 hover:underline" onClick={() => setSelectedIds(new Set())}>
                Clear selection
              </button>
            </div>
          )}

          {bulkDeleteNotice && (
            <div className="rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-700">{bulkDeleteNotice}</div>
          )}

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
                    <th className="w-8 px-3 py-2.5">
                      <input
                        type="checkbox"
                        checked={jobs.length > 0 && selectedIds.size === jobs.length}
                        onChange={toggleSelectAll}
                        aria-label="Select all jobs on this page"
                      />
                    </th>
                    <th className="px-3 py-2.5 font-medium">Source</th>
                    <th className="px-3 py-2.5 font-medium">Title</th>
                    <th className="px-3 py-2.5 font-medium">Company</th>
                    <th className="px-3 py-2.5 font-medium">Location</th>
                    <th className="px-3 py-2.5 font-medium">Remote</th>
                    <th className="px-3 py-2.5 font-medium">Posted</th>
                    <th className="px-3 py-2.5 font-medium">Used</th>
                    <th className="px-3 py-2.5 font-medium text-right">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {jobs.map((j) => (
                    <tr
                      key={j.id}
                      className={`border-t border-zinc-100 hover:bg-indigo-50/40 ${
                        selectedIds.has(j.id) ? "bg-indigo-50/60" : ""
                      }`}
                    >
                      <td className="px-3 py-2.5">
                        <input
                          type="checkbox"
                          checked={selectedIds.has(j.id)}
                          onChange={() => toggleSelected(j.id)}
                          aria-label={`Select ${j.title}`}
                        />
                      </td>
                      <td className="whitespace-nowrap px-3 py-2.5">
                        <SourceBadge name={sourceName(j.job_source_id)} />
                      </td>
                      <td className="max-w-xs truncate px-3 py-2.5">
                        <a
                          href={j.apply_url ?? "#"}
                          target="_blank"
                          rel="noreferrer"
                          onClick={() => {
                            if (j.apply_url && !j.is_used) handleToggleUsed(j, true);
                          }}
                          className={`font-medium hover:text-indigo-600 hover:underline ${
                            j.is_used ? "text-zinc-400" : "text-zinc-900"
                          }`}
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
                      <td className="px-3 py-2.5">
                        <Switch
                          checked={j.is_used}
                          onChange={(value) => handleToggleUsed(j, value)}
                          label={`Mark "${j.title}" as ${j.is_used ? "unused" : "used"}`}
                        />
                      </td>
                      <td className="whitespace-nowrap px-3 py-2.5">
                        <div className="flex items-center justify-end gap-1">
                          {j.apply_url ? (
                            <a
                              href={j.apply_url}
                              target="_blank"
                              rel="noreferrer"
                              onClick={() => {
                                if (!j.is_used) handleToggleUsed(j, true);
                              }}
                              title="Open job posting"
                              className="inline-flex h-7 w-7 items-center justify-center rounded-md text-zinc-400 hover:bg-indigo-50 hover:text-indigo-600"
                            >
                              <LinkIcon />
                            </a>
                          ) : (
                            <span
                              className="inline-flex h-7 w-7 items-center justify-center text-zinc-200"
                              title="No URL available"
                            >
                              <LinkIcon />
                            </span>
                          )}
                          <button
                            title="Delete job"
                            onClick={() => setConfirmTarget({ kind: "single", job: j })}
                            disabled={deletingId === j.id}
                            className="inline-flex h-7 w-7 items-center justify-center rounded-md text-zinc-400 hover:bg-red-50 hover:text-red-600 disabled:opacity-50"
                          >
                            {deletingId === j.id ? <Spinner className="h-3.5 w-3.5" /> : <TrashIcon />}
                          </button>
                        </div>
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

      <ConfirmDialog
        open={confirmTarget !== null}
        title={
          confirmTarget?.kind === "single"
            ? `Delete "${confirmTarget.job.title}"?`
            : `Delete ${confirmTarget?.kind === "bulk" ? confirmTarget.count : 0} job(s)?`
        }
        description="This can't be undone."
        confirmLabel="Delete"
        destructive
        loading={confirmTarget?.kind === "single" ? deletingId === confirmTarget.job.id : bulkDeleting}
        onConfirm={() => {
          if (!confirmTarget) return;
          if (confirmTarget.kind === "single") handleDeleteJob(confirmTarget.job);
          else handleBulkDelete();
        }}
        onCancel={() => setConfirmTarget(null)}
      />
    </div>
  );
}
