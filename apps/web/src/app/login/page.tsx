"use client";

import { useCallback, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { getGoogleLoginUrl, getKakaoLoginUrl, login } from "@/lib/auth";
import { useTranslation } from "@/lib/i18n";

export default function LoginPage() {
  const router = useRouter();
  const { t } = useTranslation();
  const [showEmailForm, setShowEmailForm] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleGoogle = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const url = await getGoogleLoginUrl();
      window.location.href = url;
    } catch {
      setError(t("common.error"));
      setLoading(false);
    }
  }, [t]);

  const handleKakao = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const url = await getKakaoLoginUrl();
      window.location.href = url;
    } catch {
      setError(t("common.error"));
      setLoading(false);
    }
  }, [t]);

  const handleEmailLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      await login(email, password);
      router.push("/upload");
    } catch (err) {
      setError(err instanceof Error ? err.message : t("common.error"));
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="flex min-h-screen items-center justify-center p-8">
      <div className="w-full max-w-sm space-y-4">
        <h1 className="text-center text-2xl font-bold">{t("login.title")}</h1>
        <p className="text-center text-sm text-gray-500">{t("login.welcome")}</p>

        {error && (
          <p className="rounded-lg bg-red-50 px-4 py-2 text-center text-sm text-red-600">{error}</p>
        )}

        <button onClick={handleGoogle} disabled={loading} className="flex w-full items-center justify-center gap-3 rounded-lg border border-gray-300 bg-white py-3 text-sm font-medium text-gray-700 transition hover:bg-gray-50 disabled:opacity-50">
          <svg className="h-5 w-5" viewBox="0 0 24 24"><path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z"/><path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/><path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/><path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/></svg>
          {t("login.googleBtn")}
        </button>

        <button onClick={handleKakao} disabled={loading} className="flex w-full items-center justify-center gap-3 rounded-lg py-3 text-sm font-medium text-gray-900 transition hover:brightness-95 disabled:opacity-50" style={{ backgroundColor: "#FEE500" }}>
          <svg className="h-5 w-5" viewBox="0 0 24 24"><path fill="#000000" d="M12 3C6.48 3 2 6.36 2 10.5c0 2.67 1.77 5.02 4.44 6.36-.14.52-.92 3.37-.95 3.58 0 0-.02.16.08.22.1.06.22.01.22.01.29-.04 3.37-2.2 3.9-2.57.74.1 1.51.16 2.31.16 5.52 0 10-3.36 10-7.5S17.52 3 12 3z"/></svg>
          {t("login.kakaoBtn")}
        </button>

        <div className="flex items-center gap-3">
          <div className="h-px flex-1 bg-gray-200" />
          <span className="text-xs text-gray-400">{t("login.or")}</span>
          <div className="h-px flex-1 bg-gray-200" />
        </div>

        {!showEmailForm ? (
          <button onClick={() => setShowEmailForm(true)} className="flex w-full items-center justify-center gap-3 rounded-lg border border-gray-300 bg-gray-50 py-3 text-sm font-medium text-gray-600 transition hover:bg-gray-100">
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}><path strokeLinecap="round" strokeLinejoin="round" d="M21.75 6.75v10.5a2.25 2.25 0 0 1-2.25 2.25h-15a2.25 2.25 0 0 1-2.25-2.25V6.75m19.5 0A2.25 2.25 0 0 0 19.5 4.5h-15a2.25 2.25 0 0 0-2.25 2.25m19.5 0v.243a2.25 2.25 0 0 1-1.07 1.916l-7.5 4.615a2.25 2.25 0 0 1-2.36 0L3.32 8.91a2.25 2.25 0 0 1-1.07-1.916V6.75"/></svg>
            {t("login.emailBtn")}
          </button>
        ) : (
          <form onSubmit={handleEmailLogin} className="space-y-3">
            <input type="email" placeholder={t("login.email")} value={email} onChange={(e) => setEmail(e.target.value)} required className="w-full rounded-lg border px-4 py-3 text-sm focus:border-blue-500 focus:outline-none" />
            <input type="password" placeholder={t("login.password")} value={password} onChange={(e) => setPassword(e.target.value)} required className="w-full rounded-lg border px-4 py-3 text-sm focus:border-blue-500 focus:outline-none" />
            <button type="submit" disabled={loading} className="w-full rounded-lg bg-blue-600 py-3 text-sm text-white transition hover:bg-blue-700 disabled:opacity-50">
              {loading ? t("login.loading") : t("login.submit")}
            </button>
          </form>
        )}

        <p className="text-center text-sm text-gray-500">
          {t("login.noAccount")}{" "}
          <Link href="/register" className="text-blue-600 underline">{t("login.registerLink")}</Link>
        </p>
      </div>
    </main>
  );
}
