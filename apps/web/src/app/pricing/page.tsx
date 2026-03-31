"use client";

import { authHeaders, getToken } from "@/lib/auth";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const PLANS = [
  {
    name: "무료",
    price: "$0",
    period: "",
    features: ["월 3회 변환", "최대 1024px", "기본 OCR", "기본 PSD 그룹"],
    planId: null,
  },
  {
    name: "일반",
    price: "$39",
    period: "/월",
    features: ["월 100회 변환", "HD 해상도", "고급 OCR (부분)", "고급 PSD 그룹", "PNG ZIP", "우선 처리"],
    planId: "basic_monthly",
    highlight: true,
  },
  {
    name: "프로",
    price: "$129",
    period: "/월",
    features: [
      "월 500회 변환", "4K 해상도", "고급 OCR 앙상블", "고급 PSD 그룹",
      "PNG ZIP", "JSON 메타데이터", "고급 인페인팅", "배치 처리", "API access", "최고 우선 처리",
    ],
    planId: "pro_monthly",
  },
];

async function handleCheckout(planId: string) {
  const token = getToken();
  if (!token) {
    window.location.href = "/login";
    return;
  }

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
  return (
    <main className="mx-auto max-w-5xl p-8">
      <h1 className="mb-2 text-center text-3xl font-bold">요금제</h1>
      <p className="mb-10 text-center text-gray-500">필요에 맞는 플랜을 선택하세요</p>

      <div className="grid gap-6 md:grid-cols-3">
        {PLANS.map((plan) => (
          <div
            key={plan.name}
            className={`rounded-xl border p-6 ${
              plan.highlight ? "border-blue-500 shadow-lg" : "border-gray-200"
            }`}
          >
            {plan.highlight && (
              <span className="mb-2 inline-block rounded bg-blue-600 px-2 py-0.5 text-xs text-white">
                인기
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
                  plan.highlight
                    ? "bg-blue-600 text-white hover:bg-blue-700"
                    : "border border-gray-300 text-gray-700 hover:bg-gray-50"
                }`}
              >
                시작하기
              </button>
            ) : (
              <span className="block w-full rounded-lg bg-gray-100 py-2 text-center text-sm text-gray-500">
                현재 플랜
              </span>
            )}
          </div>
        ))}
      </div>
    </main>
  );
}
