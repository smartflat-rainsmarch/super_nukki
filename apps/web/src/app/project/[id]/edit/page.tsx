"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { authHeaders } from "@/lib/auth";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface LayerData {
  id: string;
  type: string;
  position: { x: number; y: number; w: number; h: number } | null;
  text_content: string | null;
  z_index: number;
}

interface SelectedLayer {
  id: string;
  x: number;
  y: number;
  w: number;
  h: number;
}

export default function EditPage() {
  const params = useParams();
  const router = useRouter();
  const id = params.id as string;

  const [layers, setLayers] = useState<LayerData[]>([]);
  const [selected, setSelected] = useState<SelectedLayer | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      const res = await fetch(`${API_BASE}/api/project/${id}/result`, {
        headers: authHeaders(),
      });
      if (res.ok) {
        const data = await res.json();
        setLayers(data.layers ?? []);
      }
      setLoading(false);
    }
    load();
  }, [id]);

  const handleSelectLayer = useCallback((layer: LayerData) => {
    if (!layer.position) return;
    setSelected({
      id: layer.id,
      x: layer.position.x,
      y: layer.position.y,
      w: layer.position.w,
      h: layer.position.h,
    });
  }, []);

  const handleUpdatePosition = useCallback(
    (field: keyof Omit<SelectedLayer, "id">, value: number) => {
      if (!selected) return;
      setSelected({ ...selected, [field]: value });
    },
    [selected],
  );

  const handleSave = useCallback(async () => {
    if (!selected) return;

    setLayers((prev) =>
      prev.map((l) =>
        l.id === selected.id
          ? {
              ...l,
              position: {
                x: selected.x,
                y: selected.y,
                w: selected.w,
                h: selected.h,
              },
            }
          : l,
      ),
    );
    setSelected(null);
  }, [selected]);

  const handleRegenerate = useCallback(async () => {
    router.push(`/project/${id}`);
  }, [id, router]);

  if (loading) {
    return (
      <main className="flex min-h-screen items-center justify-center">
        <p className="text-gray-500">로딩 중...</p>
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-6xl p-8">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold">레이어 편집</h1>
        <div className="flex gap-3">
          <button
            onClick={handleRegenerate}
            className="rounded-lg border border-gray-300 px-4 py-2 text-sm transition hover:bg-gray-50"
          >
            PSD 재생성
          </button>
          <button
            onClick={() => router.push(`/project/${id}`)}
            className="rounded-lg bg-blue-600 px-4 py-2 text-sm text-white transition hover:bg-blue-700"
          >
            완료
          </button>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <div className="relative rounded-xl bg-gray-100 p-4" style={{ minHeight: 400 }}>
            <p className="text-center text-sm text-gray-400">
              캔버스 미리보기 (Konva.js 통합 예정)
            </p>
            {layers.map((layer) => {
              if (!layer.position) return null;
              const isSelected = selected?.id === layer.id;
              return (
                <div
                  key={layer.id}
                  onClick={() => handleSelectLayer(layer)}
                  className={`absolute cursor-pointer border-2 transition ${
                    isSelected ? "border-blue-500 bg-blue-500/10" : "border-transparent hover:border-gray-400"
                  }`}
                  style={{
                    left: `${(layer.position.x / 400) * 100}%`,
                    top: `${(layer.position.y / 700) * 100}%`,
                    width: `${(layer.position.w / 400) * 100}%`,
                    height: `${(layer.position.h / 700) * 100}%`,
                  }}
                >
                  <span className="rounded bg-black/50 px-1 text-xs text-white">
                    {layer.type}
                  </span>
                </div>
              );
            })}
          </div>
        </div>

        <div>
          <h2 className="mb-3 text-lg font-semibold">레이어 목록</h2>
          <div className="space-y-2">
            {layers.map((layer) => (
              <div
                key={layer.id}
                onClick={() => handleSelectLayer(layer)}
                className={`cursor-pointer rounded-lg p-3 transition ${
                  selected?.id === layer.id ? "bg-blue-50 ring-2 ring-blue-300" : "bg-white hover:bg-gray-50"
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="rounded bg-gray-100 px-2 py-0.5 text-xs">
                    {layer.type}
                  </span>
                  <span className="text-xs text-gray-400">z:{layer.z_index}</span>
                </div>
                {layer.text_content && (
                  <p className="mt-1 truncate text-sm text-gray-600">{layer.text_content}</p>
                )}
              </div>
            ))}
          </div>

          {selected && (
            <div className="mt-4 rounded-xl bg-white p-4 shadow">
              <h3 className="mb-3 text-sm font-semibold">위치 조정</h3>
              <div className="grid grid-cols-2 gap-2">
                {(["x", "y", "w", "h"] as const).map((field) => (
                  <label key={field} className="text-xs">
                    {field.toUpperCase()}
                    <input
                      type="number"
                      value={selected[field]}
                      onChange={(e) => handleUpdatePosition(field, Number(e.target.value))}
                      className="mt-1 w-full rounded border px-2 py-1 text-sm"
                    />
                  </label>
                ))}
              </div>
              <button
                onClick={handleSave}
                className="mt-3 w-full rounded bg-blue-600 py-1.5 text-sm text-white transition hover:bg-blue-700"
              >
                적용
              </button>
            </div>
          )}
        </div>
      </div>
    </main>
  );
}
