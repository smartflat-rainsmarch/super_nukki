export default async function ProjectPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;

  return (
    <main className="flex min-h-screen flex-col items-center p-8">
      <h1 className="mb-4 text-3xl font-bold">프로젝트 상세</h1>
      <p className="mb-4 text-gray-600">Project ID: {id}</p>
      <p className="text-gray-500">처리 결과가 여기에 표시됩니다</p>
    </main>
  );
}
