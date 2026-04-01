"use client";

import { authHeaders, getToken } from "@/lib/auth";
import { useTranslation } from "@/lib/i18n";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function handleCheckout(planId: string) {
  const token = getToken();
  if (!token) { window.location.href = "/login"; return; }
  const res = await fetch(`${API_BASE}/api/billing/checkout`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ plan: planId }),
  });
  if (res.ok) {
    const data = await res.json();
    window.location.href = data.checkout_url;
  }
}

export default function PricingPage() {
  const { t } = useTranslation();

  const PLANS = [
    {
      name: t("pricing.free"), price: "$0", period: "",
      features: [`3 ${t("nav.convert")}/${t("pricing.perMonth")}`, "1024px max", "OCR", "PSD"],
      planId: null,
    },
    {
      name: t("pricing.basic"), price: "$39", period: t("pricing.perMonth"),
      features: [`100 ${t("nav.convert")}`, "HD", "OCR+", "PSD+", "PNG ZIP"],
      planId: "basic_monthly", highlight: true,
    },
    {
      name: t("pricing.pro"), price: "$129", period: t("pricing.perMonth"),
      features: [`500 ${t("nav.convert")}`, "4K", "OCR Ensemble", "PSD+", "PNG ZIP", "JSON", "API"],
      planId: "pro_monthly",
    },
  ];

  return (
    <main className="mx-auto max-w-5xl p-8">
      <h1 className="mb-2 text-center text-3xl font-bold">{t("pricing.title")}</h1>
      <p className="mb-10 text-center text-gray-500">{t("pricing.subtitle")}</p>

      <div className="grid gap-6 md:grid-cols-3">
        {PLANS.map((plan) => (
          <div
            key={plan.name}
            className={`rounded-xl border p-6 ${plan.highlight ? "border-blue-500 shadow-lg" : "border-gray-200"}`}
          >
            {plan.highlight && (
              <span className="mb-2 inline-block rounded bg-blue-600 px-2 py-0.5 text-xs text-white">
                {t("pricing.popular")}
              </span>
            )}
            <h2 className="text-xl font-bold">{plan.name}</h2>
            <div className="my-4">
              <span className="text-3xl font-bold">{plan.price}</span>
              <span className="text-gray-500">{plan.period}</span>
            </div>
            <ul className="mb-6 space-y-2">
              {plan.features.map((f) => (
                <li key={f} className="flex items-start gap-2 text-sm text-gray-600">
                  <span className="mt-0.5 text-green-500">&#10003;</span>
                  {f}
                </li>
              ))}
            </ul>
            {plan.planId ? (
              <button
                onClick={() => handleCheckout(plan.planId!)}
                className={`w-full rounded-lg py-2 transition ${
                  plan.highlight ? "bg-blue-600 text-white hover:bg-blue-700" : "border border-gray-300 text-gray-700 hover:bg-gray-50"
                }`}
              >
                {t("pricing.startBtn")}
              </button>
            ) : (
              <span className="block w-full rounded-lg bg-gray-100 py-2 text-center text-sm text-gray-500">
                {t("pricing.currentPlan")}
              </span>
            )}
          </div>
        ))}
      </div>
    </main>
  );
}
