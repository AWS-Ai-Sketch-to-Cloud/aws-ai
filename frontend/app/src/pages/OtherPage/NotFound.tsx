import { Link } from "react-router";
import PageMeta from "../../components/common/PageMeta";

export default function NotFound() {
  return (
    <>
      <PageMeta
        title="페이지를 찾을 수 없음 | Sketch-to-Cloud"
        description="요청한 페이지가 존재하지 않습니다."
      />
      <div className="relative z-1 flex min-h-screen flex-col items-center justify-center overflow-hidden p-6">
        <div className="mx-auto w-full max-w-[242px] text-center sm:max-w-[472px]">
          <h1 className="mb-4 text-title-md font-bold text-gray-800 dark:text-white/90 xl:text-title-2xl">
            404
          </h1>

          <p className="mb-6 text-base text-gray-700 dark:text-gray-400 sm:text-lg">
            요청한 페이지를 찾을 수 없습니다.
          </p>

          <Link
            to="/"
            className="inline-flex items-center justify-center rounded-lg border border-gray-300 bg-white px-5 py-3.5 text-sm font-medium text-gray-700 shadow-theme-xs hover:bg-gray-50 hover:text-gray-800 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-400 dark:hover:bg-white/[0.03] dark:hover:text-gray-200"
          >
            콘솔로 돌아가기
          </Link>
        </div>
        <p className="absolute text-sm text-center text-gray-500 -translate-x-1/2 bottom-6 left-1/2 dark:text-gray-400">
          &copy; {new Date().getFullYear()} Sketch-to-Cloud
        </p>
      </div>
    </>
  );
}
