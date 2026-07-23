"use client";

import { useCallback, useEffect, useState, type FormEvent } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api, ApiError } from "@/lib/api";
import type { Client, Profile, TargetRole } from "@/lib/types";
import { btn, btnSecondary, card, errorText, input, label } from "@/lib/ui";
import Spinner from "@/components/Spinner";
import ConfirmDialog from "@/components/ConfirmDialog";
import TargetRolesSection from "@/components/TargetRolesSection";
import DocumentsSection from "@/components/DocumentsSection";
import ProfilesSection from "@/components/ProfilesSection";
import AnalysisSection from "@/components/AnalysisSection";

const STATUS_OPTIONS = ["active", "paused", "placed", "churned"] as const;

export default function ClientDetail({ clientId }: { clientId: string }) {
  const router = useRouter();
  const [client, setClient] = useState<Client | null>(null);
  const [targetRoles, setTargetRoles] = useState<TargetRole[]>([]);
  const [profiles, setProfiles] = useState<Profile[]>([]);
  const [error, setError] = useState<string | null>(null);

  const [editing, setEditing] = useState(false);
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [city, setCity] = useState("");
  const [state, setState] = useState("");
  const [country, setCountry] = useState("");
  const [status, setStatus] = useState<(typeof STATUS_OPTIONS)[number]>("active");
  const [saving, setSaving] = useState(false);

  const [confirmingDelete, setConfirmingDelete] = useState(false);
  const [deleting, setDeleting] = useState(false);

  const refreshClient = useCallback(() => {
    api.clients.get(clientId).then(setClient).catch((err) => setError(errMsg(err)));
  }, [clientId]);

  const refreshTargetRoles = useCallback(() => {
    api.clients
      .listTargetRoles(clientId)
      .then(setTargetRoles)
      .catch((err) => setError(errMsg(err)));
  }, [clientId]);

  const refreshProfiles = useCallback(() => {
    api.profiles
      .list(clientId)
      .then(setProfiles)
      .catch((err) => setError(errMsg(err)));
  }, [clientId]);

  useEffect(() => {
    refreshClient();
    refreshTargetRoles();
    refreshProfiles();
  }, [refreshClient, refreshTargetRoles, refreshProfiles]);

  function startEditing() {
    if (!client) return;
    setFullName(client.full_name);
    setEmail(client.email);
    setCity(client.current_city ?? "");
    setState(client.current_state ?? "");
    setCountry(client.current_country ?? "");
    setStatus(client.status as (typeof STATUS_OPTIONS)[number]);
    setEditing(true);
  }

  async function handleSave(e: FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      await api.clients.update(clientId, {
        full_name: fullName,
        email,
        current_city: city || null,
        current_state: state || null,
        current_country: country || null,
        status,
      });
      setEditing(false);
      refreshClient();
    } catch (err) {
      setError(errMsg(err));
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete() {
    setDeleting(true);
    setError(null);
    try {
      await api.clients.delete(clientId);
      router.push("/dashboard");
    } catch (err) {
      setError(errMsg(err));
      setDeleting(false);
    }
  }

  if (error) return <p className={errorText}>{error}</p>;
  if (!client) return <p className="text-sm text-zinc-500">Loading…</p>;

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <Link href="/dashboard" className="text-sm font-medium text-zinc-500 hover:text-indigo-600">
            ← All clients
          </Link>
          <h1 className="mt-1 text-xl font-semibold tracking-tight text-zinc-900">{client.full_name}</h1>
          <p className="text-sm text-zinc-500">
            {client.email}
            {client.current_city || client.current_state || client.current_country
              ? ` · ${[client.current_city, client.current_state, client.current_country].filter(Boolean).join(", ")}`
              : ""}{" "}
            · {client.status}
          </p>
        </div>
        {!editing && (
          <div className="flex shrink-0 gap-2">
            <button className={btnSecondary} onClick={startEditing}>
              Edit
            </button>
            <button
              className="inline-flex items-center justify-center rounded-lg border border-red-200 bg-white px-3.5 py-2 text-sm font-medium text-red-600 shadow-sm hover:bg-red-50 transition-colors"
              onClick={() => setConfirmingDelete(true)}
            >
              Delete
            </button>
          </div>
        )}
      </div>

      {editing && (
        <form onSubmit={handleSave} className={`${card} grid grid-cols-1 gap-4 sm:grid-cols-2`}>
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
            <label className={label}>Current state</label>
            <input className={input} value={state} onChange={(e) => setState(e.target.value)} />
          </div>
          <div>
            <label className={label}>Current country</label>
            <input className={input} value={country} onChange={(e) => setCountry(e.target.value)} />
          </div>
          <div>
            <label className={label}>Status</label>
            <select
              className={input}
              value={status}
              onChange={(e) => setStatus(e.target.value as (typeof STATUS_OPTIONS)[number])}
            >
              {STATUS_OPTIONS.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </div>
          <div className="flex items-center gap-2 sm:col-span-2">
            <button type="submit" className={`${btn} gap-2`} disabled={saving}>
              {saving && <Spinner />}
              {saving ? "Saving…" : "Save changes"}
            </button>
            <button type="button" className={btnSecondary} onClick={() => setEditing(false)} disabled={saving}>
              Cancel
            </button>
          </div>
        </form>
      )}

      <ConfirmDialog
        open={confirmingDelete}
        title={`Delete ${client.full_name}?`}
        description="This permanently removes the client along with their target roles, profiles, applications, and analysis history. This can't be undone."
        confirmLabel="Delete"
        destructive
        loading={deleting}
        onConfirm={handleDelete}
        onCancel={() => setConfirmingDelete(false)}
      />

      <TargetRolesSection clientId={clientId} targetRoles={targetRoles} onChanged={refreshTargetRoles} />

      <DocumentsSection clientId={clientId} />

      <ProfilesSection
        clientId={clientId}
        targetRoles={targetRoles}
        profiles={profiles}
        onChanged={refreshProfiles}
      />

      <AnalysisSection clientId={clientId} targetRoles={targetRoles} profiles={profiles} />
    </div>
  );
}

function errMsg(err: unknown): string {
  return err instanceof ApiError ? err.message : "Something went wrong";
}
