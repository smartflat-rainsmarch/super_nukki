"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { authHeaders, getMe, getToken, logout, type UserInfo } from "@/lib/auth";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface UsageInfo {
  plan: string;
  usage_count: number;
  limit: number;
  remaining: number;
  reset_date: string | null;
}

const PLAN_LABELS: Record<string, string> = {
  free: "무료",
  basic: "일반 ($39/월)",
  pro: "프로 ($129/월)",
};

export default function MyPage() {
  const [user, setUser] = useState<UserInfo | null>(null);
  const [usage, setUsage] = useState<UsageInfo | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      const token = getToken();
      if (!token) {
        window.location.href = "/login";
        return;
      }

      const me = await getMe();
      if (!me) {
        window.location.href = "/login";
        return;
      }
      setUser(me);

      const res = await fetch(`${API_BASE}/api/usage`, {
        headers: authHeaders(),
      });
      if (res.ok) {
        setUsage(await res.json());
      }

      setLoading(false);
    }
    load();
  }, []);

  if (loading) {
    return (
      <main className="flex min-h-screen items-center justify-center">
        <p className="text-gray-500">로딩 중...</p>
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-2xl p-8">
      <h1 className="mb-6 text-3xl font-bold">마이페이지</h1>

      {user && (
        <div className="mb-6 rounded-xl bg-white p-6 shadow">
          <h2 className="mb-3 text-lg font-semibold">계정 정보</h2>
          <p className="text-gray-600">{user.email}</p>
          <p className="mt-1 text-sm text-gray-500">
            플랜: {PLAN_LABELS[user.plan_type] ?? user.plan_type}
          </p>
        </div>
      )}

      {usage && (
        <div className="mb-6 rounded-xl bg-white p-6 shadow">
          <h2 className="mb-3 text-lg font-semibold">사용량</h2>
          <div className="mb-2 flex justify-between text-sm">
            <span>이번 달 사용</span>
            <span>
              {usage.usage_count} / {usage.limit}회
            </span>
          </div>
          <div className="h-2 w-full overflow-hidden rounded-full bg-gray-200">
            <div
              className="h-full rounded-full bg-blue-600"
              style={{
                width: `${Math.min(100, (usage.usage_count / usage.limit) * 100)}%`,
              }}
            />
          </div>
          <p className="mt-2 text-sm text-gray-500">
            남은 횟수: {usage.remaining}회
          </p>
          {usage.reset_date && (
            <p className="text-xs text-gray-400">
              리셋: {new Date(usage.reset_date).toLocaleDateString("ko-KR")}
            </p>
          )}
        </div>
      )}

      <div className="flex gap-3">
        <Link
          href="/pricing"
          className="rounded-lg border border-gray-300 px-4 py-2 text-sm transition hover:bg-gray-50"
        >
          플랜 변경
        </Link>
        <button
          onClick={logout}
          className="rounded-lg border border-red-300 px-4 py-2 text-sm text-red-600 transition hover:bg-red-50"
        >
          로그아웃
        </button>
      </div>
    </main>
  );
}
