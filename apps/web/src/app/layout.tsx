import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "UI2PSD Studio",
  description: "AI가 UI 이미지를 편집 가능한 PSD 레이어 파일로 변환합니다",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ko">
      <body className="min-h-screen bg-gray-50 text-gray-900 antialiased">
        {children}
      </body>
    </html>
  );
}
