"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";
import Link from "next/link";
import { api, ApiError } from "@/lib/api";
import type { Client } from "@/lib/types";
import { btn, btnSecondary, card, errorText, input, label } from "@/lib/ui";
import Spinner from "@/components/Spinner";
import ConfirmDialog from "@/components/ConfirmDialog";

const STATUS_STYLES: Record<string, string> = {
  active: "bg-emerald-50 text-emerald-700",
  placed: "bg-indigo-50 text-indigo-600",
  paused: "bg-amber-50 text-amber-700",
  churned: "bg-zinc-100 text-zinc-500",
};

function MailIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" strokeWidth={1.75} stroke="currentColor" className="h-4 w-4 shrink-0">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M21.75 6.75v10.5a2.25 2.25 0 0 1-2.25 2.25h-15a2.25 2.25 0 0 1-2.25-2.25V6.75m19.5 0A2.25 2.25 0 0 0 19.5 4.5h-15a2.25 2.25 0 0 0-2.25 2.25m19.5 0v.243a2.25 2.25 0 0 1-1.07 1.916l-7.5 4.615a2.25 2.25 0 0 1-2.36 0L3.32 8.91a2.25 2.25 0 0 1-1.07-1.916V6.75"
      />
    </svg>
  );
}

function MapPinIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" strokeWidth={1.75} stroke="currentColor" className="h-4 w-4 shrink-0">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M15 10.5a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z"
      />
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M19.5 10.5c0 7.142-7.5 11.25-7.5 11.25S4.5 17.642 4.5 10.5a7.5 7.5 0 1 1 15 0Z"
      />
    </svg>
  );
}

function CalendarIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" strokeWidth={1.75} stroke="currentColor" className="h-3.5 w-3.5 shrink-0">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M6.75 3v2.25M17.25 3v2.25M3 18.75V7.5a2.25 2.25 0 0 1 2.25-2.25h13.5A2.25 2.25 0 0 1 21 7.5v11.25m-18 0A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75m-18 0V11.25A2.25 2.25 0 0 1 5.25 9h13.5a2.25 2.25 0 0 1 2.25 2.25v7.5"
      />
    </svg>
  );
}

function ArrowRightIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" strokeWidth={2} stroke="currentColor" className="h-3.5 w-3.5 shrink-0">
      <path strokeLinecap="round" strokeLinejoin="round" d="M17.25 8.25 21 12m0 0-3.75 3.75M21 12H3" />
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

export default function ClientsPage() {
  const [clients, setClients] = useState<Client[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [city, setCity] = useState("");
  const [state, setState] = useState("");
  const [country, setCountry] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const [extracting, setExtracting] = useState(false);
  const [extractedText, setExtractedText] = useState<string | null>(null);
  const [extractedFileName, setExtractedFileName] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [pendingDelete, setPendingDelete] = useState<Client | null>(null);
  const [deleting, setDeleting] = useState(false);

  function refresh() {
    api.clients
      .list()
      .then(setClients)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Failed to load clients"));
  }

  useEffect(refresh, []);

  async function handleResumeUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setExtracting(true);
    setError(null);
    try {
      const result = await api.clients.extractResume(file);
      if (result.full_name) setFullName(result.full_name);
      if (result.email) setEmail(result.email);
      if (result.current_city) setCity(result.current_city);
      if (result.current_state) setState(result.current_state);
      if (result.current_country) setCountry(result.current_country);
      setExtractedText(result.raw_text);
      setExtractedFileName(file.name);
      setShowForm(true);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Resume extraction failed");
    } finally {
      setExtracting(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  }

  async function handleCreate(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const newClient = await api.clients.create({
        full_name: fullName,
        email,
        current_city: city || undefined,
        current_state: state || undefined,
        current_country: country || undefined,
      });

      if (extractedText) {
        await api.profiles.create({
          client_id: newClient.id,
          type: "resume",
          variant_label: "A",
          raw_text: extractedText,
        });
      }

      setFullName("");
      setEmail("");
      setCity("");
      setState("");
      setCountry("");
      setExtractedText(null);
      setExtractedFileName(null);
      setShowForm(false);
      refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to create client");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDelete() {
    if (!pendingDelete) return;
    setDeleting(true);
    setError(null);
    try {
      await api.clients.delete(pendingDelete.id);
      setPendingDelete(null);
      refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to delete client");
    } finally {
      setDeleting(false);
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold tracking-tight text-zinc-900">Clients</h1>
          <p className="text-sm text-zinc-500">Manage the candidates you're representing.</p>
        </div>
        <button className={btn} onClick={() => setShowForm((v) => !v)}>
          {showForm ? "Cancel" : "+ New client"}
        </button>
      </div>

      {showForm && (
        <div className={`${card} space-y-4`}>
          <div className="rounded-xl border border-dashed border-zinc-300 bg-zinc-50/50 p-4">
            <label className={label}>Upload resume to auto-fill (PDF, image, or DOCX — uses Gemini OCR)</label>
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,.png,.jpg,.jpeg,.docx,.txt"
              className={input}
              onChange={handleResumeUpload}
              disabled={extracting}
            />
            {extractedFileName && !extracting && (
              <p className="mt-1.5 text-xs text-emerald-600">
                Extracted from {extractedFileName} — a resume profile will be created automatically with this client.
              </p>
            )}
          </div>

          {extracting && (
            <div className="flex items-center gap-3 rounded-lg bg-indigo-50 p-3 text-sm font-medium text-indigo-700">
              <Spinner className="h-5 w-5" />
              <span>Processing resume with AI — this can take up to 15 seconds. The fields below will fill in automatically.</span>
            </div>
          )}

          <form
            onSubmit={handleCreate}
            className={`grid grid-cols-1 gap-4 sm:grid-cols-2 ${extracting ? "pointer-events-none opacity-50" : ""}`}
          >
            <div>
              <label className={label}>Full name</label>
              <input
                className={input}
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                required
                disabled={extracting}
              />
            </div>
            <div>
              <label className={label}>Email</label>
              <input
                className={input}
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                disabled={extracting}
              />
            </div>
            <div>
              <label className={label}>Current city</label>
              <input className={input} value={city} onChange={(e) => setCity(e.target.value)} disabled={extracting} />
            </div>
            <div>
              <label className={label}>Current state</label>
              <input
                className={input}
                value={state}
                onChange={(e) => setState(e.target.value)}
                disabled={extracting}
              />
            </div>
            <div>
              <label className={label}>Current country</label>
              <input
                className={input}
                value={country}
                onChange={(e) => setCountry(e.target.value)}
                disabled={extracting}
              />
            </div>
            <div className="flex items-end gap-2 sm:col-span-2">
              <button type="submit" className={`${btn} gap-2`} disabled={submitting || extracting}>
                {submitting && <Spinner />}
                {submitting ? "Creating…" : "Create client"}
              </button>
              {extractedText && (
                <button
                  type="button"
                  className={btnSecondary}
                  onClick={() => {
                    setExtractedText(null);
                    setExtractedFileName(null);
                  }}
                >
                  Discard extracted resume
                </button>
              )}
            </div>
          </form>
        </div>
      )}

      {error && <p className={errorText}>{error}</p>}

      {clients === null ? (
        <div className="flex items-center gap-2 py-8 text-sm text-zinc-500">
          <Spinner className="h-4 w-4" />
          Loading…
        </div>
      ) : clients.length === 0 ? (
        <p className="py-8 text-center text-sm text-zinc-500">No clients yet. Create one to get started.</p>
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {clients.map((c) => (
            <Link
              key={c.id}
              href={`/dashboard/clients/${c.id}`}
              className={`${card} group flex flex-col gap-3 transition-all hover:-translate-y-0.5 hover:border-indigo-300 hover:shadow-md`}
            >
              <div className="flex items-start justify-between gap-2">
                <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-indigo-500 to-indigo-600 text-sm font-semibold text-white shadow-sm">
                  {c.full_name.slice(0, 2).toUpperCase()}
                </span>
                <div className="flex shrink-0 items-center gap-1.5">
                  <span
                    className={`rounded-full px-2 py-0.5 text-xs font-medium uppercase tracking-wide ${
                      STATUS_STYLES[c.status] ?? STATUS_STYLES.active
                    }`}
                  >
                    {c.status}
                  </span>
                  <button
                    onClick={(e) => {
                      e.preventDefault();
                      e.stopPropagation();
                      setPendingDelete(c);
                    }}
                    title="Delete client"
                    className="rounded-lg p-1 text-zinc-300 opacity-0 transition-colors hover:bg-red-50 hover:text-red-600 group-hover:opacity-100"
                  >
                    <TrashIcon />
                  </button>
                </div>
              </div>

              <p className="truncate text-base font-semibold text-zinc-900">{c.full_name}</p>

              <div className="space-y-1.5 text-sm text-zinc-500">
                <div className="flex items-center gap-2">
                  <MailIcon />
                  <span className="truncate">{c.email}</span>
                </div>
                {(c.current_city || c.current_state || c.current_country) && (
                  <div className="flex items-center gap-2">
                    <MapPinIcon />
                    <span className="truncate">
                      {[c.current_city, c.current_state, c.current_country].filter(Boolean).join(", ")}
                    </span>
                  </div>
                )}
              </div>

              <div className="mt-1 flex items-center justify-between border-t border-zinc-100 pt-2.5 text-xs text-zinc-400">
                <span className="flex items-center gap-1">
                  <CalendarIcon />
                  Added {new Date(c.created_at).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" })}
                </span>
                <span className="flex items-center gap-1 font-medium text-indigo-600 opacity-0 transition-opacity group-hover:opacity-100">
                  View
                  <ArrowRightIcon />
                </span>
              </div>
            </Link>
          ))}
        </div>
      )}

      <ConfirmDialog
        open={pendingDelete !== null}
        title={`Delete ${pendingDelete?.full_name ?? "this client"}?`}
        description="This permanently removes the client along with their target roles, profiles, applications, and analysis history. This can't be undone."
        confirmLabel="Delete"
        destructive
        loading={deleting}
        onConfirm={handleDelete}
        onCancel={() => setPendingDelete(null)}
      />
    </div>
  );
}
