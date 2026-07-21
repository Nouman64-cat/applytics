"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { api, ApiError } from "@/lib/api";
import type { Client, Profile, TargetRole } from "@/lib/types";
import { errorText } from "@/lib/ui";
import TargetRolesSection from "@/components/TargetRolesSection";
import ProfilesSection from "@/components/ProfilesSection";
import AnalysisSection from "@/components/AnalysisSection";
import ApplicationsSection from "@/components/ApplicationsSection";
import PerformanceSection from "@/components/PerformanceSection";

export default function ClientDetail({ clientId }: { clientId: string }) {
  const [client, setClient] = useState<Client | null>(null);
  const [targetRoles, setTargetRoles] = useState<TargetRole[]>([]);
  const [profiles, setProfiles] = useState<Profile[]>([]);
  const [error, setError] = useState<string | null>(null);

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

  if (error) return <p className={errorText}>{error}</p>;
  if (!client) return <p className="text-sm text-zinc-500">Loading…</p>;

  return (
    <div className="space-y-6">
      <div>
        <Link href="/dashboard" className="text-sm text-zinc-500 hover:underline">
          ← All clients
        </Link>
        <h1 className="mt-1 text-xl font-semibold">{client.full_name}</h1>
        <p className="text-sm text-zinc-500">
          {client.email}
          {client.current_city || client.current_state || client.current_country
            ? ` · ${[client.current_city, client.current_state, client.current_country].filter(Boolean).join(", ")}`
            : ""}{" "}
          · {client.status}
        </p>
      </div>

      <TargetRolesSection clientId={clientId} targetRoles={targetRoles} onChanged={refreshTargetRoles} />

      <ProfilesSection
        clientId={clientId}
        targetRoles={targetRoles}
        profiles={profiles}
        onChanged={refreshProfiles}
      />

      <AnalysisSection clientId={clientId} targetRoles={targetRoles} profiles={profiles} />

      <ApplicationsSection clientId={clientId} profiles={profiles} />

      <PerformanceSection clientId={clientId} targetRoles={targetRoles} profiles={profiles} />
    </div>
  );
}

function errMsg(err: unknown): string {
  return err instanceof ApiError ? err.message : "Something went wrong";
}
