"use client";

import { useEffect } from "react";
import Spinner from "@/components/Spinner";

export default function ConfirmDialog({
  open,
  title,
  description,
  confirmLabel = "Confirm",
  cancelLabel = "Cancel",
  destructive = false,
  loading = false,
  onConfirm,
  onCancel,
}: {
  open: boolean;
  title: string;
  description?: string;
  confirmLabel?: string;
  cancelLabel?: string;
  destructive?: boolean;
  loading?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  useEffect(() => {
    if (!open) return;
    function onKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") onCancel();
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [open, onCancel]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" role="dialog" aria-modal="true">
      <div className="absolute inset-0 bg-zinc-900/40 backdrop-blur-sm" onClick={loading ? undefined : onCancel} />
      <div className="relative w-full max-w-sm rounded-2xl border border-zinc-200/70 bg-white p-5 shadow-xl">
        <h2 className="text-base font-semibold tracking-tight text-zinc-900">{title}</h2>
        {description && <p className="mt-1.5 text-sm text-zinc-500">{description}</p>}
        <div className="mt-5 flex justify-end gap-2">
          <button
            className="inline-flex items-center justify-center rounded-lg border border-zinc-200 bg-white px-3.5 py-2 text-sm font-medium text-zinc-700 shadow-sm hover:bg-zinc-50 hover:border-zinc-300 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            onClick={onCancel}
            disabled={loading}
          >
            {cancelLabel}
          </button>
          <button
            className={`inline-flex items-center justify-center gap-2 rounded-lg px-3.5 py-2 text-sm font-medium text-white shadow-sm disabled:opacity-50 disabled:cursor-not-allowed transition-colors ${
              destructive ? "bg-red-600 hover:bg-red-700 active:bg-red-800" : "bg-indigo-600 hover:bg-indigo-700 active:bg-indigo-800"
            }`}
            onClick={onConfirm}
            disabled={loading}
          >
            {loading && <Spinner className="h-3.5 w-3.5" />}
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
