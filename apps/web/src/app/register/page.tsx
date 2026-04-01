"use client";

import { useCallback, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { getGoogleLoginUrl, getKakaoLoginUrl } from "@/lib/auth";
import { useTranslation } from "@/lib/i18n";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8001";

type Step = "email" | "verify" | "password";

export default function RegisterPage() {
  const router = useRouter();
  const { t } = useTranslation();
  const [step, setStep] = useState<Step>("email");
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [verifiedToken, setVerifiedToken] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [devCode, setDevCode] = useState<string | null>(null);

  const handleGoogle = useCallback(async () => {
    setLoading(true);
    try { window.location.href = await getGoogleLoginUrl(); }
    catch { setError(t("common.error")); setLoading(false); }
  }, [t]);

  const handleKakao = useCallback(async () => {
    setLoading(true);
    try { window.location.href = await getKakaoLoginUrl(); }
    catch { setError(t("common.error")); setLoading(false); }
  }, [t]);

  const handleSendCode = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/auth/send-code`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail);
      if (data.dev_code) setDevCode(data.dev_code);
      setStep("verify");
    } catch (err) {
      setError(err instanceof Error ? err.message : t("common.error"));
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyCode = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/auth/verify-code`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, code }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail);
      setVerifiedToken(data.verified_token);
      setStep("password");
    } catch (err) {
      setError(err instanceof Error ? err.message : t("common.error"));
    } finally {
      setLoading(false);
    }
  };

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    if (password !== confirm) { setError(t("register.passwordMismatch")); return; }
    if (password.length < 8) { setError(t("register.passwordShort")); return; }

    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/auth/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password, verified_token: verifiedToken }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail);
      localStorage.setItem("access_token", data.access_token);
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
        <h1 className="text-center text-2xl font-bold">{t("register.title")}</h1>
        <p className="text-center text-sm text-gray-500">{t("register.subtitle")}</p>

        {error && <p className="rounded-lg bg-red-50 px-4 py-2 text-center text-sm text-red-600">{error}</p>}

        {/* Step indicator */}
        <div className="flex justify-center gap-2">
          {(["email", "verify", "password"] as Step[]).map((s, i) => (
            <div key={s} className={`h-1.5 w-10 rounded-full ${
              (["email", "verify", "password"] as Step[]).indexOf(step) >= i ? "bg-blue-600" : "bg-gray-200"
            }`} />
          ))}
        </div>

        {step === "email" && (
          <>
            <button onClick={handleGoogle} disabled={loading} className="flex w-full items-center justify-center gap-3 rounded-lg border border-gray-300 bg-white py-3 text-sm font-medium text-gray-700 transition hover:bg-gray-50 disabled:opacity-50">
              <svg className="h-5 w-5" viewBox="0 0 24 24"><path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z"/><path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/><path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/><path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/></svg>
              {t("login.googleBtn")}
            </button>
            <button onClick={handleKakao} disabled={loading} className="flex w-full items-center justify-center gap-3 rounded-lg py-3 text-sm font-medium text-gray-900 transition hover:brightness-95 disabled:opacity-50" style={{ backgroundColor: "#FEE500" }}>
              <svg className="h-5 w-5" viewBox="0 0 24 24"><path fill="#000" d="M12 3C6.48 3 2 6.36 2 10.5c0 2.67 1.77 5.02 4.44 6.36-.14.52-.92 3.37-.95 3.58 0 0-.02.16.08.22.1.06.22.01.22.01.29-.04 3.37-2.2 3.9-2.57.74.1 1.51.16 2.31.16 5.52 0 10-3.36 10-7.5S17.52 3 12 3z"/></svg>
              {t("login.kakaoBtn")}
            </button>
            <div className="flex items-center gap-3">
              <div className="h-px flex-1 bg-gray-200" />
              <span className="text-xs text-gray-400">{t("login.or")}</span>
              <div className="h-px flex-1 bg-gray-200" />
            </div>
            <form onSubmit={handleSendCode} className="space-y-3">
              <input type="email" placeholder={t("login.email")} value={email} onChange={(e) => setEmail(e.target.value)} required className="w-full rounded-lg border px-4 py-3 text-sm focus:border-blue-500 focus:outline-none" />
              <button type="submit" disabled={loading} className="w-full rounded-lg bg-blue-600 py-3 text-sm text-white transition hover:bg-blue-700 disabled:opacity-50">
                {loading ? t("common.loading") : t("register.sendCode")}
              </button>
            </form>
          </>
        )}

        {step === "verify" && (
          <form onSubmit={handleVerifyCode} className="space-y-3">
            <p className="text-center text-sm text-gray-600">
              <span className="font-medium">{email}</span> {t("register.codeSent")}
            </p>
            {devCode && (
              <div className="rounded-lg bg-amber-50 px-4 py-2 text-center text-sm">
                <span className="text-amber-600">[DEV] </span>
                <span className="font-mono font-bold text-amber-800">{devCode}</span>
              </div>
            )}
            <input
              type="text"
              placeholder={t("register.codePlaceholder")}
              value={code}
              onChange={(e) => setCode(e.target.value.replace(/\D/g, "").slice(0, 6))}
              maxLength={6}
              required
              className="w-full rounded-lg border px-4 py-3 text-center text-lg font-mono tracking-widest focus:border-blue-500 focus:outline-none"
            />
            <button type="submit" disabled={loading || code.length !== 6} className="w-full rounded-lg bg-blue-600 py-3 text-sm text-white transition hover:bg-blue-700 disabled:opacity-50">
              {loading ? t("common.loading") : t("register.verifyBtn")}
            </button>
            <button type="button" onClick={() => { setStep("email"); setError(null); setCode(""); setDevCode(null); }} className="w-full text-center text-sm text-gray-400 hover:text-gray-600">
              {t("register.resendCode")}
            </button>
          </form>
        )}

        {step === "password" && (
          <form onSubmit={handleRegister} className="space-y-3">
            <p className="text-center text-sm text-green-600">{t("register.verified")}</p>
            <input type="password" placeholder={t("register.passwordPlaceholder")} value={password} onChange={(e) => setPassword(e.target.value)} required className="w-full rounded-lg border px-4 py-3 text-sm focus:border-blue-500 focus:outline-none" />
            <input type="password" placeholder={t("register.confirmPlaceholder")} value={confirm} onChange={(e) => setConfirm(e.target.value)} required className="w-full rounded-lg border px-4 py-3 text-sm focus:border-blue-500 focus:outline-none" />
            <button type="submit" disabled={loading} className="w-full rounded-lg bg-blue-600 py-3 text-sm text-white transition hover:bg-blue-700 disabled:opacity-50">
              {loading ? t("register.loading") : t("register.submit")}
            </button>
          </form>
        )}

        <p className="text-center text-sm text-gray-500">
          {t("register.hasAccount")}{" "}
          <Link href="/login" className="text-blue-600 underline">{t("register.loginLink")}</Link>
        </p>
      </div>
    </main>
  );
}
