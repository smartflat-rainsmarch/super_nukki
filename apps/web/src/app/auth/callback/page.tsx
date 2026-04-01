"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { handleOAuthCallback } from "@/lib/auth";

export default function AuthCallbackPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [error, setError] = useState<string | null>(null);
  const processed = useRef(false);

  useEffect(() => {
    if (processed.current) return;
    processed.current = true;

    const code = searchParams.get("code");
    const provider = searchParams.get("provider");

    if (!code || !provider) {
      setError("인증 정보가 올바르지 않습니다.");
      return;
    }

    async function processCallback() {
      try {
        await handleOAuthCallback(code!, provider!);
        router.push("/upload");
      } catch (err) {
        setError(err instanceof Error ? err.message : "로그인에 실패했습니다.");
      }
    }

    processCallback();
  }, [searchParams, router]);

  if (error) {
    return (
      <main className="flex min-h-screen flex-col items-center justify-center p-8">
        <div className="w-full max-w-sm text-center">
          <p className="mb-4 text-red-600">{error}</p>
          <a href="/login" className="text-sm text-blue-600 underline">
            로그인 페이지로 돌아가기
          </a>
        </div>
      </main>
    );
  }

  return (
    <main className="flex min-h-screen items-center justify-center p-8">
      <div className="text-center">
        <div className="mb-4 h-8 w-8 animate-spin rounded-full border-4 border-blue-600 border-t-transparent mx-auto" />
        <p className="text-gray-500">로그인 처리 중...</p>
      </div>
    </main>
  );
}
