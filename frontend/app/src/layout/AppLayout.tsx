import { Outlet } from "react-router";
import AppHeader from "./AppHeader";

const AppLayout: React.FC = () => {
  return (
    <div className="min-h-screen bg-slate-50 text-slate-950 dark:bg-slate-950 dark:text-slate-50">
      <AppHeader />
      <div className="mx-auto w-full max-w-7xl px-4 py-6 md:px-6">
        <Outlet />
      </div>
    </div>
  );
};

export default AppLayout;
