"use client";

import { useState, type FormEvent } from "react";
import { api, ApiError } from "@/lib/api";
import type { KeywordAnalysis, Profile, ProfileType, TargetRole } from "@/lib/types";
import { badge, btn, btnSecondary, card, errorText, input, label, sectionTitle } from "@/lib/ui";
import Spinner from "@/components/Spinner";

export default function ProfilesSection({
  clientId,
  targetRoles,
  profiles,
  onChanged,
}: {
  clientId: string;
  targetRoles: TargetRole[];
  profiles: Profile[];
  onChanged: () => void;
}) {
  const [showForm, setShowForm] = useState(false);
  const [type, setType] = useState<ProfileType>("resume");
  const [variantLabel, setVariantLabel] = useState("");
  const [targetRoleId, setTargetRoleId] = useState("");
  const [rawText, setRawText] = useState("");
  const [sourceUrl, setSourceUrl] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const [keywordResults, setKeywordResults] = useState<Record<string, KeywordAnalysis>>({});
  const [analyzing, setAnalyzing] = useState<string | null>(null);

  async function handleCreate(e: FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      if (file) {
        const formData = new FormData();
        formData.append("client_id", clientId);
        formData.append("variant_label", variantLabel);
        if (targetRoleId) formData.append("target_role_id", targetRoleId);
        formData.append("file", file);
        await api.profiles.upload(formData);
      } else {
        await api.profiles.create({
          client_id: clientId,
          target_role_id: targetRoleId || undefined,
          type,
          variant_label: variantLabel,
          source_url: type === "linkedin" ? sourceUrl || undefined : undefined,
          raw_text: type === "resume" ? rawText || undefined : undefined,
        });
      }
      setVariantLabel("");
      setTargetRoleId("");
      setRawText("");
      setSourceUrl("");
      setFile(null);
      setShowForm(false);
      onChanged();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to create profile");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleAnalyzeKeywords(profile: Profile) {
    setAnalyzing(profile.id);
    setError(null);
    try {
      const result = await api.analysis.keywords(profile.id, profile.target_role_id);
      setKeywordResults((prev) => ({ ...prev, [profile.id]: result }));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Keyword analysis failed");
    } finally {
      setAnalyzing(null);
    }
  }

  return (
    <section className={`${card} space-y-3`}>
      <div className="flex items-center justify-between">
        <h2 className={sectionTitle}>Profiles (resume / LinkedIn variants)</h2>
        <button className="text-sm text-zinc-500 hover:underline" onClick={() => setShowForm((v) => !v)}>
          {showForm ? "Cancel" : "+ Add profile"}
        </button>
      </div>

      {showForm && (
        <form onSubmit={handleCreate} className="space-y-3">
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            <div>
              <label className={label}>Type</label>
              <select
                className={input}
                value={type}
                onChange={(e) => setType(e.target.value as ProfileType)}
                disabled={!!file}
              >
                <option value="resume">Resume</option>
                <option value="linkedin">LinkedIn</option>
              </select>
            </div>
            <div>
              <label className={label}>Variant label</label>
              <input
                className={input}
                placeholder="e.g. A, B, v2"
                value={variantLabel}
                onChange={(e) => setVariantLabel(e.target.value)}
                required
              />
            </div>
            <div>
              <label className={label}>Target role (optional)</label>
              <select className={input} value={targetRoleId} onChange={(e) => setTargetRoleId(e.target.value)}>
                <option value="">None</option>
                {targetRoles.map((tr) => (
                  <option key={tr.id} value={tr.id}>
                    {tr.title}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div>
            <label className={label}>Upload resume file (PDF / DOCX / txt) — or fill in text below instead</label>
            <input
              className={input}
              type="file"
              accept=".pdf,.docx,.txt"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            />
          </div>

          {!file && type === "resume" && (
            <div>
              <label className={label}>Resume text</label>
              <textarea
                className={`${input} min-h-24`}
                value={rawText}
                onChange={(e) => setRawText(e.target.value)}
              />
            </div>
          )}
          {!file && type === "linkedin" && (
            <div>
              <label className={label}>LinkedIn URL</label>
              <input className={input} value={sourceUrl} onChange={(e) => setSourceUrl(e.target.value)} />
            </div>
          )}

          <button type="submit" className={`${btn} gap-2`} disabled={submitting}>
            {submitting && <Spinner />}
            {submitting ? "Saving…" : "Save profile"}
          </button>
        </form>
      )}

      {error && <p className={errorText}>{error}</p>}

      {profiles.length === 0 ? (
        <p className="text-sm text-zinc-500">No profiles yet.</p>
      ) : (
        <ul className="space-y-3">
          {profiles.map((p) => {
            const result = keywordResults[p.id];
            return (
              <li key={p.id} className="rounded-md border border-zinc-200 p-3 dark:border-zinc-800">
                <div className="flex items-center justify-between">
                  <div>
                    <span className={badge}>{p.type}</span>{" "}
                    <span className="text-sm font-medium">variant {p.variant_label}</span>
                    {!p.is_active && <span className="ml-2 text-xs text-zinc-400">(inactive)</span>}
                  </div>
                  <button
                    className={`${btnSecondary} gap-2`}
                    onClick={() => handleAnalyzeKeywords(p)}
                    disabled={analyzing === p.id}
                  >
                    {analyzing === p.id && <Spinner />}
                    {analyzing === p.id ? "Analyzing…" : "Analyze keywords"}
                  </button>
                </div>
                <p className="mt-1 line-clamp-2 text-xs text-zinc-500">
                  {p.raw_text || p.source_url || "(no content)"}
                </p>
                {analyzing === p.id && (
                  <div className="mt-2 flex items-center gap-2 rounded bg-zinc-50 p-2 text-xs text-zinc-500 dark:bg-zinc-800/50">
                    <Spinner className="h-3.5 w-3.5" />
                    Analyzing keyword strength against the target role…
                  </div>
                )}
                {result && analyzing !== p.id && (
                  <div className="mt-2 rounded bg-zinc-50 p-2 text-xs dark:bg-zinc-800/50">
                    <p>
                      ATS score: <strong>{result.ats_score}</strong> · Recruiter attention:{" "}
                      <strong>{result.recruiter_attention_score}</strong>
                    </p>
                    {result.missing_keywords.length > 0 && (
                      <p className="mt-1">Missing: {result.missing_keywords.join(", ")}</p>
                    )}
                  </div>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}
