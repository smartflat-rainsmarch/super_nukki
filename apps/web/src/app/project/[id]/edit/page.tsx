"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { authHeaders } from "@/lib/auth";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8001";
const MAX_HISTORY = 50;

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
  name: string;
}

interface CanvasSize {
  width: number;
  height: number;
}

interface ContextMenuState {
  x: number;
  y: number;
}

const TYPE_COLORS: Record<string, string> = {
  background: "bg-gray-200 text-gray-600",
  text: "bg-green-100 text-green-700",
  button: "bg-blue-100 text-blue-700",
  card: "bg-purple-100 text-purple-700",
  icon: "bg-yellow-100 text-yellow-700",
  image: "bg-pink-100 text-pink-700",
};

// --- Download helper ---
async function downloadLayerImage(imageUrl: string, filename: string) {
  // imageUrl = /storage/outputs/{projectId}/layers/{file}.png
  const match = imageUrl.match(/\/storage\/outputs\/([^/]+)\/layers\/(.+)$/);
  if (!match) return;
  const [, projectId, layerFile] = match;
  const apiUrl = `${API_BASE}/api/layer-image/${projectId}/${layerFile}`;

  const res = await fetch(apiUrl);
  if (!res.ok) return;
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

export default function EditPage() {
  const params = useParams();
  const router = useRouter();
  const id = params.id as string;

  const [layers, setLayers] = useState<LayerData[]>([]);
  const [canvasSize, setCanvasSize] = useState<CanvasSize>({ width: 400, height: 700 });
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [displayScale, setDisplayScale] = useState(1);

  // Drag state
  const [dragging, setDragging] = useState(false);
  const dragStart = useRef<{
    mouseX: number;
    mouseY: number;
    origPositions: Map<string, { x: number; y: number }>;
  } | null>(null);

  // Undo/Redo history
  const [history, setHistory] = useState<LayerData[][]>([]);
  const [historyIndex, setHistoryIndex] = useState(-1);
  const skipHistoryRef = useRef(false);

  // Context menu
  const [contextMenu, setContextMenu] = useState<ContextMenuState | null>(null);

  // --- Push to history ---
  const pushHistory = useCallback((newLayers: LayerData[]) => {
    setHistory((prev) => {
      const trimmed = prev.slice(0, historyIndex + 1);
      const next = [...trimmed, newLayers];
      if (next.length > MAX_HISTORY) next.shift();
      return next;
    });
    setHistoryIndex((prev) => Math.min(prev + 1, MAX_HISTORY - 1));
  }, [historyIndex]);

  // Wrap setLayers to auto-push history
  const updateLayers = useCallback(
    (updater: (prev: LayerData[]) => LayerData[]) => {
      setLayers((prev) => {
        const next = updater(prev);
        if (!skipHistoryRef.current) {
          pushHistory(next);
        }
        return next;
      });
    },
    [pushHistory],
  );

  // --- Load data ---
  useEffect(() => {
    async function load() {
      try {
        const res = await fetch(`${API_BASE}/api/project/${id}/result`, {
          headers: authHeaders(),
        });
        if (!res.ok) {
          setLoadError("프로젝트를 불러올 수 없습니다.");
          setLoading(false);
          return;
        }
        const data = await res.json();
        if (data.canvas_size) setCanvasSize(data.canvas_size);
        const initial = (data.layers ?? []).map((l: Omit<LayerData, "visible" | "name">, i: number) => ({
          ...l,
          visible: true,
          name: l.text_content || `${l.type}_${i}`,
        }));
        setLayers(initial);
        setHistory([initial]);
        setHistoryIndex(0);
      } catch {
        setLoadError("네트워크 오류가 발생했습니다.");
      }
      setLoading(false);
    }
    load();
  }, [id]);

  // --- Display scale ---
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

  // --- Undo/Redo keyboard ---
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === "z") {
        e.preventDefault();
        if (historyIndex > 0) {
          skipHistoryRef.current = true;
          setLayers(history[historyIndex - 1]);
          setHistoryIndex((i) => i - 1);
          skipHistoryRef.current = false;
        }
      }
      if ((e.ctrlKey || e.metaKey) && e.key === "y") {
        e.preventDefault();
        if (historyIndex < history.length - 1) {
          skipHistoryRef.current = true;
          setLayers(history[historyIndex + 1]);
          setHistoryIndex((i) => i + 1);
          skipHistoryRef.current = false;
        }
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [history, historyIndex]);

  // --- Close context menu on click outside ---
  useEffect(() => {
    if (!contextMenu) return;
    const close = () => setContextMenu(null);
    window.addEventListener("click", close);
    return () => window.removeEventListener("click", close);
  }, [contextMenu]);

  // --- Selection ---
  const handleSelectLayer = useCallback((layerId: string, ctrlKey: boolean) => {
    setSelectedIds((prev) => {
      if (ctrlKey) {
        const next = new Set(prev);
        if (next.has(layerId)) {
          next.delete(layerId);
        } else {
          next.add(layerId);
        }
        return next;
      }
      return new Set([layerId]);
    });
  }, []);

  const handleToggleVisibility = useCallback((layerId: string) => {
    updateLayers((prev) =>
      prev.map((l) => (l.id === layerId ? { ...l, visible: !l.visible } : l)),
    );
  }, [updateLayers]);

  // --- Multi drag ---
  const handleMouseDown = useCallback(
    (e: React.MouseEvent, layerId: string) => {
      e.preventDefault();
      e.stopPropagation();

      // If not in selection, select it
      if (!selectedIds.has(layerId)) {
        if (e.ctrlKey || e.metaKey) {
          setSelectedIds((prev) => new Set([...prev, layerId]));
        } else {
          setSelectedIds(new Set([layerId]));
        }
      }

      const targetIds = selectedIds.has(layerId) ? selectedIds : new Set([layerId]);
      const origPositions = new Map<string, { x: number; y: number }>();
      for (const sid of targetIds) {
        const layer = layers.find((l) => l.id === sid);
        if (layer?.position) {
          origPositions.set(sid, { x: layer.position.x, y: layer.position.y });
        }
      }

      dragStart.current = {
        mouseX: e.clientX,
        mouseY: e.clientY,
        origPositions,
      };
      setDragging(true);
    },
    [layers, selectedIds],
  );

  useEffect(() => {
    if (!dragging) return;

    const handleMouseMove = (e: MouseEvent) => {
      if (!dragStart.current) return;
      const dx = (e.clientX - dragStart.current.mouseX) / displayScale;
      const dy = (e.clientY - dragStart.current.mouseY) / displayScale;
      const orig = dragStart.current.origPositions;

      skipHistoryRef.current = true;
      setLayers((prev) =>
        prev.map((l) => {
          const o = orig.get(l.id);
          if (!o || !l.position) return l;
          return {
            ...l,
            position: {
              ...l.position,
              x: Math.round(o.x + dx),
              y: Math.round(o.y + dy),
            },
          };
        }),
      );
      skipHistoryRef.current = false;
    };

    const handleMouseUp = () => {
      setDragging(false);
      // Push final position to history
      setLayers((prev) => {
        pushHistory(prev);
        return prev;
      });
      dragStart.current = null;
    };

    window.addEventListener("mousemove", handleMouseMove);
    window.addEventListener("mouseup", handleMouseUp);
    return () => {
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("mouseup", handleMouseUp);
    };
  }, [dragging, displayScale, pushHistory]);

  // --- Position/Size input ---
  const handlePositionChange = useCallback(
    (field: keyof Position, value: number) => {
      updateLayers((prev) =>
        prev.map((l) =>
          selectedIds.has(l.id) && l.position
            ? { ...l, position: { ...l.position, [field]: value } }
            : l,
        ),
      );
    },
    [selectedIds, updateLayers],
  );

  // --- Context menu ---
  const handleContextMenu = useCallback(
    (e: React.MouseEvent, layerId: string) => {
      e.preventDefault();
      e.stopPropagation();
      if (!selectedIds.has(layerId)) {
        setSelectedIds(new Set([layerId]));
      }
      setContextMenu({ x: e.clientX, y: e.clientY });
    },
    [selectedIds],
  );

  // --- Rename (double-click) ---
  const [renamingId, setRenamingId] = useState<string | null>(null);
  const [renameValue, setRenameValue] = useState("");
  const renameInputRef = useRef<HTMLInputElement>(null);

  const handleStartRename = useCallback((layerId: string) => {
    const layer = layers.find((l) => l.id === layerId);
    if (!layer) return;
    setRenamingId(layerId);
    setRenameValue(layer.name);
  }, [layers]);

  const handleFinishRename = useCallback(() => {
    if (renamingId && renameValue.trim()) {
      updateLayers((prev) =>
        prev.map((l) => (l.id === renamingId ? { ...l, name: renameValue.trim() } : l)),
      );
    }
    setRenamingId(null);
  }, [renamingId, renameValue, updateLayers]);

  useEffect(() => {
    if (renamingId && renameInputRef.current) {
      renameInputRef.current.focus();
      renameInputRef.current.select();
    }
  }, [renamingId]);

  const handleDownloadSelected = useCallback(async () => {
    setContextMenu(null);
    const targets = layers.filter((l) => selectedIds.has(l.id) && l.image_url);
    for (let i = 0; i < targets.length; i++) {
      const layer = targets[i];
      const ext = layer.image_url!.split(".").pop() ?? "png";
      await downloadLayerImage(layer.image_url!, `${layer.name}.${ext}`);
      if (i < targets.length - 1) {
        await new Promise((r) => setTimeout(r, 500));
      }
    }
  }, [layers, selectedIds]);

  // --- Render ---
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

  const firstSelected = layers.find((l) => selectedIds.has(l.id));
  const canUndo = historyIndex > 0;
  const canRedo = historyIndex < history.length - 1;

  return (
    <main className="mx-auto max-w-7xl p-6">
      {/* Header */}
      <div className="mb-4 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">레이어 편집</h1>
          <p className="text-sm text-gray-500">
            {canvasSize.width} x {canvasSize.height}px | {layers.length}개 레이어
            {selectedIds.size > 1 && ` | ${selectedIds.size}개 선택됨`}
          </p>
        </div>
        <div className="flex items-center gap-2">
          {/* Undo/Redo buttons */}
          <button
            onClick={() => {
              if (canUndo) {
                skipHistoryRef.current = true;
                setLayers(history[historyIndex - 1]);
                setHistoryIndex((i) => i - 1);
                skipHistoryRef.current = false;
              }
            }}
            disabled={!canUndo}
            className="rounded p-1.5 text-gray-500 transition hover:bg-gray-100 disabled:opacity-30"
            title="실행 취소 (Ctrl+Z)"
          >
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M3 10h10a5 5 0 015 5v2M3 10l4-4m-4 4l4 4" />
            </svg>
          </button>
          <button
            onClick={() => {
              if (canRedo) {
                skipHistoryRef.current = true;
                setLayers(history[historyIndex + 1]);
                setHistoryIndex((i) => i + 1);
                skipHistoryRef.current = false;
              }
            }}
            disabled={!canRedo}
            className="rounded p-1.5 text-gray-500 transition hover:bg-gray-100 disabled:opacity-30"
            title="다시 실행 (Ctrl+Y)"
          >
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M21 10H11a5 5 0 00-5 5v2m15-7l-4-4m4 4l-4 4" />
            </svg>
          </button>

          <div className="mx-2 h-6 w-px bg-gray-200" />

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
        <div
          ref={containerRef}
          className="flex items-start justify-center rounded-xl bg-gray-100 p-4"
          onClick={() => setSelectedIds(new Set())}
        >
          <div
            className="relative overflow-hidden rounded-lg bg-white shadow-lg"
            style={{ width: displayW, height: displayH, cursor: dragging ? "grabbing" : "default" }}
          >
            {sortedLayers.map((layer) => {
              if (!layer.position || !layer.image_url) return null;
              const { x, y, w, h } = layer.position;
              const isSelected = selectedIds.has(layer.id);

              return (
                <img
                  key={layer.id}
                  src={`${API_BASE}${layer.image_url}`}
                  alt={`${layer.type} layer`}
                  draggable={false}
                  onClick={(e) => {
                    e.stopPropagation();
                    handleSelectLayer(layer.id, e.ctrlKey || e.metaKey);
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
              const isSelected = selectedIds.has(layer.id);
              return (
                <div
                  key={layer.id}
                  onClick={(e) => handleSelectLayer(layer.id, e.ctrlKey || e.metaKey)}
                  onDoubleClick={(e) => {
                    e.stopPropagation();
                    handleStartRename(layer.id);
                  }}
                  onContextMenu={(e) => handleContextMenu(e, layer.id)}
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

                  {/* Thumbnail */}
                  {layer.image_url && (
                    <div className="h-8 w-8 shrink-0 overflow-hidden rounded border bg-gray-50">
                      <img
                        src={`${API_BASE}${layer.image_url}`}
                        alt=""
                        className="h-full w-full object-contain"
                      />
                    </div>
                  )}

                  <div className="flex-1 min-w-0">
                    {renamingId === layer.id ? (
                      <input
                        ref={renameInputRef}
                        type="text"
                        value={renameValue}
                        onChange={(e) => setRenameValue(e.target.value)}
                        onBlur={handleFinishRename}
                        onKeyDown={(e) => {
                          if (e.key === "Enter") handleFinishRename();
                          if (e.key === "Escape") setRenamingId(null);
                        }}
                        onClick={(e) => e.stopPropagation()}
                        className="w-full rounded border border-blue-400 px-1.5 py-0.5 text-xs focus:outline-none"
                      />
                    ) : (
                      <>
                        <div className="flex items-center gap-1.5">
                          <span className={`rounded px-1.5 py-0.5 text-[10px] font-medium ${TYPE_COLORS[layer.type] ?? "bg-gray-100 text-gray-600"}`}>
                            {layer.type}
                          </span>
                          <span className="truncate text-xs text-gray-700">{layer.name}</span>
                        </div>
                        {layer.text_content && (
                          <p className="mt-0.5 truncate text-xs text-gray-400">{layer.text_content}</p>
                        )}
                      </>
                    )}
                  </div>

                  <span className="text-[10px] text-gray-300">{layer.z_index}</span>
                </div>
              );
            })}
          </div>

          {/* Selected Layer Controls */}
          {firstSelected && firstSelected.position && (
            <div className="rounded-xl bg-white p-4 shadow">
              <h3 className="mb-3 text-sm font-semibold">
                선택된 레이어 {selectedIds.size > 1 ? `(${selectedIds.size}개)` : ""}
              </h3>

              {/* Thumbnail preview */}
              {(() => {
                const selected = layers.filter((l) => selectedIds.has(l.id) && l.image_url);
                if (selected.length === 1) {
                  return (
                    <div className="mb-3 overflow-hidden rounded-lg border bg-gray-50">
                      <img
                        src={`${API_BASE}${selected[0].image_url}`}
                        alt={selected[0].name}
                        className="h-32 w-full object-contain"
                      />
                    </div>
                  );
                }
                if (selected.length > 1) {
                  return (
                    <div className="mb-3 grid grid-cols-3 gap-1 rounded-lg border bg-gray-50 p-1">
                      {selected.slice(0, 9).map((l) => (
                        <div key={l.id} className="overflow-hidden rounded bg-white">
                          <img
                            src={`${API_BASE}${l.image_url}`}
                            alt={l.name}
                            className="h-16 w-full object-contain"
                          />
                        </div>
                      ))}
                      {selected.length > 9 && (
                        <div className="flex h-16 items-center justify-center rounded bg-gray-100 text-xs text-gray-400">
                          +{selected.length - 9}
                        </div>
                      )}
                    </div>
                  );
                }
                return null;
              })()}

              {selectedIds.size === 1 && (
                <div className="mb-3 flex items-center gap-2">
                  <span className={`rounded px-1.5 py-0.5 text-[10px] font-medium ${TYPE_COLORS[firstSelected.type] ?? "bg-gray-100 text-gray-600"}`}>
                    {firstSelected.type}
                  </span>
                  {firstSelected.text_content && (
                    <span className="truncate text-xs text-gray-500">&ldquo;{firstSelected.text_content}&rdquo;</span>
                  )}
                </div>
              )}

              <p className="mb-1 text-[10px] font-medium text-gray-400">위치</p>
              <div className="mb-3 grid grid-cols-2 gap-2">
                {(["x", "y"] as const).map((field) => (
                  <label key={field} className="text-xs">
                    <span className="text-gray-400">{field.toUpperCase()}</span>
                    <input
                      type="number"
                      value={firstSelected.position![field]}
                      onChange={(e) => handlePositionChange(field, Number(e.target.value))}
                      className="mt-0.5 w-full rounded border px-2 py-1 text-sm focus:border-blue-500 focus:outline-none"
                    />
                  </label>
                ))}
              </div>

              <p className="mb-1 text-[10px] font-medium text-gray-400">크기</p>
              <div className="grid grid-cols-2 gap-2">
                {(["w", "h"] as const).map((field) => (
                  <label key={field} className="text-xs">
                    <span className="text-gray-400">{field === "w" ? "W" : "H"}</span>
                    <input
                      type="number"
                      value={firstSelected.position![field]}
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

      {/* Context Menu */}
      {contextMenu && (
        <div
          className="fixed z-50 rounded-lg border bg-white py-1 shadow-lg"
          style={{ left: contextMenu.x, top: contextMenu.y }}
        >
          <button
            onClick={handleDownloadSelected}
            className="flex w-full items-center gap-2 px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
          >
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
            </svg>
            {selectedIds.size > 1
              ? `${selectedIds.size}개 이미지로 다운로드`
              : "이미지로 다운로드"}
          </button>
        </div>
      )}
    </main>
  );
}
