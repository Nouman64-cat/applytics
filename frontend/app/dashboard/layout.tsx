"use client";

import { useEffect } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { badge, btnSecondary } from "@/lib/ui";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const { bd, loading, logout } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (!loading && !bd) router.replace("/login");
  }, [loading, bd, router]);

  if (loading || !bd) {
    return <div className="flex flex-1 items-center justify-center text-sm text-zinc-500">Loading…</div>;
  }

  const navLink = (href: string, text: string) => (
    <Link
      href={href}
      className={`text-sm font-medium ${
        pathname === href || (href !== "/dashboard" && pathname?.startsWith(href))
          ? "text-zinc-900 dark:text-zinc-100"
          : "text-zinc-500 hover:text-zinc-700 dark:hover:text-zinc-300"
      }`}
    >
      {text}
    </Link>
  );

  return (
    <div className="flex flex-1 flex-col">
      <header className="border-b border-zinc-200 dark:border-zinc-800">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-4 py-3">
          <div className="flex items-center gap-6">
            <span className="text-sm font-semibold">Applytics</span>
            <nav className="flex items-center gap-4">
              {navLink("/dashboard", "Clients")}
              {navLink("/dashboard/jobs", "Jobs")}
            </nav>
          </div>
          <div className="flex items-center gap-3">
            <span className={badge}>
              {bd.email} · {bd.role}
            </span>
            <button className={btnSecondary} onClick={logout}>
              Log out
            </button>
          </div>
        </div>
      </header>
      <main className="mx-auto w-full max-w-5xl flex-1 px-4 py-6">{children}</main>
    </div>
  );
}
