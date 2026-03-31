"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";

const STEPS = [
  {
    title: "UI 이미지를 업로드하세요",
    desc: "PNG, JPG, WebP 형식의 UI 스크린샷을 드래그하거나 붙여넣기하세요. 모바일 UI에 최적화되어 있습니다.",
    cta: "다음",
  },
  {
    title: "AI가 자동으로 분석합니다",
    desc: "텍스트 추출, 요소 분리, 배경 복원을 20초 이내에 완료합니다. 실시간으로 진행 상황을 확인할 수 있어요.",
    cta: "다음",
  },
  {
    title: "PSD 파일을 다운로드하세요",
    desc: "레이어가 정리된 PSD 파일을 Photoshop에서 바로 편집할 수 있습니다. 에셋 PNG도 함께 제공됩니다.",
    cta: "첫 이미지 업로드하기",
  },
];

export default function OnboardingPage() {
  const router = useRouter();
  const [step, setStep] = useState(0);

  const handleNext = () => {
    if (step < STEPS.length - 1) {
      setStep(step + 1);
    } else {
      router.push("/upload");
    }
  };

  const current = STEPS[step];

  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-8">
      <div className="w-full max-w-md text-center">
        {/* Progress */}
        <div className="mb-8 flex justify-center gap-2">
          {STEPS.map((_, i) => (
            <div
              key={i}
              className={`h-2 w-12 rounded-full transition ${
                i <= step ? "bg-blue-600" : "bg-gray-200"
              }`}
            />
          ))}
        </div>

        {/* Step number */}
        <div className="mb-4 inline-flex h-12 w-12 items-center justify-center rounded-full bg-blue-100 text-xl font-bold text-blue-600">
          {step + 1}
        </div>

        <h1 className="mb-3 text-2xl font-bold">{current.title}</h1>
        <p className="mb-8 text-gray-600">{current.desc}</p>

        <button
          onClick={handleNext}
          className="w-full rounded-lg bg-blue-600 py-3 text-white transition hover:bg-blue-700"
        >
          {current.cta}
        </button>

        {step < STEPS.length - 1 && (
          <button
            onClick={() => router.push("/upload")}
            className="mt-3 text-sm text-gray-400 underline"
          >
            건너뛰기
          </button>
        )}
      </div>
    </main>
  );
}
