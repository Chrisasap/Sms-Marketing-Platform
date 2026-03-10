import { Outlet } from "react-router-dom";
import Sidebar from "./Sidebar";
import { useSidebarStore } from "../../stores/sidebar";

export default function Layout() {
  const collapsed = useSidebarStore((s) => s.collapsed);

  return (
    <div className="min-h-screen bg-navy-950">
      <Sidebar />
      <main
        className="min-h-screen transition-[margin-left] duration-300 ease-in-out"
        style={{ marginLeft: collapsed ? 72 : 256 }}
      >
        <div className="p-8">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
