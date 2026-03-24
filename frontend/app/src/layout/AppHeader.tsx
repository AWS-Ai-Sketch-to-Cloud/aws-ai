import { ThemeToggleButton } from "../components/common/ThemeToggleButton";
import { useSidebar } from "../context/SidebarContext";

const AppHeader: React.FC = () => {
  const { isMobileOpen, toggleSidebar, toggleMobileSidebar } = useSidebar();

  const handleToggle = () => {
    if (window.innerWidth >= 1024) {
      toggleSidebar();
    } else {
      toggleMobileSidebar();
    }
  };

  return (
    <header className="sticky top-0 z-99999 flex w-full border-b border-gray-200 bg-white dark:border-gray-800 dark:bg-gray-900">
      <div className="flex w-full items-center justify-between px-3 py-3 sm:px-4 lg:px-6">
        <div className="flex items-center gap-3">
          <button
            className="z-99999 flex h-10 w-10 items-center justify-center rounded-lg border border-gray-200 text-gray-500 dark:border-gray-800 dark:text-gray-400"
            onClick={handleToggle}
            aria-label="사이드바 토글"
          >
            {isMobileOpen ? (
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
                <path
                  fillRule="evenodd"
                  clipRule="evenodd"
                  d="M6.22 7.28a.75.75 0 0 1 1.06-1.06L12 10.94l4.72-4.72a.75.75 0 1 1 1.06 1.06L13.06 12l4.72 4.72a.75.75 0 1 1-1.06 1.06L12 13.06l-4.72 4.72a.75.75 0 0 1-1.06-1.06L10.94 12 6.22 7.28Z"
                  fill="currentColor"
                />
              </svg>
            ) : (
              <svg width="16" height="12" viewBox="0 0 16 12" fill="none">
                <path
                  fillRule="evenodd"
                  clipRule="evenodd"
                  d="M.58 1A.75.75 0 0 1 1.33.25h13.34a.75.75 0 0 1 0 1.5H1.33A.75.75 0 0 1 .58 1Zm0 10a.75.75 0 0 1 .75-.75h13.34a.75.75 0 0 1 0 1.5H1.33a.75.75 0 0 1-.75-.75Zm0-5a.75.75 0 0 1 .75-.75H8a.75.75 0 0 1 0 1.5H1.33A.75.75 0 0 1 .58 6Z"
                  fill="currentColor"
                />
              </svg>
            )}
          </button>

          <div>
            <p className="text-sm font-semibold text-gray-900 dark:text-white">Sketch-to-Cloud</p>
            <p className="text-xs text-gray-500 dark:text-gray-400">AI 인프라 설계 콘솔</p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <span className="rounded-md bg-[#FFF3DF] px-2 py-1 text-xs font-medium text-[#FF9900]">
            API v2
          </span>
          <ThemeToggleButton />
        </div>
      </div>
    </header>
  );
};

export default AppHeader;
