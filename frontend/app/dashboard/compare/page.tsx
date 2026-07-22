"use client";

import { useEffect, useState } from "react";
import { api, ApiError } from "@/lib/api";
import type { Client, ComparisonRun, Profile } from "@/lib/types";
import { btn, card, errorText, input, label, sectionTitle } from "@/lib/ui";
import Spinner from "@/components/Spinner";
import ComparisonResultView from "@/components/ComparisonResultView";

function ClientResumePicker({
  title,
  clients,
  selectedClientId,
  onSelectClient,
  selectedProfileId,
  onSelectProfile,
  disabled,
}: {
  title: string;
  clients: Client[];
  selectedClientId: string;
  onSelectClient: (id: string) => void;
  selectedProfileId: string;
  onSelectProfile: (id: string) => void;
  disabled: boolean;
}) {
  const [profiles, setProfiles] = useState<Profile[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!selectedClientId) {
      setProfiles([]);
      return;
    }
    setLoading(true);
    api.profiles
      .list(selectedClientId)
      .then((all) => setProfiles(all.filter((p) => p.type === "resume")))
      .finally(() => setLoading(false));
  }, [selectedClientId]);

  return (
    <div className={`${card} space-y-3`}>
      <h3 className={sectionTitle}>{title}</h3>
      <div>
        <label className={label}>Client</label>
        <select
          className={input}
          value={selectedClientId}
          onChange={(e) => {
            onSelectClient(e.target.value);
            onSelectProfile("");
          }}
          disabled={disabled}
        >
          <option value="">Select a client…</option>
          {clients.map((c) => (
            <option key={c.id} value={c.id}>
              {c.full_name}
            </option>
          ))}
        </select>
      </div>
      <div>
        <label className={label}>Resume</label>
        <select
          className={input}
          value={selectedProfileId}
          onChange={(e) => onSelectProfile(e.target.value)}
          disabled={disabled || !selectedClientId || loading}
        >
          <option value="">{loading ? "Loading…" : "Select a resume…"}</option>
          {profiles.map((p) => (
            <option key={p.id} value={p.id}>
              Variant {p.variant_label}
            </option>
          ))}
        </select>
        {selectedClientId && !loading && profiles.length === 0 && (
          <p className="mt-1 text-xs text-zinc-500">This client has no resume profiles yet.</p>
        )}
      </div>
    </div>
  );
}

export default function CompareClientsPage() {
  const [clients, setClients] = useState<Client[]>([]);
  const [clientAId, setClientAId] = useState("");
  const [profileAId, setProfileAId] = useState("");
  const [clientBId, setClientBId] = useState("");
  const [profileBId, setProfileBId] = useState("");
  const [roleTitle, setRoleTitle] = useState("");
  const [roleKeywords, setRoleKeywords] = useState("");
  const [comparing, setComparing] = useState(false);
  const [result, setResult] = useState<ComparisonRun | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.clients
      .list()
      .then(setClients)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Failed to load clients"));
  }, []);

  const clientAName = clients.find((c) => c.id === clientAId)?.full_name;
  const clientBName = clients.find((c) => c.id === clientBId)?.full_name;

  async function handleCompare() {
    if (!profileAId || !profileBId) {
      setError("Select a resume for both clients first.");
      return;
    }
    if (profileAId === profileBId) {
      setError("Choose two different resumes to compare.");
      return;
    }
    setComparing(true);
    setError(null);
    setResult(null);
    try {
      const keywords = roleKeywords
        .split(",")
        .map((k) => k.trim())
        .filter(Boolean);
      const run = await api.analysis.compareClients([profileAId, profileBId], roleTitle || undefined, keywords);
      setResult(run);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Comparison failed");
    } finally {
      setComparing(false);
    }
  }

  function labelFor(profileId: string): string {
    if (profileId === profileAId) return clientAName ? `${clientAName} (Client A)` : "Client A";
    if (profileId === profileBId) return clientBName ? `${clientBName} (Client B)` : "Client B";
    return profileId;
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold">Compare resumes across clients</h1>
        <p className="mt-1 text-sm text-zinc-500">
          Pick a resume from two different clients to rank them side by side and see why the weaker one might fail
          with USA-based employers.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <ClientResumePicker
          title="Client A"
          clients={clients}
          selectedClientId={clientAId}
          onSelectClient={setClientAId}
          selectedProfileId={profileAId}
          onSelectProfile={setProfileAId}
          disabled={comparing}
        />
        <ClientResumePicker
          title="Client B"
          clients={clients.filter((c) => c.id !== clientAId)}
          selectedClientId={clientBId}
          onSelectClient={setClientBId}
          selectedProfileId={profileBId}
          onSelectProfile={setProfileBId}
          disabled={comparing}
        />
      </div>

      <div className={`${card} space-y-3`}>
        <h3 className={sectionTitle}>Target role context (optional)</h3>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <div>
            <label className={label}>Role title</label>
            <input
              className={input}
              placeholder="e.g. Senior Backend Engineer"
              value={roleTitle}
              onChange={(e) => setRoleTitle(e.target.value)}
              disabled={comparing}
            />
          </div>
          <div>
            <label className={label}>Must-have keywords (comma separated)</label>
            <input
              className={input}
              placeholder="python, aws, postgresql"
              value={roleKeywords}
              onChange={(e) => setRoleKeywords(e.target.value)}
              disabled={comparing}
            />
          </div>
        </div>
        <button
          className={`${btn} gap-2`}
          onClick={handleCompare}
          disabled={comparing || !profileAId || !profileBId}
        >
          {comparing && <Spinner />}
          {comparing ? "Comparing… (can take ~10-20s)" : "Compare"}
        </button>
      </div>

      {comparing && (
        <div className="flex items-center gap-2 rounded bg-zinc-50 p-3 text-sm text-zinc-500 dark:bg-zinc-800/50">
          <Spinner className="h-4 w-4" />
          Running the comparison agent across both resumes — this can take 10-20 seconds…
        </div>
      )}

      {error && <p className={errorText}>{error}</p>}

      {result && !comparing && <ComparisonResultView comparisonResult={result} labelFor={labelFor} />}
    </div>
  );
}
