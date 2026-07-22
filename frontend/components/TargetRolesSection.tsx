"use client";

import { useState, type FormEvent } from "react";
import { api, ApiError } from "@/lib/api";
import type { TargetRole } from "@/lib/types";
import { badge, btn, card, errorText, input, label, sectionTitle } from "@/lib/ui";

export default function TargetRolesSection({
  clientId,
  targetRoles,
  onChanged,
}: {
  clientId: string;
  targetRoles: TargetRole[];
  onChanged: () => void;
}) {
  const [showForm, setShowForm] = useState(false);
  const [title, setTitle] = useState("");
  const [seniority, setSeniority] = useState("");
  const [keywords, setKeywords] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleCreate(e: FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await api.clients.createTargetRole(clientId, {
        title,
        seniority: seniority || undefined,
        must_have_keywords: keywords
          .split(",")
          .map((k) => k.trim())
          .filter(Boolean),
      });
      setTitle("");
      setSeniority("");
      setKeywords("");
      setShowForm(false);
      onChanged();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to create target role");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section className={`${card} space-y-3`}>
      <div className="flex items-center justify-between">
        <h2 className={sectionTitle}>Target roles</h2>
        <button
          className="text-sm font-medium text-indigo-600 hover:text-indigo-700"
          onClick={() => setShowForm((v) => !v)}
        >
          {showForm ? "Cancel" : "+ Add target role"}
        </button>
      </div>

      {showForm && (
        <form onSubmit={handleCreate} className="grid grid-cols-1 gap-3 sm:grid-cols-3">
          <div>
            <label className={label}>Title</label>
            <input className={input} value={title} onChange={(e) => setTitle(e.target.value)} required />
          </div>
          <div>
            <label className={label}>Seniority</label>
            <input className={input} value={seniority} onChange={(e) => setSeniority(e.target.value)} />
          </div>
          <div>
            <label className={label}>Must-have keywords (comma separated)</label>
            <input className={input} value={keywords} onChange={(e) => setKeywords(e.target.value)} />
          </div>
          <div className="sm:col-span-3">
            <button type="submit" className={btn} disabled={submitting}>
              {submitting ? "Saving…" : "Save target role"}
            </button>
          </div>
        </form>
      )}

      {error && <p className={errorText}>{error}</p>}

      {targetRoles.length === 0 ? (
        <p className="text-sm text-zinc-500">No target roles yet.</p>
      ) : (
        <ul className="space-y-2">
          {targetRoles.map((tr) => (
            <li key={tr.id} className="text-sm">
              <span className="font-medium">{tr.title}</span>
              {tr.seniority && <span className="text-zinc-500"> · {tr.seniority}</span>}
              {tr.must_have_keywords.length > 0 && (
                <div className="mt-1 flex flex-wrap gap-1">
                  {tr.must_have_keywords.map((k) => (
                    <span key={k} className={badge}>
                      {k}
                    </span>
                  ))}
                </div>
              )}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
