import Link from "next/link";

export default function HomePage() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-8">
      <h1 className="mb-4 text-4xl font-bold">UI2PSD Studio</h1>
      <p className="mb-8 text-lg text-gray-600">
        UI 이미지를 편집 가능한 PSD 레이어 파일로 변환합니다
      </p>
      <Link
        href="/upload"
        className="rounded-lg bg-blue-600 px-6 py-3 text-white transition hover:bg-blue-700"
      >
        시작하기
      </Link>
    </main>
  );
}
