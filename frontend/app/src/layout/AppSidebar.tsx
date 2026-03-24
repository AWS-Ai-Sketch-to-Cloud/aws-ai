import { Link, useLocation } from "react-router";
import { GridIcon } from "../icons";
import { useSidebar } from "../context/SidebarContext";

const AppSidebar: React.FC = () => {
  const { isExpanded, isMobileOpen, isHovered, setIsHovered } = useSidebar();
  const location = useLocation();

  const isActive = location.pathname === "/dashboard";

  return (
    <aside
      className={`fixed top-0 left-0 z-50 mt-16 flex h-screen flex-col border-r border-gray-200 bg-white px-5 text-gray-900 transition-all duration-300 ease-in-out dark:border-gray-800 dark:bg-gray-900 lg:mt-0
      ${isExpanded || isMobileOpen ? "w-[290px]" : isHovered ? "w-[290px]" : "w-[90px]"}
      ${isMobileOpen ? "translate-x-0" : "-translate-x-full"} lg:translate-x-0`}
      onMouseEnter={() => !isExpanded && setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      <div className={`flex py-8 ${!isExpanded && !isHovered ? "lg:justify-center" : "justify-start"}`}>
        <Link to="/dashboard" className="block">
          {isExpanded || isHovered || isMobileOpen ? (
            <div>
              <p className="text-lg font-semibold text-gray-900 dark:text-white">Sketch-to-Cloud</p>
              <p className="text-xs text-gray-500 dark:text-gray-400">프로젝트 콘솔</p>
            </div>
          ) : (
            <div className="rounded-lg bg-[#FF9900] p-2 text-white">
              <GridIcon />
            </div>
          )}
        </Link>
      </div>

      <nav className="mb-6">
        <h2
          className={`mb-4 flex text-xs leading-[20px] text-gray-400 ${!isExpanded && !isHovered ? "lg:justify-center" : "justify-start"}`}
        >
          {isExpanded || isHovered || isMobileOpen ? "메뉴" : "..."}
        </h2>

        <ul className="flex flex-col gap-2">
          <li>
            <Link to="/dashboard" className={`menu-item group ${isActive ? "menu-item-active" : "menu-item-inactive"}`}>
              <span className={`menu-item-icon-size ${isActive ? "menu-item-icon-active" : "menu-item-icon-inactive"}`}>
                <GridIcon />
              </span>
              {(isExpanded || isHovered || isMobileOpen) && <span className="menu-item-text">클라우드 콘솔</span>}
            </Link>
          </li>
        </ul>
      </nav>
    </aside>
  );
};

export default AppSidebar;
