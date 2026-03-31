"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getMe, getToken, logout, type UserInfo } from "@/lib/auth";

export function Navbar() {
  const [user, setUser] = useState<UserInfo | null>(null);

  useEffect(() => {
    async function load() {
      const token = getToken();
      if (token) {
        const me = await getMe();
        setUser(me);
      }
    }
    load();
  }, []);

  return (
    <nav className="border-b bg-white">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-3">
        <Link href="/" className="text-xl font-bold text-blue-600">
          UI2PSD
        </Link>

        <div className="flex items-center gap-6 text-sm">
          <Link href="/upload" className="text-gray-600 hover:text-gray-900">
            변환하기
          </Link>
          <Link href="/pricing" className="text-gray-600 hover:text-gray-900">
            요금제
          </Link>

          {user ? (
            <>
              <Link href="/mypage" className="text-gray-600 hover:text-gray-900">
                마이페이지
              </Link>
              <button
                onClick={logout}
                className="text-gray-400 hover:text-gray-600"
              >
                로그아웃
              </button>
            </>
          ) : (
            <>
              <Link href="/login" className="text-gray-600 hover:text-gray-900">
                로그인
              </Link>
              <Link
                href="/register"
                className="rounded-lg bg-blue-600 px-4 py-1.5 text-white hover:bg-blue-700"
              >
                회원가입
              </Link>
            </>
          )}
        </div>
      </div>
    </nav>
  );
}
