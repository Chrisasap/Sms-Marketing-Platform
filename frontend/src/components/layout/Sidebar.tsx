import { motion, AnimatePresence } from "framer-motion";
import { Link, useLocation } from "react-router-dom";
import { useSidebarStore } from "../../stores/sidebar";
import {
  LayoutDashboard,
  Send,
  MessageSquare,
  Users,
  List,
  Phone,
  Shield,
  Bot,
  FileText,
  Zap,
  BarChart3,
  Settings,
  CreditCard,
  ChevronLeft,
  ChevronRight,
  Waves,
  ClipboardList,
} from "lucide-react";
import clsx from "clsx";

const navItems = [
  { icon: LayoutDashboard, label: "Dashboard", path: "/" },
  { icon: Send, label: "Campaigns", path: "/campaigns" },
  { icon: MessageSquare, label: "Inbox", path: "/inbox" },
  { icon: Users, label: "Contacts", path: "/contacts" },
  { icon: List, label: "Lists", path: "/lists" },
  { icon: Phone, label: "Numbers", path: "/numbers" },
  { icon: Shield, label: "Compliance", path: "/compliance" },
  { icon: Bot, label: "AI Agents", path: "/ai-agents" },
  { icon: FileText, label: "Templates", path: "/templates" },
  { icon: Zap, label: "Automations", path: "/automations" },
  { icon: BarChart3, label: "Analytics", path: "/analytics" },
  { icon: CreditCard, label: "Billing", path: "/settings/billing" },
  { icon: Settings, label: "Settings", path: "/settings" },
  { icon: ClipboardList, label: "DLC Queue", path: "/admin/dlc-queue" },
];

export default function Sidebar() {
  const { collapsed, toggle } = useSidebarStore();
  const location = useLocation();

  return (
    <motion.aside
      animate={{ width: collapsed ? 72 : 256 }}
      transition={{ duration: 0.3, ease: "easeInOut" }}
      className="fixed left-0 top-0 h-screen bg-navy-900/80 backdrop-blur-xl border-r border-white/5 z-40 flex flex-col"
    >
      {/* Logo */}
      <div className="h-16 flex items-center px-4 gap-3 border-b border-white/5">
        <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center flex-shrink-0">
          <Waves className="w-6 h-6 text-white" />
        </div>
        <AnimatePresence>
          {!collapsed && (
            <motion.span
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -10 }}
              className="text-lg font-bold bg-gradient-to-r from-blue-400 to-indigo-400 bg-clip-text text-transparent whitespace-nowrap"
            >
              BlastWave
            </motion.span>
          )}
        </AnimatePresence>
      </div>

      {/* Nav */}
      <nav className="flex-1 overflow-y-auto py-4 px-2 space-y-1">
        {navItems.map((item) => {
          const isActive = location.pathname === item.path;
          return (
            <Link
              key={item.path}
              to={item.path}
              className={clsx(
                "flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all duration-200 group relative",
                isActive
                  ? "bg-blue-500/10 text-blue-400"
                  : "text-gray-400 hover:text-white hover:bg-white/5"
              )}
            >
              {isActive && (
                <motion.div
                  layoutId="activeNav"
                  className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-6 bg-blue-500 rounded-r-full"
                />
              )}
              <item.icon className={clsx("w-5 h-5 flex-shrink-0", isActive && "text-blue-400")} />
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
        onClick={toggle}
        className="h-12 flex items-center justify-center border-t border-white/5 text-gray-500 hover:text-white transition-colors"
      >
        {collapsed ? <ChevronRight className="w-5 h-5" /> : <ChevronLeft className="w-5 h-5" />}
      </button>
    </motion.aside>
  );
}
