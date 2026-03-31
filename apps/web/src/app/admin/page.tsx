"use client";

import { useEffect, useState } from "react";
import { authHeaders } from "@/lib/auth";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface Stats {
  users: { total: number; by_plan: Record<string, number> };
  projects: { total: number };
  jobs: { total: number; completed: number; failed: number; success_rate: number };
}

interface UserItem {
  id: string;
  email: string;
  plan_type: string;
  created_at: string | null;
}

export default function AdminPage() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [users, setUsers] = useState<UserItem[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const [statsRes, usersRes] = await Promise.all([
          fetch(`${API_BASE}/api/admin/stats`, { headers: authHeaders() }),
          fetch(`${API_BASE}/api/admin/users`, { headers: authHeaders() }),
        ]);

        if (!statsRes.ok) {
          setError("관리자 권한이 필요합니다.");
          return;
        }

        setStats(await statsRes.json());
        if (usersRes.ok) {
          const data = await usersRes.json();
          setUsers(data.users);
        }
      } catch {
        setError("데이터를 불러올 수 없습니다.");
      }
    }
    load();
  }, []);

  if (error) {
    return (
      <main className="flex min-h-screen items-center justify-center">
        <p className="text-red-600">{error}</p>
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-5xl p-8">
      <h1 className="mb-6 text-3xl font-bold">관리자 대시보드</h1>

      {stats && (
        <div className="mb-8 grid gap-4 sm:grid-cols-4">
          <StatCard label="전체 사용자" value={stats.users.total} />
          <StatCard label="전체 프로젝트" value={stats.projects.total} />
          <StatCard label="성공률" value={`${stats.jobs.success_rate}%`} />
          <StatCard label="실패 작업" value={stats.jobs.failed} color="red" />
        </div>
      )}

      {stats && (
        <div className="mb-8 rounded-xl bg-white p-6 shadow">
          <h2 className="mb-3 text-lg font-semibold">플랜별 사용자</h2>
          <div className="flex gap-4">
            {Object.entries(stats.users.by_plan).map(([plan, count]) => (
              <div key={plan} className="rounded-lg bg-gray-50 px-4 py-2">
                <span className="text-sm font-medium capitalize">{plan}</span>
                <span className="ml-2 text-lg font-bold">{count}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="rounded-xl bg-white p-6 shadow">
        <h2 className="mb-3 text-lg font-semibold">사용자 목록</h2>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="border-b text-gray-500">
              <tr>
                <th className="pb-2">이메일</th>
                <th className="pb-2">플랜</th>
                <th className="pb-2">가입일</th>
              </tr>
            </thead>
            <tbody>
              {users.map((user) => (
                <tr key={user.id} className="border-b last:border-0">
                  <td className="py-2">{user.email}</td>
                  <td className="py-2">
                    <span className="rounded bg-blue-50 px-2 py-0.5 text-xs capitalize">
                      {user.plan_type}
                    </span>
                  </td>
                  <td className="py-2 text-gray-500">
                    {user.created_at
                      ? new Date(user.created_at).toLocaleDateString("ko-KR")
                      : "-"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </main>
  );
}

function StatCard({
  label,
  value,
  color = "blue",
}: {
  label: string;
  value: string | number;
  color?: string;
}) {
  return (
    <div className="rounded-xl bg-white p-4 shadow">
      <p className="text-sm text-gray-500">{label}</p>
      <p className={`text-2xl font-bold ${color === "red" ? "text-red-600" : "text-gray-900"}`}>
        {value}
      </p>
    </div>
  );
}
