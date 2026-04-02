"use client";

import { useState } from "react";
import { authHeaders } from "@/lib/auth";
import { useTranslation } from "@/lib/i18n";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8001";

interface FigmaShareModalProps {
  projectId: string;
  onClose: () => void;
}

export function FigmaShareModal({ projectId, onClose }: FigmaShareModalProps) {
  const { t } = useTranslation();
  const [shareCode, setShareCode] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleCreateShare = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/api/export/${projectId}/figma-share`, {
        method: "POST",
        headers: authHeaders(),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: "Failed" }));
        throw new Error(err.detail);
      }
      const data = await res.json();
      setShareCode(data.share_code);
    } catch (err) {
      setError(err instanceof Error ? err.message : t("common.error"));
    } finally {
      setLoading(false);
    }
  };

  const handleCopy = async () => {
    if (!shareCode) return;
    await navigator.clipboard.writeText(shareCode);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" onClick={onClose}>
      <div className="w-full max-w-md rounded-xl bg-white p-6 shadow-xl" onClick={(e) => e.stopPropagation()}>
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-bold">{t("figma.title")}</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">X</button>
        </div>

        {!shareCode ? (
          <>
            <p className="mb-4 text-sm text-gray-600">{t("figma.description")}</p>

            {error && <p className="mb-3 text-sm text-red-600">{error}</p>}

            <button
              onClick={handleCreateShare}
              disabled={loading}
              className="w-full rounded-lg bg-blue-600 py-3 text-sm font-medium text-white transition hover:bg-blue-700 disabled:opacity-50"
            >
              {loading ? t("common.loading") : t("figma.generateCode")}
            </button>
          </>
        ) : (
          <>
            <div className="mb-4 space-y-3">
              <p className="text-sm text-gray-600">{t("figma.step1")}</p>

              <p className="text-sm text-gray-600">{t("figma.step2")}</p>

              <div className="flex items-center gap-2 rounded-lg bg-gray-100 px-4 py-3">
                <code className="flex-1 text-lg font-mono font-bold tracking-wider text-gray-800">
                  {shareCode}
                </code>
                <button
                  onClick={handleCopy}
                  className="rounded bg-blue-600 px-3 py-1 text-xs text-white transition hover:bg-blue-700"
                >
                  {copied ? t("figma.copied") : t("figma.copy")}
                </button>
              </div>

              <p className="text-xs text-gray-400">{t("figma.expiresIn")}</p>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
