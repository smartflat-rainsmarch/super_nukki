"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { authHeaders } from "@/lib/auth";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8001";

interface Position {
  x: number;
  y: number;
  w: number;
  h: number;
}

interface LayerData {
  id: string;
  type: string;
  position: Position | null;
  image_url: string | null;
  text_content: string | null;
  z_index: number;
  layer_kind: "editable" | "raster";
  visible: boolean;
}

interface CanvasSize {
  width: number;
  height: number;
}

const TYPE_COLORS: Record<string, string> = {
  background: "bg-gray-200 text-gray-600",
  text: "bg-green-100 text-green-700",
  button: "bg-blue-100 text-blue-700",
  card: "bg-purple-100 text-purple-700",
  icon: "bg-yellow-100 text-yellow-700",
  image: "bg-pink-100 text-pink-700",
};

export default function EditPage() {
  const params = useParams();
  const router = useRouter();
  const id = params.id as string;

  const [layers, setLayers] = useState<LayerData[]>([]);
  const [canvasSize, setCanvasSize] = useState<CanvasSize>({ width: 400, height: 700 });
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLDivElement>(null);
  const [displayScale, setDisplayScale] = useState(1);

  // Drag state
  const [dragging, setDragging] = useState(false);
  const dragStart = useRef<{ mouseX: number; mouseY: number; origX: number; origY: number } | null>(null);

  // Load data
  useEffect(() => {
    async function load() {
      try {
        const res = await fetch(`${API_BASE}/api/project/${id}/result`, {
          headers: authHeaders(),
        });
        if (!res.ok) {
          setLoadError("프로젝트를 불러올 수 없���니다.");
          setLoading(false);
          return;
        }
        const data = await res.json();
        if (data.canvas_size) setCanvasSize(data.canvas_size);
        setLayers(
          (data.layers ?? []).map((l: Omit<LayerData, "visible">) => ({
            ...l,
            visible: true,
          })),
        );
      } catch {
        setLoadError("네트워크 오류가 발생���습니다.");
      }
      setLoading(false);
    }
    load();
  }, [id]);

  // Calculate display scale
  useEffect(() => {
    function updateScale() {
      if (!containerRef.current) return;
      const containerWidth = containerRef.current.clientWidth - 32;
      const maxHeight = window.innerHeight - 200;
      const scaleW = containerWidth / canvasSize.width;
      const scaleH = maxHeight / canvasSize.height;
      setDisplayScale(Math.min(scaleW, scaleH, 1));
    }
    updateScale();
    window.addEventListener("resize", updateScale);
    return () => window.removeEventListener("resize", updateScale);
  }, [canvasSize]);

  const handleToggleVisibility = useCallback((layerId: string) => {
    setLayers((prev) =>
      prev.map((l) => (l.id === layerId ? { ...l, visible: !l.visible } : l)),
    );
  }, []);

  const handleSelectLayer = useCallback((layerId: string) => {
    setSelectedId((prev) => (prev === layerId ? null : layerId));
  }, []);

  // --- Drag to move ---
  const handleMouseDown = useCallback(
    (e: React.MouseEvent, layerId: string) => {
      e.preventDefault();
      e.stopPropagation();
      setSelectedId(layerId);
      const layer = layers.find((l) => l.id === layerId);
      if (!layer?.position) return;

      dragStart.current = {
        mouseX: e.clientX,
        mouseY: e.clientY,
        origX: layer.position.x,
        origY: layer.position.y,
      };
      setDragging(true);
    },
    [layers],
  );

  useEffect(() => {
    if (!dragging || !selectedId) return;

    const handleMouseMove = (e: MouseEvent) => {
      if (!dragStart.current) return;
      const dx = (e.clientX - dragStart.current.mouseX) / displayScale;
      const dy = (e.clientY - dragStart.current.mouseY) / displayScale;
      const newX = Math.round(dragStart.current.origX + dx);
      const newY = Math.round(dragStart.current.origY + dy);

      setLayers((prev) =>
        prev.map((l) =>
          l.id === selectedId && l.position
            ? { ...l, position: { ...l.position, x: newX, y: newY } }
            : l,
        ),
      );
    };

    const handleMouseUp = () => {
      setDragging(false);
      dragStart.current = null;
    };

    window.addEventListener("mousemove", handleMouseMove);
    window.addEventListener("mouseup", handleMouseUp);
    return () => {
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("mouseup", handleMouseUp);
    };
  }, [dragging, selectedId, displayScale]);

  // --- Position/Size input change ---
  const handlePositionChange = useCallback(
    (field: keyof Position, value: number) => {
      if (!selectedId) return;
      setLayers((prev) =>
        prev.map((l) =>
          l.id === selectedId && l.position
            ? { ...l, position: { ...l.position, [field]: value } }
            : l,
        ),
      );
    },
    [selectedId],
  );

  if (loading) {
    return (
      <main className="flex min-h-screen items-center justify-center">
        <p className="text-gray-500">로딩 중...</p>
      </main>
    );
  }

  if (loadError) {
    return (
      <main className="flex min-h-screen items-center justify-center">
        <p className="text-red-600">{loadError}</p>
      </main>
    );
  }

  const displayW = canvasSize.width * displayScale;
  const displayH = canvasSize.height * displayScale;
  const sortedLayers = [...layers].sort((a, b) => a.z_index - b.z_index);
  const reversedLayers = [...layers].sort((a, b) => b.z_index - a.z_index);
  const selectedLayer = layers.find((l) => l.id === selectedId);

  return (
    <main className="mx-auto max-w-7xl p-6">
      {/* Header */}
      <div className="mb-4 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">레이어 편집</h1>
          <p className="text-sm text-gray-500">
            {canvasSize.width} x {canvasSize.height}px | {layers.length}개 레이어
          </p>
        </div>
        <div className="flex gap-3">
          <button
            onClick={() => router.push(`/upload`)}
            className="rounded-lg border border-gray-300 px-4 py-2 text-sm text-gray-700 transition hover:bg-gray-50"
          >
            다시 작업하기
          </button>
          <a
            href={`${API_BASE}/api/download/${id}`}
            className="rounded-lg bg-blue-600 px-4 py-2 text-sm text-white transition hover:bg-blue-700"
          >
            PSD로 받기
          </a>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-[1fr_320px]">
        {/* Canvas */}
        <div ref={containerRef} className="flex items-start justify-center rounded-xl bg-gray-100 p-4">
          <div
            ref={canvasRef}
            className="relative overflow-hidden rounded-lg bg-white shadow-lg"
            style={{ width: displayW, height: displayH, cursor: dragging ? "grabbing" : "default" }}
          >
            {sortedLayers.map((layer) => {
              if (!layer.position || !layer.image_url) return null;
              const { x, y, w, h } = layer.position;
              const isSelected = layer.id === selectedId;

              return (
                <img
                  key={layer.id}
                  src={`${API_BASE}${layer.image_url}`}
                  alt={`${layer.type} layer`}
                  draggable={false}
                  onClick={(e) => {
                    e.stopPropagation();
                    handleSelectLayer(layer.id);
                  }}
                  onMouseDown={(e) => handleMouseDown(e, layer.id)}
                  className="absolute select-none transition-opacity duration-200"
                  style={{
                    left: x * displayScale,
                    top: y * displayScale,
                    width: w * displayScale,
                    height: h * displayScale,
                    opacity: layer.visible ? 1 : 0,
                    pointerEvents: layer.visible ? "auto" : "none",
                    outline: isSelected ? "3px solid #3b82f6" : "none",
                    outlineOffset: "1px",
                    zIndex: layer.z_index,
                    cursor: layer.visible ? "grab" : "default",
                  }}
                />
              );
            })}
          </div>
        </div>

        {/* Layer Panel */}
        <div className="space-y-4">
          <h2 className="text-lg font-semibold">레이어 목록</h2>

          <div className="max-h-[50vh] space-y-1 overflow-y-auto rounded-xl bg-white p-3 shadow">
            {reversedLayers.map((layer) => {
              const isSelected = layer.id === selectedId;
              return (
                <div
                  key={layer.id}
                  onClick={() => handleSelectLayer(layer.id)}
                  className={`flex cursor-pointer items-center gap-2 rounded-lg px-3 py-2 transition ${
                    isSelected ? "bg-blue-50 ring-2 ring-blue-300" : "hover:bg-gray-50"
                  } ${!layer.visible ? "opacity-40" : ""}`}
                >
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleToggleVisibility(layer.id);
                    }}
                    className="flex h-6 w-6 shrink-0 items-center justify-center rounded text-xs hover:bg-gray-200"
                    title={layer.visible ? "숨기기" : "보이기"}
                  >
                    {layer.visible ? (
                      <svg className="h-4 w-4 text-gray-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                        <path strokeLinecap="round" strokeLinejoin="round" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                      </svg>
                    ) : (
                      <svg className="h-4 w-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21" />
                      </svg>
                    )}
                  </button>

                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-1.5">
                      <span className={`rounded px-1.5 py-0.5 text-[10px] font-medium ${TYPE_COLORS[layer.type] ?? "bg-gray-100 text-gray-600"}`}>
                        {layer.type}
                      </span>
                      {layer.layer_kind === "editable" && (
                        <span className="text-[10px] text-green-600">편집가능</span>
                      )}
                    </div>
                    {layer.text_content && (
                      <p className="mt-0.5 truncate text-xs text-gray-500">{layer.text_content}</p>
                    )}
                  </div>

                  <span className="text-[10px] text-gray-300">{layer.z_index}</span>
                </div>
              );
            })}
          </div>

          {/* Selected Layer Controls */}
          {selectedLayer && selectedLayer.position && (
            <div className="rounded-xl bg-white p-4 shadow">
              <h3 className="mb-3 text-sm font-semibold">선택된 레이어</h3>

              <div className="mb-3 flex items-center gap-2">
                <span className={`rounded px-1.5 py-0.5 text-[10px] font-medium ${TYPE_COLORS[selectedLayer.type] ?? "bg-gray-100 text-gray-600"}`}>
                  {selectedLayer.type}
                </span>
                {selectedLayer.text_content && (
                  <span className="truncate text-xs text-gray-500">&ldquo;{selectedLayer.text_content}&rdquo;</span>
                )}
              </div>

              {/* Position inputs */}
              <p className="mb-1 text-[10px] font-medium text-gray-400">위치</p>
              <div className="mb-3 grid grid-cols-2 gap-2">
                {(["x", "y"] as const).map((field) => (
                  <label key={field} className="text-xs">
                    <span className="text-gray-400">{field.toUpperCase()}</span>
                    <input
                      type="number"
                      value={selectedLayer.position![field]}
                      onChange={(e) => handlePositionChange(field, Number(e.target.value))}
                      className="mt-0.5 w-full rounded border px-2 py-1 text-sm focus:border-blue-500 focus:outline-none"
                    />
                  </label>
                ))}
              </div>

              {/* Size inputs */}
              <p className="mb-1 text-[10px] font-medium text-gray-400">크기</p>
              <div className="grid grid-cols-2 gap-2">
                {(["w", "h"] as const).map((field) => (
                  <label key={field} className="text-xs">
                    <span className="text-gray-400">{field === "w" ? "W" : "H"}</span>
                    <input
                      type="number"
                      value={selectedLayer.position![field]}
                      onChange={(e) => handlePositionChange(field, Math.max(1, Number(e.target.value)))}
                      className="mt-0.5 w-full rounded border px-2 py-1 text-sm focus:border-blue-500 focus:outline-none"
                    />
                  </label>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </main>
  );
}
