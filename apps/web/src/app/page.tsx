"use client";

import Link from "next/link";
import { useTranslation } from "@/lib/i18n";

export default function LandingPage() {
  const { t } = useTranslation();

  const FEATURES = [
    { title: t("landing.feat1Title"), desc: t("landing.feat1Desc"), icon: "1" },
    { title: t("landing.feat2Title"), desc: t("landing.feat2Desc"), icon: "2" },
    { title: t("landing.feat3Title"), desc: t("landing.feat3Desc"), icon: "3" },
    { title: t("landing.feat4Title"), desc: t("landing.feat4Desc"), icon: "4" },
  ];

  return (
    <>
      <section className="flex min-h-[80vh] flex-col items-center justify-center px-6 text-center">
        <h1 className="mb-4 text-5xl font-extrabold leading-tight tracking-tight md:text-6xl">
          {t("landing.title1")}
          <br />
          <span className="text-blue-600">{t("landing.titleHighlight")}</span>
          {t("landing.titleSuffix")}
        </h1>
        <p className="mb-8 max-w-xl text-lg text-gray-600">{t("landing.subtitle")}</p>
        <div className="flex gap-4">
          <Link href="/upload" className="rounded-lg bg-blue-600 px-8 py-3 text-lg font-medium text-white transition hover:bg-blue-700">
            {t("landing.cta")}
          </Link>
          <Link href="/pricing" className="rounded-lg border border-gray-300 px-8 py-3 text-lg font-medium text-gray-700 transition hover:bg-gray-50">
            {t("landing.viewPricing")}
          </Link>
        </div>
        <p className="mt-4 text-sm text-gray-400">{t("landing.freeTrial")}</p>
      </section>

      <section className="bg-gray-50 px-6 py-20">
        <div className="mx-auto max-w-4xl text-center">
          <h2 className="mb-10 text-3xl font-bold">{t("landing.beforeAfter")}</h2>
          <div className="grid gap-6 md:grid-cols-2">
            <div className="rounded-xl bg-white p-6 shadow">
              <div className="mb-3 flex h-48 items-center justify-center rounded-lg bg-gray-100">
                <span className="text-4xl text-gray-300">PNG</span>
              </div>
              <p className="font-medium text-gray-500">{t("landing.beforeLabel")}</p>
            </div>
            <div className="rounded-xl bg-white p-6 shadow ring-2 ring-blue-200">
              <div className="mb-3 flex h-48 items-center justify-center rounded-lg bg-blue-50">
                <div className="space-y-1 text-left text-sm text-blue-700">
                  <p>Header</p>
                  <p className="pl-4">Title Text</p>
                  <p>Card</p>
                  <p className="pl-4">Image</p>
                  <p className="pl-4">Description</p>
                  <p>CTA</p>
                  <p className="pl-4">Button</p>
                  <p>Background (restored)</p>
                </div>
              </div>
              <p className="font-medium text-blue-600">{t("landing.afterLabel")}</p>
            </div>
          </div>
        </div>
      </section>

      <section className="px-6 py-20">
        <div className="mx-auto max-w-4xl">
          <h2 className="mb-10 text-center text-3xl font-bold">{t("landing.featuresTitle")}</h2>
          <div className="grid gap-6 sm:grid-cols-2">
            {FEATURES.map((f) => (
              <div key={f.icon} className="rounded-xl border border-gray-200 p-6">
                <span className="mb-2 flex h-8 w-8 items-center justify-center rounded-full bg-blue-100 text-sm font-bold text-blue-600">
                  {f.icon}
                </span>
                <h3 className="mb-1 text-lg font-semibold">{f.title}</h3>
                <p className="text-sm text-gray-600">{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="px-6 py-20 text-center">
        <h2 className="mb-4 text-3xl font-bold">{t("landing.ctaBottom")}</h2>
        <p className="mb-8 text-gray-600">{t("landing.ctaBottomSub")}</p>
        <Link href="/register" className="rounded-lg bg-blue-600 px-8 py-3 text-lg font-medium text-white transition hover:bg-blue-700">
          {t("landing.ctaBottomBtn")}
        </Link>
      </section>
    </>
  );
}
