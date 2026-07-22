"use client";

import { useCallback, useEffect, useState } from "react";
import { api, ApiError } from "@/lib/api";
import type { Profile, ProfilePerformance, TargetRole } from "@/lib/types";
import { card, errorText, input, label, sectionTitle } from "@/lib/ui";

export default function PerformanceSection({
  clientId,
  targetRoles,
  profiles,
}: {
  clientId: string;
  targetRoles: TargetRole[];
  profiles: Profile[];
}) {
  const [targetRoleId, setTargetRoleId] = useState("");
  const [performance, setPerformance] = useState<ProfilePerformance[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(() => {
    api.clients
      .performance(clientId, targetRoleId || undefined)
      .then(setPerformance)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Failed to load performance"));
  }, [clientId, targetRoleId]);

  useEffect(refresh, [refresh]);

  function profileLabel(id: string): string {
    const profile = profiles.find((p) => p.id === id);
    return profile ? `${profile.type} · ${profile.variant_label}` : id;
  }

  return (
    <section className={`${card} space-y-3`}>
      <div className="flex items-center justify-between">
        <h2 className={sectionTitle}>Profile performance (ground truth)</h2>
        <div className="flex items-center gap-2">
          <label className={`${label} mb-0`}>Filter by target role:</label>
          <select className={input} value={targetRoleId} onChange={(e) => setTargetRoleId(e.target.value)}>
            <option value="">All</option>
            {targetRoles.map((tr) => (
              <option key={tr.id} value={tr.id}>
                {tr.title}
              </option>
            ))}
          </select>
        </div>
      </div>

      {error && <p className={errorText}>{error}</p>}

      {performance === null ? (
        <p className="text-sm text-zinc-500">Loading…</p>
      ) : performance.length === 0 ? (
        <p className="text-sm text-zinc-500">No profiles to show performance for.</p>
      ) : (
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs uppercase text-zinc-400">
              <th className="pb-1">Profile</th>
              <th className="pb-1">Total applications</th>
              <th className="pb-1">Interview rate</th>
              <th className="pb-1">Status breakdown</th>
            </tr>
          </thead>
          <tbody>
            {performance.map((p) => (
              <tr key={p.profile_id} className="border-t border-zinc-100 hover:bg-zinc-50">
                <td className="py-1.5 pr-2">{profileLabel(p.profile_id)}</td>
                <td className="py-1.5 pr-2">{p.total_applications}</td>
                <td className="py-1.5 pr-2">
                  {p.interview_rate === null ? "—" : `${Math.round(p.interview_rate * 100)}%`}
                </td>
                <td className="py-1.5 text-xs text-zinc-500">
                  {Object.entries(p.status_counts)
                    .filter(([, count]) => count > 0)
                    .map(([status, count]) => `${status}: ${count}`)
                    .join(", ") || "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}
