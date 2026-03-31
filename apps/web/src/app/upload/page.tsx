"use client";

import { useCallback, useState } from "react";
import { useRouter } from "next/navigation";
import { uploadImage } from "@/lib/api";

type UploadState = "idle" | "uploading" | "success" | "error";

export default function UploadPage() {
  const router = useRouter();
  const [state, setState] = useState<UploadState>("idle");
  const [dragOver, setDragOver] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [progress, setProgress] = useState(0);

  const handleFile = useCallback(
    async (file: File) => {
      const allowed = ["image/png", "image/jpeg", "image/webp"];
      if (!allowed.includes(file.type)) {
        setError("PNG, JPG, WebP 파일만 업로드 가능합니다.");
        setState("error");
        return;
      }

      if (file.size > 20 * 1024 * 1024) {
        setError("파일 크기는 20MB 이하여야 합니다.");
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
        setError(err instanceof Error ? err.message : "업로드에 실패했습니다.");
        setState("error");
      }
    },
    [router],
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
      <h1 className="mb-2 text-3xl font-bold">이미지 업로드</h1>
      <p className="mb-8 text-gray-500">UI 이미지를 업로드하면 PSD 파일로 변환합니다</p>

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
            <p className="text-gray-500">
              PNG, JPG, WebP 파일을 드래그하거나 클릭
            </p>
            <p className="mt-1 text-sm text-gray-400">
              Ctrl+V로 클립보드 붙여넣기 가능 | 최대 20MB
            </p>
          </div>
        )}

        {state === "uploading" && (
          <div className="w-full">
            <p className="mb-3 text-blue-600">업로드 중...</p>
            <div className="h-2 w-full overflow-hidden rounded-full bg-gray-200">
              <div
                className="h-full rounded-full bg-blue-600 transition-all duration-300"
                style={{ width: `${progress}%` }}
              />
            </div>
          </div>
        )}

        {state === "success" && (
          <p className="text-green-600">업로드 완료! 처리 페이지로 이동합니다...</p>
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
              다시 시도
            </button>
          </div>
        )}
      </label>
    </main>
  );
}
