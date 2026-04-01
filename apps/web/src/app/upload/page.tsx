"use client";

import { useCallback, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { uploadImage } from "@/lib/api";
import { useTranslation } from "@/lib/i18n";

type UploadState = "idle" | "uploading" | "success" | "error" | "limit_reached";

export default function UploadPage() {
  const router = useRouter();
  const { t } = useTranslation();
  const [state, setState] = useState<UploadState>("idle");
  const [dragOver, setDragOver] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [progress, setProgress] = useState(0);

  const handleFile = useCallback(
    async (file: File) => {
      const allowed = ["image/png", "image/jpeg", "image/webp"];
      if (!allowed.includes(file.type)) {
        setError(t("upload.invalidType"));
        setState("error");
        return;
      }

      if (file.size > 20 * 1024 * 1024) {
        setError(t("upload.tooLarge"));
        setState("error");
        return;
      }

      setState("uploading");
      setError(null);
      setProgress(30);

      try {
        setProgress(60);
        const result = await uploadImage(file);
        setProgress(100);
        setState("success");
        setTimeout(() => {
          router.push(`/project/${result.project_id}`);
        }, 500);
      } catch (err) {
        const message = err instanceof Error ? err.message : t("common.error");
        if (message.includes("무료") || message.includes("한도") || message.includes("limit")) {
          setState("limit_reached");
        } else {
          setError(message);
          setState("error");
        }
      }
    },
    [router, t],
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragOver(false);
      const file = e.dataTransfer.files[0];
      if (file) handleFile(file);
    },
    [handleFile],
  );

  const handleChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) handleFile(file);
    },
    [handleFile],
  );

  const handlePaste = useCallback(
    (e: React.ClipboardEvent) => {
      const file = Array.from(e.clipboardData.items)
        .find((item) => item.type.startsWith("image/"))
        ?.getAsFile();
      if (file) handleFile(file);
    },
    [handleFile],
  );

  return (
    <main
      className="flex min-h-screen flex-col items-center justify-center p-8"
      onPaste={handlePaste}
    >
      <h1 className="mb-2 text-3xl font-bold">{t("upload.title")}</h1>
      <p className="mb-8 text-gray-500">{t("upload.subtitle")}</p>

      {state === "limit_reached" && (
        <div className="mb-6 w-full max-w-lg rounded-xl border border-amber-200 bg-amber-50 p-8 text-center">
          <div className="mb-3 text-4xl">3/3</div>
          <h2 className="mb-2 text-xl font-bold text-gray-900">
            {t("upload.limitTitle")}
          </h2>
          <p className="mb-6 text-sm text-gray-600">
            {t("upload.limitDesc")}
          </p>
          <div className="flex justify-center gap-3">
            <Link
              href="/login"
              className="rounded-lg border border-gray-300 px-6 py-2.5 text-sm font-medium text-gray-700 transition hover:bg-gray-50"
            >
              {t("upload.limitLogin")}
            </Link>
            <Link
              href="/pricing"
              className="rounded-lg bg-blue-600 px-6 py-2.5 text-sm font-medium text-white transition hover:bg-blue-700"
            >
              {t("upload.limitPricing")}
            </Link>
          </div>
        </div>
      )}

      {state !== "limit_reached" && (
        <label
          className={`flex w-full max-w-lg cursor-pointer flex-col items-center rounded-xl border-2 border-dashed p-12 text-center transition ${
            dragOver
              ? "border-blue-500 bg-blue-50"
              : "border-gray-300 hover:border-blue-400"
          }`}
          onDragOver={(e) => {
            e.preventDefault();
            setDragOver(true);
          }}
          onDragLeave={() => setDragOver(false)}
          onDrop={handleDrop}
        >
          <input
            type="file"
            accept=".png,.jpg,.jpeg,.webp"
            className="hidden"
            onChange={handleChange}
          />

          {state === "idle" && (
            <div>
              <div className="mb-4 text-5xl text-gray-300">+</div>
              <p className="text-gray-500">{t("upload.dragText")}</p>
              <p className="mt-1 text-sm text-gray-400">{t("upload.pasteHint")}</p>
            </div>
          )}

          {state === "uploading" && (
            <div className="w-full">
              <p className="mb-3 text-blue-600">{t("upload.uploading")}</p>
              <div className="h-2 w-full overflow-hidden rounded-full bg-gray-200">
                <div
                  className="h-full rounded-full bg-blue-600 transition-all duration-300"
                  style={{ width: `${progress}%` }}
                />
              </div>
            </div>
          )}

          {state === "success" && (
            <p className="text-green-600">{t("upload.success")}</p>
          )}

          {state === "error" && (
            <div>
              <p className="mb-2 text-red-600">{error}</p>
              <button
                type="button"
                onClick={(e) => {
                  e.preventDefault();
                  setState("idle");
                  setError(null);
                }}
                className="text-sm text-blue-600 underline"
              >
                {t("upload.retry")}
              </button>
            </div>
          )}
        </label>
      )}
    </main>
  );
}
