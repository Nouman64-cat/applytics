export const card = "rounded-2xl border border-zinc-200/70 bg-white p-4 shadow-sm";
export const btn =
  "inline-flex items-center justify-center rounded-lg bg-indigo-600 text-white px-3.5 py-2 text-sm font-medium shadow-sm hover:bg-indigo-700 active:bg-indigo-800 disabled:opacity-50 disabled:cursor-not-allowed transition-colors";
export const btnSecondary =
  "inline-flex items-center justify-center rounded-lg border border-zinc-200 bg-white px-3.5 py-2 text-sm font-medium text-zinc-700 shadow-sm hover:bg-zinc-50 hover:border-zinc-300 disabled:opacity-50 disabled:cursor-not-allowed transition-colors";
export const input =
  "w-full rounded-lg border border-zinc-200 bg-white px-3 py-2 text-sm text-zinc-900 placeholder:text-zinc-400 shadow-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/40 focus:border-indigo-400 transition-shadow";
export const label = "block text-xs font-medium text-zinc-500 mb-1.5";
export const errorText = "text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2";
export const sectionTitle = "text-sm font-semibold text-zinc-900 tracking-tight";
export const badge = "inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium bg-zinc-100 text-zinc-600";

export const badgeVariants: Record<string, string> = {
  fully_remote: "bg-emerald-50 text-emerald-700",
  hybrid: "bg-amber-50 text-amber-700",
  onsite: "bg-zinc-100 text-zinc-600",
  unknown: "bg-zinc-100 text-zinc-500",
};

export function remoteBadge(remoteType: string): string {
  return `inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${
    badgeVariants[remoteType] ?? badgeVariants.unknown
  }`;
}
