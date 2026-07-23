"use client";

import { useEffect, useRef, useState, type DragEvent, type FormEvent } from "react";
import { api, ApiError } from "@/lib/api";
import type { KeywordAnalysis, Profile, TargetRole } from "@/lib/types";
import { btn, btnSecondary, card, errorText, input, label, sectionTitle } from "@/lib/ui";
import Spinner from "@/components/Spinner";

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function UploadIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" strokeWidth={1.5} stroke="currentColor" className="h-7 w-7 shrink-0">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M3 16.5v2.25A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75V16.5M16.5 8.25 12 3.75m0 0L7.5 8.25M12 3.75v12.75"
      />
    </svg>
  );
}

function TrashIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" strokeWidth={1.75} stroke="currentColor" className="h-4 w-4 shrink-0">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="m14.74 9-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 0 1-2.244 2.077H8.084a2.25 2.25 0 0 1-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 0 0-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 0 1 3.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 0 0-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 0 0-7.5 0"
      />
    </svg>
  );
}

function ResumeIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" strokeWidth={1.5} stroke="currentColor" className="h-5 w-5 shrink-0">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z"
      />
    </svg>
  );
}

function CloseIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" strokeWidth={1.5} stroke="currentColor" className="h-5 w-5 shrink-0">
      <path strokeLinecap="round" strokeLinejoin="round" d="M6 18 18 6M6 6l12 12" />
    </svg>
  );
}

function ProfilePreviewModal({
  profile,
  targetRoleTitle,
  onClose,
}: {
  profile: Profile;
  targetRoleTitle: string | null;
  onClose: () => void;
}) {
  useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [onClose]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" role="dialog" aria-modal="true">
      <div className="absolute inset-0 bg-zinc-900/40 backdrop-blur-sm" onClick={onClose} />
      <div className="relative flex max-h-[85vh] w-full max-w-2xl flex-col overflow-hidden rounded-2xl border border-zinc-200/70 bg-white shadow-xl">
        <div className="flex shrink-0 items-start justify-between gap-3 border-b border-zinc-100 px-5 py-4">
          <div className="min-w-0">
            <h2 className="text-sm font-semibold text-zinc-900">Variant {profile.variant_label}</h2>
            {targetRoleTitle && <p className="mt-1 text-xs text-zinc-500">Target role: {targetRoleTitle}</p>}
          </div>
          <button
            onClick={onClose}
            className="shrink-0 rounded-lg p-1.5 text-zinc-400 hover:bg-zinc-100 hover:text-zinc-600"
          >
            <CloseIcon />
          </button>
        </div>
        <div className="overflow-y-auto px-5 py-4">
          {profile.raw_text ? (
            <pre className="whitespace-pre-wrap font-sans text-sm leading-relaxed text-zinc-700">
              {profile.raw_text}
            </pre>
          ) : (
            <p className="text-sm text-zinc-400">No resume text on file.</p>
          )}
        </div>
      </div>
    </div>
  );
}

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
  const [variantLabel, setVariantLabel] = useState("");
  const [targetRoleId, setTargetRoleId] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [keywordResults, setKeywordResults] = useState<Record<string, KeywordAnalysis>>({});
  const [analyzing, setAnalyzing] = useState<string | null>(null);
  const [previewProfile, setPreviewProfile] = useState<Profile | null>(null);

  const targetRoleById = new Map(targetRoles.map((tr) => [tr.id, tr]));
  const resumeProfiles = profiles.filter((p) => p.type === "resume");

  function handleDrop(e: DragEvent<HTMLDivElement>) {
    e.preventDefault();
    setIsDragging(false);
    const dropped = e.dataTransfer.files?.[0];
    if (dropped) setFile(dropped);
  }

  async function handleCreate(e: FormEvent) {
    e.preventDefault();
    if (!file) return;
    setSubmitting(true);
    setError(null);
    try {
      const formData = new FormData();
      formData.append("client_id", clientId);
      formData.append("variant_label", variantLabel);
      if (targetRoleId) formData.append("target_role_id", targetRoleId);
      formData.append("file", file);
      await api.profiles.upload(formData);
      setVariantLabel("");
      setTargetRoleId("");
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
    <section className={`${card} space-y-4`}>
      <div className="flex items-center justify-between">
        <h2 className={sectionTitle}>Profiles (resume variants)</h2>
        <button className={showForm ? btnSecondary : btn} onClick={() => setShowForm((v) => !v)}>
          {showForm ? "Cancel" : "+ Add profile"}
        </button>
      </div>

      {showForm && (
        <form onSubmit={handleCreate} className="space-y-4 rounded-xl border border-zinc-200/70 bg-zinc-50/60 p-4">
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
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
            <label className={label}>Resume file</label>
            <div
              onClick={() => fileInputRef.current?.click()}
              onDragOver={(e) => {
                e.preventDefault();
                setIsDragging(true);
              }}
              onDragLeave={() => setIsDragging(false)}
              onDrop={handleDrop}
              className={`flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed px-4 py-8 text-center transition-colors ${
                isDragging
                  ? "border-indigo-400 bg-indigo-50/60"
                  : "border-zinc-300 bg-white hover:border-indigo-300 hover:bg-indigo-50/30"
              }`}
            >
              {file ? (
                <div className="flex w-full max-w-sm items-center gap-3 rounded-lg border border-zinc-200 bg-zinc-50 px-3 py-2.5 text-left">
                  <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-indigo-50 text-indigo-600">
                    <ResumeIcon />
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium text-zinc-900" title={file.name}>
                      {file.name}
                    </p>
                    <p className="text-xs text-zinc-400">{formatSize(file.size)}</p>
                  </div>
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      setFile(null);
                      if (fileInputRef.current) fileInputRef.current.value = "";
                    }}
                    title="Remove file"
                    className="shrink-0 rounded-lg p-1.5 text-zinc-400 hover:bg-red-50 hover:text-red-600"
                  >
                    <TrashIcon />
                  </button>
                </div>
              ) : (
                <>
                  <div className="flex h-11 w-11 items-center justify-center rounded-full bg-indigo-50 text-indigo-500">
                    <UploadIcon />
                  </div>
                  <p className="mt-3 text-sm font-medium text-zinc-700">
                    <span className="text-indigo-600">Click to upload</span> or drag and drop
                  </p>
                  <p className="mt-1 text-xs text-zinc-400">PDF, DOCX, or TXT</p>
                </>
              )}
              <input
                ref={fileInputRef}
                type="file"
                className="hidden"
                accept=".pdf,.docx,.txt"
                onChange={(e) => setFile(e.target.files?.[0] ?? null)}
              />
            </div>
          </div>

          <button type="submit" className={`${btn} gap-2`} disabled={submitting || !file}>
            {submitting && <Spinner />}
            {submitting ? "Saving…" : "Save profile"}
          </button>
        </form>
      )}

      {error && <p className={errorText}>{error}</p>}

      {resumeProfiles.length === 0 ? (
        <p className="py-4 text-center text-sm text-zinc-500">No profiles yet.</p>
      ) : (
        <ul className="grid grid-cols-1 gap-3 lg:grid-cols-2">
          {resumeProfiles.map((p) => {
            const result = keywordResults[p.id];
            const roleTitle = p.target_role_id ? targetRoleById.get(p.target_role_id)?.title ?? null : null;
            const hasContent = !!p.raw_text;
            return (
              <li key={p.id} className="flex flex-col gap-3 rounded-xl border border-zinc-200/70 p-4">
                <div className="flex items-start gap-3">
                  <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-indigo-50 text-indigo-600">
                    <ResumeIcon />
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-1.5">
                      <span className="text-sm font-semibold text-zinc-900">Variant {p.variant_label}</span>
                      {!p.is_active && (
                        <span className="rounded-full bg-zinc-100 px-1.5 py-0.5 text-[11px] font-medium text-zinc-400">
                          Inactive
                        </span>
                      )}
                    </div>
                    <div className="mt-1 flex flex-wrap items-center gap-x-1.5 gap-y-0.5 text-xs text-zinc-500">
                      {roleTitle && <span className="truncate">{roleTitle}</span>}
                      <span>{roleTitle ? `· ${formatDate(p.created_at)}` : formatDate(p.created_at)}</span>
                    </div>
                  </div>
                </div>

                <div className="rounded-lg bg-zinc-50 px-3 py-2.5 text-xs leading-relaxed text-zinc-500">
                  {hasContent ? (
                    <p className="line-clamp-3 whitespace-pre-wrap break-words">{p.raw_text}</p>
                  ) : (
                    <p className="italic text-zinc-400">No content on file</p>
                  )}
                </div>

                <div className="flex flex-wrap items-center gap-2">
                  {hasContent && (
                    <button className={btnSecondary} onClick={() => setPreviewProfile(p)}>
                      Preview
                    </button>
                  )}
                  <button
                    className={`${btnSecondary} gap-2`}
                    onClick={() => handleAnalyzeKeywords(p)}
                    disabled={analyzing === p.id}
                  >
                    {analyzing === p.id && <Spinner />}
                    {analyzing === p.id ? "Analyzing…" : "Analyze keywords"}
                  </button>
                </div>

                {analyzing === p.id && (
                  <div className="flex items-center gap-2 rounded-lg bg-indigo-50 p-2 text-xs text-indigo-700">
                    <Spinner className="h-3.5 w-3.5" />
                    Analyzing keyword strength against the target role…
                  </div>
                )}
                {result && analyzing !== p.id && (
                  <div className="rounded-lg bg-zinc-50 p-2.5 text-xs text-zinc-600">
                    <p>
                      ATS score: <strong className="text-zinc-900">{result.ats_score}</strong> · Recruiter attention:{" "}
                      <strong className="text-zinc-900">{result.recruiter_attention_score}</strong>
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

      {previewProfile && (
        <ProfilePreviewModal
          profile={previewProfile}
          targetRoleTitle={
            previewProfile.target_role_id ? targetRoleById.get(previewProfile.target_role_id)?.title ?? null : null
          }
          onClose={() => setPreviewProfile(null)}
        />
      )}
    </section>
  );
}
