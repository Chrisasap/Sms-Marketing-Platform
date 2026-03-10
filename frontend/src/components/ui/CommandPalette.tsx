import { useState, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useNavigate } from "react-router-dom";
import { Search, LayoutDashboard, Send, MessageSquare, Users, Phone, Settings, BarChart3, Bot, Zap } from "lucide-react";
import clsx from "clsx";

const commands = [
  { icon: LayoutDashboard, label: "Dashboard", path: "/" },
  { icon: Send, label: "Campaigns", path: "/campaigns" },
  { icon: Send, label: "New Campaign", path: "/campaigns/new" },
  { icon: MessageSquare, label: "Inbox", path: "/inbox" },
  { icon: Users, label: "Contacts", path: "/contacts" },
  { icon: Users, label: "Import Contacts", path: "/contacts/import" },
  { icon: Phone, label: "Phone Numbers", path: "/numbers" },
  { icon: Phone, label: "Buy Numbers", path: "/numbers/search" },
  { icon: Bot, label: "AI Agents", path: "/ai-agents" },
  { icon: Zap, label: "Automations", path: "/automations" },
  { icon: BarChart3, label: "Analytics", path: "/analytics" },
  { icon: Settings, label: "Settings", path: "/settings" },
];

export default function CommandPalette() {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [activeIndex, setActiveIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const navigate = useNavigate();

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setOpen((o) => !o);
      }
      if (e.key === "Escape") setOpen(false);
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, []);

  useEffect(() => {
    if (open) {
      setQuery("");
      setActiveIndex(0);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [open]);

  const filtered = commands.filter((c) => c.label.toLowerCase().includes(query.toLowerCase()));

  const handleSelect = (path: string) => {
    navigate(path);
    setOpen(false);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActiveIndex((i) => Math.min(i + 1, filtered.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActiveIndex((i) => Math.max(i - 1, 0));
    } else if (e.key === "Enter" && filtered[activeIndex]) {
      handleSelect(filtered[activeIndex].path);
    }
  };

  return (
    <AnimatePresence>
      {open && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => setOpen(false)}
            className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50"
          />
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: -20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: -20 }}
            className="fixed top-[20%] left-1/2 -translate-x-1/2 w-full max-w-lg z-50"
          >
            <div className="bg-navy-900/95 backdrop-blur-xl border border-white/10 rounded-2xl shadow-2xl overflow-hidden">
              <div className="flex items-center px-4 border-b border-white/5">
                <Search className="w-5 h-5 text-gray-500" />
                <input
                  ref={inputRef}
                  type="text"
                  value={query}
                  onChange={(e) => { setQuery(e.target.value); setActiveIndex(0); }}
                  onKeyDown={handleKeyDown}
                  placeholder="Type a command or search..."
                  className="flex-1 px-3 py-4 bg-transparent text-white placeholder-gray-500 focus:outline-none"
                />
                <kbd className="text-xs text-gray-500 bg-white/5 px-2 py-1 rounded">ESC</kbd>
              </div>
              <div className="max-h-80 overflow-y-auto p-2">
                {filtered.map((cmd, i) => (
                  <button
                    key={cmd.path}
                    onClick={() => handleSelect(cmd.path)}
                    onMouseEnter={() => setActiveIndex(i)}
                    className={clsx(
                      "w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors",
                      i === activeIndex ? "bg-blue-500/20 text-blue-400" : "text-gray-400 hover:text-white"
                    )}
                  >
                    <cmd.icon className="w-4 h-4" />
                    {cmd.label}
                  </button>
                ))}
                {filtered.length === 0 && (
                  <p className="text-center text-gray-500 py-8">No results found</p>
                )}
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
