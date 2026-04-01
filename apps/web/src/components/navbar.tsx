"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getMe, getToken, logout, type UserInfo } from "@/lib/auth";
import { LOCALE_NAMES, SUPPORTED_LOCALES, useTranslation } from "@/lib/i18n";

export function Navbar() {
  const [user, setUser] = useState<UserInfo | null>(null);
  const { t, locale, setLocale } = useTranslation();

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

        <div className="flex items-center gap-4 text-sm">
          <Link href="/upload" className="text-gray-600 hover:text-gray-900">
            {t("nav.convert")}
          </Link>
          <Link href="/pricing" className="text-gray-600 hover:text-gray-900">
            {t("nav.pricing")}
          </Link>

          {user ? (
            <>
              <Link href="/mypage" className="text-gray-600 hover:text-gray-900">
                {t("nav.mypage")}
              </Link>
              <button
                onClick={logout}
                className="text-gray-400 hover:text-gray-600"
              >
                {t("nav.logout")}
              </button>
            </>
          ) : (
            <>
              <Link href="/login" className="text-gray-600 hover:text-gray-900">
                {t("nav.login")}
              </Link>
              <Link
                href="/register"
                className="rounded-lg bg-blue-600 px-4 py-1.5 text-white hover:bg-blue-700"
              >
                {t("nav.register")}
              </Link>
            </>
          )}

          {/* Language selector */}
          <select
            value={locale}
            onChange={(e) => setLocale(e.target.value)}
            className="rounded border border-gray-200 bg-white px-2 py-1 text-xs text-gray-600 focus:border-blue-500 focus:outline-none"
          >
            {SUPPORTED_LOCALES.map((loc) => (
              <option key={loc} value={loc}>
                {LOCALE_NAMES[loc] ?? loc}
              </option>
            ))}
          </select>
        </div>
      </div>
    </nav>
  );
}
