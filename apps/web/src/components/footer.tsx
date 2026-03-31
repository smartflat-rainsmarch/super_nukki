import Link from "next/link";

export function Footer() {
  return (
    <footer className="border-t bg-gray-50 px-6 py-10">
      <div className="mx-auto max-w-4xl">
        <div className="grid gap-8 sm:grid-cols-3">
          <div>
            <p className="mb-2 font-bold text-blue-600">UI2PSD Studio</p>
            <p className="text-sm text-gray-500">
              AI가 UI 이미지를 편집 가능한 PSD 레이어 파일로 변환합니다
            </p>
          </div>
          <div>
            <p className="mb-2 text-sm font-semibold text-gray-700">서비스</p>
            <div className="space-y-1 text-sm text-gray-500">
              <Link href="/upload" className="block hover:text-gray-700">변환하기</Link>
              <Link href="/pricing" className="block hover:text-gray-700">요금제</Link>
            </div>
          </div>
          <div>
            <p className="mb-2 text-sm font-semibold text-gray-700">안내</p>
            <p className="text-xs text-gray-400">
              결과물은 실무용 편집 초안입니다. AI 분석 특성상 완벽한 복원을 보장하지 않습니다.
            </p>
          </div>
        </div>
        <div className="mt-8 border-t pt-4 text-center text-xs text-gray-400">
          UI2PSD Studio. All rights reserved.
        </div>
      </div>
    </footer>
  );
}
