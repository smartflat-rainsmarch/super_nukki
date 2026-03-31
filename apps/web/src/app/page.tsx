import Link from "next/link";

const FEATURES = [
  {
    title: "AI 요소 분리",
    desc: "버튼, 카드, 아이콘, 배경을 자동으로 레이어별 분리",
    icon: "🔍",
  },
  {
    title: "텍스트 OCR",
    desc: "폰트 크기, 색상, 정렬까지 자동 추정하여 편집 가능한 텍스트 레이어 생성",
    icon: "📝",
  },
  {
    title: "배경 복원",
    desc: "텍스트/아이콘 제거 후 자연스러운 배경 인페인팅",
    icon: "🎨",
  },
  {
    title: "PSD 레이어 출력",
    desc: "그룹 구조가 정리된 PSD 파일로 Photoshop에서 바로 편집",
    icon: "📂",
  },
];

const USE_CASES = [
  { role: "프론트엔드 개발자", scenario: "AI가 생성한 UI 시안을 컴포넌트 단위로 해석" },
  { role: "디자이너", scenario: "PNG/JPG 캡처를 편집 가능한 PSD 레이어로 복원" },
  { role: "에이전시", scenario: "클라이언트가 보낸 캡처본을 즉시 편집 가능 형태로 변환" },
  { role: "스타트업 PM", scenario: "생성형 AI 결과물을 수정/개발 가능한 구조로 분해" },
];

export default function LandingPage() {
  return (
    <>
      {/* Hero */}
      <section className="flex min-h-[80vh] flex-col items-center justify-center px-6 text-center">
        <h1 className="mb-4 text-5xl font-extrabold leading-tight tracking-tight md:text-6xl">
          UI 이미지 한 장을
          <br />
          <span className="text-blue-600">편집 가능한 PSD</span>로
        </h1>
        <p className="mb-8 max-w-xl text-lg text-gray-600">
          AI가 UI 스크린샷을 분석하여 레이어별로 분리하고,
          텍스트를 추출하고, 배경을 복원한 PSD 파일을 생성합니다.
        </p>
        <div className="flex gap-4">
          <Link
            href="/upload"
            className="rounded-lg bg-blue-600 px-8 py-3 text-lg font-medium text-white transition hover:bg-blue-700"
          >
            무료로 시작하기
          </Link>
          <Link
            href="/pricing"
            className="rounded-lg border border-gray-300 px-8 py-3 text-lg font-medium text-gray-700 transition hover:bg-gray-50"
          >
            요금제 보기
          </Link>
        </div>
        <p className="mt-4 text-sm text-gray-400">
          가입 없이 월 3회 무료 체험 가능
        </p>
      </section>

      {/* Before / After */}
      <section className="bg-gray-50 px-6 py-20">
        <div className="mx-auto max-w-4xl text-center">
          <h2 className="mb-10 text-3xl font-bold">Before → After</h2>
          <div className="grid gap-6 md:grid-cols-2">
            <div className="rounded-xl bg-white p-6 shadow">
              <div className="mb-3 flex h-48 items-center justify-center rounded-lg bg-gray-100">
                <span className="text-4xl text-gray-300">PNG</span>
              </div>
              <p className="font-medium text-gray-500">UI 스크린샷 (단일 이미지)</p>
            </div>
            <div className="rounded-xl bg-white p-6 shadow ring-2 ring-blue-200">
              <div className="mb-3 flex h-48 items-center justify-center rounded-lg bg-blue-50">
                <div className="space-y-1 text-left text-sm text-blue-700">
                  <p>📁 Header</p>
                  <p className="pl-4">📝 Title Text</p>
                  <p>📁 Card</p>
                  <p className="pl-4">🖼 Image</p>
                  <p className="pl-4">📝 Description</p>
                  <p>📁 CTA</p>
                  <p className="pl-4">🔘 Button</p>
                  <p>📁 Background (restored)</p>
                </div>
              </div>
              <p className="font-medium text-blue-600">PSD 레이어 파일 (편집 가능)</p>
            </div>
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="px-6 py-20">
        <div className="mx-auto max-w-4xl">
          <h2 className="mb-10 text-center text-3xl font-bold">하나의 파이프라인으로</h2>
          <div className="grid gap-6 sm:grid-cols-2">
            {FEATURES.map((f) => (
              <div key={f.title} className="rounded-xl border border-gray-200 p-6">
                <span className="mb-2 block text-2xl">{f.icon}</span>
                <h3 className="mb-1 text-lg font-semibold">{f.title}</h3>
                <p className="text-sm text-gray-600">{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Use Cases */}
      <section className="bg-gray-50 px-6 py-20">
        <div className="mx-auto max-w-4xl">
          <h2 className="mb-10 text-center text-3xl font-bold">누가 사용하나요?</h2>
          <div className="grid gap-4 sm:grid-cols-2">
            {USE_CASES.map((uc) => (
              <div key={uc.role} className="rounded-xl bg-white p-5 shadow-sm">
                <p className="mb-1 font-semibold">{uc.role}</p>
                <p className="text-sm text-gray-600">{uc.scenario}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="px-6 py-20 text-center">
        <h2 className="mb-4 text-3xl font-bold">지금 바로 시작하세요</h2>
        <p className="mb-8 text-gray-600">
          실무에서 편집 가능한 초안을 AI가 만들어 드립니다
        </p>
        <Link
          href="/register"
          className="rounded-lg bg-blue-600 px-8 py-3 text-lg font-medium text-white transition hover:bg-blue-700"
        >
          무료 체험 시작
        </Link>
      </section>
    </>
  );
}
