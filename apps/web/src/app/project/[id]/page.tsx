"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface ProjectStatus {
  id: string;
  image_url: string;
  status: string;
  stage: string;
  progress: number;
  created_at: string;
}

interface ProjectResult {
  id: string;
  image_url: string;
  status: string;
  psd_url: string | null;
  notice: string | null;
  layers: Array<{
    id: string;
    type: string;
    position: Record<string, number> | null;
    text_content: string | null;
    z_index: number;
    layer_kind: "editable" | "raster";
  }>;
}

const STAGE_LABELS: Record<string, string> = {
  pending: "대기 중",
  queued: "큐 대기 중",
  preprocessing: "전처리 중",
  analyzing: "레이아웃 분석 중",
  segmenting: "요소 분리 중",
  inpainting: "배경 복원 중",
  composing: "레이어 구성 중",
  exporting: "PSD 생성 중",
  completed: "완료",
  failed: "실패",
};

export default function ProjectPage() {
  const params = useParams();
  const id = params.id as string;

  const [status, setStatus] = useState<ProjectStatus | null>(null);
  const [result, setResult] = useState<ProjectResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const fetchStatus = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/project/${id}`);
      if (!res.ok) throw new Error("Failed to fetch project");
      const data: ProjectStatus = await res.json();
      setStatus(data);

      if (data.status === "done") {
        const resultRes = await fetch(`${API_BASE}/api/project/${id}/result`);
        if (resultRes.ok) {
          setResult(await resultRes.json());
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error fetching project");
    }
  }, [id]);

  useEffect(() => {
    fetchStatus();
  }, [fetchStatus]);

  useEffect(() => {
    if (status?.status === "done" || status?.status === "failed") return;
    const interval = setInterval(fetchStatus, 2000);
    return () => clearInterval(interval);
  }, [fetchStatus, status?.status]);

  if (error) {
    return (
      <main className="flex min-h-screen items-center justify-center p-8">
        <p className="text-red-600">{error}</p>
      </main>
    );
  }

  if (!status) {
    return (
      <main className="flex min-h-screen items-center justify-center p-8">
        <p className="text-gray-500">로딩 중...</p>
      </main>
    );
  }

  const isProcessing = status.status === "processing" || status.status === "pending";
  const isDone = status.status === "done";
  const isFailed = status.status === "failed";

  return (
    <main className="mx-auto max-w-4xl p-8">
      <h1 className="mb-6 text-3xl font-bold">
        {isDone ? "변환 완료" : isProcessing ? "처리 중..." : "프로젝트"}
      </h1>

      {isProcessing && (
        <div className="mb-8 rounded-xl bg-white p-8 shadow">
          <p className="mb-2 text-lg font-medium">
            {STAGE_LABELS[status.stage] ?? status.stage}
          </p>
          <div className="mb-2 h-3 w-full overflow-hidden rounded-full bg-gray-200">
            <div
              className="h-full rounded-full bg-blue-600 transition-all duration-500"
              style={{ width: `${status.progress}%` }}
            />
          </div>
          <p className="text-sm text-gray-500">{status.progress}% 완료</p>
        </div>
      )}

      {isFailed && (
        <div className="mb-8 rounded-xl bg-red-50 p-6">
          <p className="text-red-600">처리에 실패했습니다. 다시 시도해주세요.</p>
        </div>
      )}

      {isDone && result && (
        <div className="space-y-6">
          {/* Notice */}
          {result.notice && (
            <div className="rounded-lg bg-amber-50 px-4 py-3 text-sm text-amber-700">
              {result.notice}
            </div>
          )}

          <div className="flex gap-4">
            <a
              href={`${API_BASE}/api/download/${id}`}
              className="rounded-lg bg-blue-600 px-6 py-3 text-white transition hover:bg-blue-700"
            >
              PSD 다운로드
            </a>
            <a
              href={`/project/${id}/edit`}
              className="rounded-lg border border-gray-300 px-6 py-3 text-gray-700 transition hover:bg-gray-50"
            >
              레이어 편집
            </a>
            <a
              href="/upload"
              className="rounded-lg border border-gray-300 px-6 py-3 text-gray-700 transition hover:bg-gray-50"
            >
              새 이미지 변환
            </a>
          </div>

          {result.layers.length > 0 && (
            <div className="rounded-xl bg-white p-6 shadow">
              <h2 className="mb-4 text-xl font-semibold">레이어 목록</h2>
              <div className="space-y-2">
                {result.layers.map((layer) => (
                  <div
                    key={layer.id}
                    className="flex items-center justify-between rounded-lg bg-gray-50 px-4 py-3"
                  >
                    <div>
                      <span className="mr-2 rounded bg-blue-100 px-2 py-0.5 text-xs text-blue-700">
                        {layer.type}
                      </span>
                      <span className={`mr-2 rounded px-2 py-0.5 text-xs ${
                        layer.layer_kind === "editable"
                          ? "bg-green-100 text-green-700"
                          : "bg-gray-100 text-gray-500"
                      }`}>
                        {layer.layer_kind === "editable" ? "편집가능" : "래스터"}
                      </span>
                      {layer.text_content && (
                        <span className="text-sm text-gray-600">
                          {layer.text_content}
                        </span>
                      )}
                    </div>
                    <span className="text-xs text-gray-400">z: {layer.z_index}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </main>
  );
}
