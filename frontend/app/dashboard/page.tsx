"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";
import Link from "next/link";
import { api, ApiError } from "@/lib/api";
import type { Client } from "@/lib/types";
import { btn, btnSecondary, card, errorText, input, label, sectionTitle } from "@/lib/ui";
import Spinner from "@/components/Spinner";

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
        <div className="space-y-2">
          {clients.map((c) => (
            <Link
              key={c.id}
              href={`/dashboard/clients/${c.id}`}
              className={`${card} flex items-center justify-between gap-3 transition-colors hover:border-indigo-300 hover:shadow-md`}
            >
              <div className="flex min-w-0 items-center gap-3">
                <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-indigo-100 text-xs font-semibold text-indigo-700">
                  {c.full_name.slice(0, 2).toUpperCase()}
                </span>
                <div className="min-w-0">
                  <p className={sectionTitle}>{c.full_name}</p>
                  <p className="truncate text-sm text-zinc-500">
                    {c.email}
                    {c.current_city || c.current_state || c.current_country
                      ? ` · ${[c.current_city, c.current_state, c.current_country].filter(Boolean).join(", ")}`
                      : ""}
                  </p>
                </div>
              </div>
              <span className="shrink-0 rounded-full bg-zinc-100 px-2 py-0.5 text-xs font-medium uppercase tracking-wide text-zinc-500">
                {c.status}
              </span>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
