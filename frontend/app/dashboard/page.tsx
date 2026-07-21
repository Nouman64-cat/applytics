"use client";

import { useEffect, useState, type FormEvent } from "react";
import Link from "next/link";
import { api, ApiError } from "@/lib/api";
import type { Client } from "@/lib/types";
import { btn, card, errorText, input, label, sectionTitle } from "@/lib/ui";

export default function ClientsPage() {
  const [clients, setClients] = useState<Client[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [city, setCity] = useState("");
  const [country, setCountry] = useState("");
  const [submitting, setSubmitting] = useState(false);

  function refresh() {
    api.clients
      .list()
      .then(setClients)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Failed to load clients"));
  }

  useEffect(refresh, []);

  async function handleCreate(e: FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await api.clients.create({
        full_name: fullName,
        email,
        current_city: city || undefined,
        current_country: country || undefined,
      });
      setFullName("");
      setEmail("");
      setCity("");
      setCountry("");
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
        <h1 className="text-xl font-semibold">Clients</h1>
        <button className={btn} onClick={() => setShowForm((v) => !v)}>
          {showForm ? "Cancel" : "New client"}
        </button>
      </div>

      {showForm && (
        <form onSubmit={handleCreate} className={`${card} grid grid-cols-1 gap-4 sm:grid-cols-2`}>
          <div>
            <label className={label}>Full name</label>
            <input className={input} value={fullName} onChange={(e) => setFullName(e.target.value)} required />
          </div>
          <div>
            <label className={label}>Email</label>
            <input
              className={input}
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </div>
          <div>
            <label className={label}>Current city</label>
            <input className={input} value={city} onChange={(e) => setCity(e.target.value)} />
          </div>
          <div>
            <label className={label}>Current country</label>
            <input className={input} value={country} onChange={(e) => setCountry(e.target.value)} />
          </div>
          <div className="sm:col-span-2">
            <button type="submit" className={btn} disabled={submitting}>
              {submitting ? "Creating…" : "Create client"}
            </button>
          </div>
        </form>
      )}

      {error && <p className={errorText}>{error}</p>}

      {clients === null ? (
        <p className="text-sm text-zinc-500">Loading…</p>
      ) : clients.length === 0 ? (
        <p className="text-sm text-zinc-500">No clients yet. Create one to get started.</p>
      ) : (
        <div className="space-y-2">
          {clients.map((c) => (
            <Link
              key={c.id}
              href={`/dashboard/clients/${c.id}`}
              className={`${card} flex items-center justify-between hover:border-zinc-400 dark:hover:border-zinc-600`}
            >
              <div>
                <p className={sectionTitle}>{c.full_name}</p>
                <p className="text-sm text-zinc-500">
                  {c.email}
                  {c.current_city || c.current_country
                    ? ` · ${[c.current_city, c.current_country].filter(Boolean).join(", ")}`
                    : ""}
                </p>
              </div>
              <span className="text-xs uppercase tracking-wide text-zinc-400">{c.status}</span>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
