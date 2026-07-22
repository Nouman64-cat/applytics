"use client";

import { useCallback, useEffect, useState, type FormEvent } from "react";
import { api, ApiError } from "@/lib/api";
import type { Application, ApplicationStatus, Job, Profile } from "@/lib/types";
import { btn, card, errorText, input, label, sectionTitle } from "@/lib/ui";

const STATUSES: ApplicationStatus[] = ["applied", "screening", "interview", "offer", "rejected"];

export default function ApplicationsSection({ clientId, profiles }: { clientId: string; profiles: Profile[] }) {
  const [applications, setApplications] = useState<Application[]>([]);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [profileId, setProfileId] = useState("");
  const [jobId, setJobId] = useState("");
  const [notes, setNotes] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const refreshApplications = useCallback(() => {
    api.applications
      .list(clientId)
      .then(setApplications)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Failed to load applications"));
  }, [clientId]);

  useEffect(() => {
    refreshApplications();
    api.jobs
      .list({ limit: 50 })
      .then(setJobs)
      .catch(() => setJobs([]));
  }, [refreshApplications]);

  async function handleCreate(e: FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await api.applications.create({ client_id: clientId, profile_id: profileId, job_id: jobId, notes: notes || undefined });
      setProfileId("");
      setJobId("");
      setNotes("");
      setShowForm(false);
      refreshApplications();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to log application");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleStatusChange(applicationId: string, status: ApplicationStatus) {
    try {
      await api.applications.update(applicationId, { status });
      refreshApplications();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to update status");
    }
  }

  function jobLabel(id: string): string {
    const job = jobs.find((j) => j.id === id);
    return job ? `${job.title} @ ${job.company ?? "?"}` : id;
  }

  function profileLabel(id: string): string {
    const profile = profiles.find((p) => p.id === id);
    return profile ? `${profile.type} · ${profile.variant_label}` : id;
  }

  return (
    <section className={`${card} space-y-3`}>
      <div className="flex items-center justify-between">
        <h2 className={sectionTitle}>Applications</h2>
        <button
          className="text-sm font-medium text-indigo-600 hover:text-indigo-700"
          onClick={() => setShowForm((v) => !v)}
        >
          {showForm ? "Cancel" : "+ Log application"}
        </button>
      </div>

      {showForm && (
        <form onSubmit={handleCreate} className="grid grid-cols-1 gap-3 sm:grid-cols-3">
          <div>
            <label className={label}>Profile used</label>
            <select className={input} value={profileId} onChange={(e) => setProfileId(e.target.value)} required>
              <option value="">Select…</option>
              {profiles.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.type} · {p.variant_label}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className={label}>Job</label>
            <select className={input} value={jobId} onChange={(e) => setJobId(e.target.value)} required>
              <option value="">Select…</option>
              {jobs.map((j) => (
                <option key={j.id} value={j.id}>
                  {j.title} @ {j.company ?? "?"}
                </option>
              ))}
            </select>
            {jobs.length === 0 && (
              <p className="mt-1 text-xs text-zinc-400">
                No scraped jobs available yet — run a scrape from the Jobs page first.
              </p>
            )}
          </div>
          <div>
            <label className={label}>Notes (optional)</label>
            <input className={input} value={notes} onChange={(e) => setNotes(e.target.value)} />
          </div>
          <div className="sm:col-span-3">
            <button type="submit" className={btn} disabled={submitting || !profileId || !jobId}>
              {submitting ? "Saving…" : "Log application"}
            </button>
          </div>
        </form>
      )}

      {error && <p className={errorText}>{error}</p>}

      {applications.length === 0 ? (
        <p className="text-sm text-zinc-500">No applications logged yet.</p>
      ) : (
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs uppercase text-zinc-400">
              <th className="pb-1">Profile</th>
              <th className="pb-1">Job</th>
              <th className="pb-1">Applied</th>
              <th className="pb-1">Status</th>
            </tr>
          </thead>
          <tbody>
            {applications.map((a) => (
              <tr key={a.id} className="border-t border-zinc-100 hover:bg-zinc-50">
                <td className="py-1.5 pr-2">{profileLabel(a.profile_id)}</td>
                <td className="py-1.5 pr-2">{jobLabel(a.job_id)}</td>
                <td className="py-1.5 pr-2 text-zinc-500">{new Date(a.applied_at).toLocaleDateString()}</td>
                <td className="py-1.5">
                  <select
                    className={`${input} !py-1`}
                    value={a.status}
                    onChange={(e) => handleStatusChange(a.id, e.target.value as ApplicationStatus)}
                  >
                    {STATUSES.map((s) => (
                      <option key={s} value={s}>
                        {s}
                      </option>
                    ))}
                  </select>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}
