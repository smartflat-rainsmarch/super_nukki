"use client";

import { useCallback, useState } from "react";
import { uploadImage } from "@/lib/api";

type UploadState = "idle" | "uploading" | "success" | "error";

export default function UploadPage() {
  const [state, setState] = useState<UploadState>("idle");
  const [dragOver, setDragOver] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [projectId, setProjectId] = useState<string | null>(null);

  const handleFile = useCallback(async (file: File) => {
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

    try {
      const result = await uploadImage(file);
      setProjectId(result.project_id);
      setState("success");
    } catch (err) {
      setError(err instanceof Error ? err.message : "업로드에 실패했습니다.");
      setState("error");
    }
  }, []);

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
      <h1 className="mb-8 text-3xl font-bold">이미지 업로드</h1>

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
          <p className="text-gray-500">
            PNG, JPG, WebP 파일을 드래그하거나 클릭하여 업로드하세요
            <br />
            <span className="text-sm">또는 Ctrl+V로 클립보드에서 붙여넣기</span>
          </p>
        )}

        {state === "uploading" && (
          <p className="text-blue-600">업로드 중...</p>
        )}

        {state === "success" && (
          <div>
            <p className="mb-2 text-green-600">업로드 완료!</p>
            <a
              href={`/project/${projectId}`}
              className="text-blue-600 underline"
            >
              결과 보기
            </a>
          </div>
        )}

        {state === "error" && (
          <p className="text-red-600">{error}</p>
        )}
      </label>
    </main>
  );
}
