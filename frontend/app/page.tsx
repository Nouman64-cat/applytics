"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";

export default function Home() {
  const { bd, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (loading) return;
    router.replace(bd ? "/dashboard" : "/login");
  }, [bd, loading, router]);

  return <div className="flex flex-1 items-center justify-center text-sm text-zinc-500">Loading…</div>;
}
