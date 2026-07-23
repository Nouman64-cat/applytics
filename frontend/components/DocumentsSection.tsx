"use client";

import { useEffect, useRef, useState } from "react";
import { api, ApiError } from "@/lib/api";
import type { ClientDocument } from "@/lib/types";
import { btn, card, errorText, sectionTitle } from "@/lib/ui";
import Spinner from "@/components/Spinner";
import ConfirmDialog from "@/components/ConfirmDialog";

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
}

function TrashIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" strokeWidth={1.75} stroke="currentColor" className="h-4 w-4 shrink-0">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="m14.74 9-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 0 1-2.244 2.077H8.084a2.25 2.25 0 0 1-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 0 0-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 0 1 3.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 0 0-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 0 0-7.5 0"
      />
    </svg>
  );
}

function DocumentIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" strokeWidth={1.5} stroke="currentColor" className="h-8 w-8 shrink-0">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m5.231 13.481L15 17.25m-1.519-3.75L12 17.25m0 0-1.481-3.75M12 17.25V21m-7.5-3.75h15A2.25 2.25 0 0 0 21.75 15V5.25A2.25 2.25 0 0 0 19.5 3h-15a2.25 2.25 0 0 0-2.25 2.25V15a2.25 2.25 0 0 0 2.25 2.25Z"
      />
    </svg>
  );
}

function DocumentPreview({ document }: { document: ClientDocument }) {
  if (document.content_type.startsWith("image/")) {
    return (
      <a href={document.preview_url} target="_blank" rel="noreferrer" className="block shrink-0">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={document.preview_url}
          alt={document.filename}
          className="h-16 w-16 rounded-lg border border-zinc-200 object-cover"
        />
      </a>
    );
  }
  if (document.content_type === "application/pdf") {
    return (
      <a
        href={document.preview_url}
        target="_blank"
        rel="noreferrer"
        className="block h-16 w-16 shrink-0 overflow-hidden rounded-lg border border-zinc-200 bg-white"
      >
        <embed src={document.preview_url} type="application/pdf" className="h-full w-full" />
      </a>
    );
  }
  return (
    <div className="flex h-16 w-16 shrink-0 items-center justify-center rounded-lg border border-zinc-200 bg-zinc-50 text-zinc-400">
      <DocumentIcon />
    </div>
  );
}

export default function DocumentsSection({ clientId }: { clientId: string }) {
  const [documents, setDocuments] = useState<ClientDocument[] | null>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pendingDelete, setPendingDelete] = useState<ClientDocument | null>(null);
  const [deleting, setDeleting] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  function refresh() {
    api.clients
      .listDocuments(clientId)
      .then(setDocuments)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Failed to load documents"));
  }

  useEffect(refresh, [clientId]);

  async function handleUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    setError(null);
    try {
      await api.clients.uploadDocument(clientId, file);
      refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Upload failed");
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  }

  async function handleDelete() {
    if (!pendingDelete) return;
    setDeleting(true);
    setError(null);
    try {
      await api.clients.deleteDocument(pendingDelete.id);
      setPendingDelete(null);
      refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to delete document");
    } finally {
      setDeleting(false);
    }
  }

  return (
    <section className={`${card} space-y-3`}>
      <div className="flex items-center justify-between">
        <h2 className={sectionTitle}>Documents</h2>
        <button className={`${btn} gap-2`} onClick={() => fileInputRef.current?.click()} disabled={uploading}>
          {uploading && <Spinner className="h-4 w-4" />}
          {uploading ? "Uploading…" : "+ Upload document"}
        </button>
        <input ref={fileInputRef} type="file" className="hidden" onChange={handleUpload} disabled={uploading} />
      </div>

      {uploading && (
        <div className="flex items-center gap-2 rounded-lg bg-indigo-50 p-3 text-sm font-medium text-indigo-700">
          <Spinner className="h-4 w-4" />
          Uploading to S3…
        </div>
      )}

      {error && <p className={errorText}>{error}</p>}

      {documents === null ? (
        <div className="flex items-center gap-2 py-4 text-sm text-zinc-500">
          <Spinner className="h-4 w-4" />
          Loading…
        </div>
      ) : documents.length === 0 ? (
        <p className="py-4 text-center text-sm text-zinc-500">No documents uploaded yet.</p>
      ) : (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {documents.map((doc) => (
            <div key={doc.id} className="flex items-start gap-3 rounded-xl border border-zinc-200/70 p-3">
              <DocumentPreview document={doc} />
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium text-zinc-900" title={doc.filename}>
                  {doc.filename}
                </p>
                <p className="text-xs text-zinc-400">
                  {formatSize(doc.size_bytes)} · {formatDate(doc.uploaded_at)}
                </p>
                <a
                  href={doc.preview_url}
                  target="_blank"
                  rel="noreferrer"
                  className="mt-1 inline-block text-xs font-medium text-indigo-600 hover:text-indigo-700"
                >
                  View / download
                </a>
              </div>
              <button
                onClick={() => setPendingDelete(doc)}
                title="Delete document"
                className="shrink-0 rounded-lg p-1 text-zinc-300 hover:bg-red-50 hover:text-red-600"
              >
                <TrashIcon />
              </button>
            </div>
          ))}
        </div>
      )}

      <ConfirmDialog
        open={pendingDelete !== null}
        title={`Delete ${pendingDelete?.filename ?? "this document"}?`}
        description="This permanently removes the file from storage. This can't be undone."
        confirmLabel="Delete"
        destructive
        loading={deleting}
        onConfirm={handleDelete}
        onCancel={() => setPendingDelete(null)}
      />
    </section>
  );
}
