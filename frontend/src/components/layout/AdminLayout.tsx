import { Outlet, Link, useLocation, useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import {
  LayoutDashboard,
  Users,
  Building2,
  ClipboardCheck,
  BarChart3,
  Server,
  ScrollText,
  Settings,
  ChevronLeft,
  ChevronRight,
  Shield,
  ArrowLeft,
} from "lucide-react";
import clsx from "clsx";
import { useState } from "react";

const adminNav = [
  { icon: LayoutDashboard, label: "Dashboard", path: "/admin" },
  { icon: Building2, label: "Tenants", path: "/admin/tenants" },
  { icon: Users, label: "Users", path: "/admin/users" },
  { icon: ClipboardCheck, label: "DLC Review", path: "/admin/dlc-queue" },
  { icon: Shield, label: "DLC Analytics", path: "/admin/dlc-analytics" },
  { icon: BarChart3, label: "Revenue", path: "/admin/revenue" },
  { icon: Server, label: "System", path: "/admin/system" },
  { icon: ScrollText, label: "Audit Log", path: "/admin/audit-log" },
  { icon: Settings, label: "Settings", path: "/admin/settings" },
];

export default function AdminLayout() {
  const [collapsed, setCollapsed] = useState(false);
  const location = useLocation();
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-navy-950">
      <motion.aside
        animate={{ width: collapsed ? 72 : 256 }}
        transition={{ duration: 0.3, ease: "easeInOut" }}
        className="fixed left-0 top-0 h-screen bg-navy-900/80 backdrop-blur-xl border-r border-white/5 z-40 flex flex-col"
      >
        {/* Logo */}
        <div className="h-16 flex items-center px-4 gap-3 border-b border-white/5">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-rose-500 to-orange-600 flex items-center justify-center flex-shrink-0">
            <Shield className="w-6 h-6 text-white" />
          </div>
          <AnimatePresence>
            {!collapsed && (
              <motion.span
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -10 }}
                className="text-lg font-bold bg-gradient-to-r from-rose-400 to-orange-400 bg-clip-text text-transparent whitespace-nowrap"
              >
                Admin Panel
              </motion.span>
            )}
          </AnimatePresence>
        </div>

        {/* Back to App */}
        <button
          onClick={() => navigate("/")}
          className="flex items-center gap-3 px-4 py-3 text-gray-500 hover:text-white hover:bg-white/5 transition-colors border-b border-white/5"
        >
          <ArrowLeft className="w-5 h-5 flex-shrink-0" />
          <AnimatePresence>
            {!collapsed && (
              <motion.span
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="text-sm font-medium"
              >
                Back to App
              </motion.span>
            )}
          </AnimatePresence>
        </button>

        {/* Nav */}
        <nav className="flex-1 overflow-y-auto py-4 px-2 space-y-1">
          {adminNav.map((item) => {
            const isActive = location.pathname === item.path ||
              (item.path !== "/admin" && location.pathname.startsWith(item.path));
            return (
              <Link
                key={item.path}
                to={item.path}
                className={clsx(
                  "flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all duration-200 group relative",
                  isActive
                    ? "bg-rose-500/10 text-rose-400"
                    : "text-gray-400 hover:text-white hover:bg-white/5"
                )}
              >
                {isActive && (
                  <motion.div
                    layoutId="activeAdminNav"
                    className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-6 bg-rose-500 rounded-r-full"
                  />
                )}
                <item.icon className={clsx("w-5 h-5 flex-shrink-0", isActive && "text-rose-400")} />
                <AnimatePresence>
                  {!collapsed && (
                    <motion.span
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      exit={{ opacity: 0 }}
                      className="text-sm font-medium whitespace-nowrap"
                    >
                      {item.label}
                    </motion.span>
                  )}
                </AnimatePresence>
              </Link>
            );
          })}
        </nav>

        {/* Collapse toggle */}
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="h-12 flex items-center justify-center border-t border-white/5 text-gray-500 hover:text-white transition-colors"
        >
          {collapsed ? <ChevronRight className="w-5 h-5" /> : <ChevronLeft className="w-5 h-5" />}
        </button>
      </motion.aside>

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
