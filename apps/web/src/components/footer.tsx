"use client";

import Link from "next/link";
import { useTranslation } from "@/lib/i18n";

export function Footer() {
  const { t } = useTranslation();

  return (
    <footer className="border-t bg-gray-50 px-6 py-10">
      <div className="mx-auto max-w-4xl">
        <div className="grid gap-8 sm:grid-cols-3">
          <div>
            <p className="mb-2 font-bold text-blue-600">UI2PSD Studio</p>
            <p className="text-sm text-gray-500">{t("footer.description")}</p>
          </div>
          <div>
            <p className="mb-2 text-sm font-semibold text-gray-700">{t("footer.service")}</p>
            <div className="space-y-1 text-sm text-gray-500">
              <Link href="/upload" className="block hover:text-gray-700">{t("nav.convert")}</Link>
              <Link href="/pricing" className="block hover:text-gray-700">{t("nav.pricing")}</Link>
            </div>
          </div>
          <div>
            <p className="mb-2 text-sm font-semibold text-gray-700">{t("footer.info")}</p>
            <p className="text-xs text-gray-400">{t("footer.notice")}</p>
          </div>
        </div>
        <div className="mt-8 border-t pt-4 text-center text-xs text-gray-400">
          {t("footer.rights")}
        </div>
      </div>
    </footer>
  );
}
