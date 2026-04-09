import { useEffect, useMemo, useState } from "react";
import { NavLink, useLocation, useNavigate } from "react-router";
import { ThemeToggleButton } from "../components/common/ThemeToggleButton";
import {
  clearAuthSession,
  getStoredAuthSession,
  type StoredAuthSession,
} from "../lib/auth-session";

const AppHeader: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const [session, setSession] = useState<StoredAuthSession | null>(null);

  useEffect(() => {
    setSession(getStoredAuthSession());
  }, [location.pathname]);

  const initials = useMemo(() => {
    const displayName = session?.user.displayName?.trim();
    if (!displayName) {
      return "ST";
    }
    return displayName.slice(0, 2).toUpperCase();
  }, [session?.user.displayName]);

  const authProviderLabel = useMemo(() => {
    switch (session?.authProvider ?? "password") {
      case "github":
        return "GitHub";
      case "google":
        return "Google";
      case "kakao":
        return "Kakao";
      case "naver":
        return "Naver";
      default:
        return "ID";
    }
  }, [session?.authProvider]);

  const navItems = [
    { to: "/workspace", label: "워크스페이스" },
    { to: "/projects", label: "프로젝트" },
    { to: "/deploy", label: "배포" },
    { to: "/settings", label: "설정" },
  ];

  const handleLogout = () => {
    clearAuthSession();
    navigate("/", { replace: true });
  };

  return (
    <header className="sticky top-0 z-50 border-b border-slate-200 bg-white/95 backdrop-blur dark:border-slate-800 dark:bg-slate-950/95">
      <div className="mx-auto flex w-full max-w-7xl flex-col">
        <div className="flex items-center justify-between gap-4 px-4 py-4 md:px-6">
          <div className="flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-[#FF9900] text-base font-bold text-white shadow-sm">
              SC
            </div>
            <div>
              <p className="text-base font-semibold text-slate-950 dark:text-white">
                Sketch-to-Cloud
              </p>
              <p className="text-sm text-slate-500 dark:text-slate-400">
                AI 아키텍처 콘솔
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <ThemeToggleButton />
            <div className="hidden items-center gap-3 rounded-2xl border border-slate-200 bg-slate-50 px-3 py-2 md:flex dark:border-slate-800 dark:bg-slate-900">
              <div className="flex h-10 w-10 items-center justify-center rounded-full bg-slate-900 text-xs font-semibold text-white dark:bg-slate-200 dark:text-slate-900">
                {initials}
              </div>
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <p className="truncate text-sm font-medium text-slate-900 dark:text-white">
                    {session?.user.displayName ?? "게스트"}
                  </p>
                  <span className="shrink-0 rounded-full bg-slate-200 px-2 py-0.5 text-[10px] font-semibold text-slate-700 dark:bg-slate-800 dark:text-slate-100">
                    {authProviderLabel}
                  </span>
                </div>
                <p className="mt-1 truncate text-xs text-slate-500 dark:text-slate-400">
                  {session?.user.email ?? "로그인 정보 없음"}
                </p>
              </div>
            </div>
            {session ? (
              <button
                type="button"
                onClick={handleLogout}
                className="rounded-xl border border-slate-300 px-3 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-100 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-900"
              >
                로그아웃
              </button>
            ) : null}
          </div>
        </div>

        <nav className="overflow-x-auto border-t border-slate-200 px-4 dark:border-slate-800 md:px-6">
          <div className="flex min-w-max items-center gap-2 py-3">
            {navItems.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  `rounded-full px-4 py-2 text-sm font-medium transition ${
                    isActive
                      ? "bg-slate-900 text-white dark:bg-slate-100 dark:text-slate-950"
                      : "text-slate-600 hover:bg-slate-100 hover:text-slate-900 dark:text-slate-300 dark:hover:bg-slate-900 dark:hover:text-white"
                  }`
                }
              >
                {item.label}
              </NavLink>
            ))}
          </div>
        </nav>
      </div>
    </header>
  );
};

export default AppHeader;
