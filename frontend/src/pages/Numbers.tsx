import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { motion, AnimatePresence } from "framer-motion";
import {
  Phone,
  PhoneCall,
  PhoneForwarded,
  DollarSign,
  Plus,
  Search,
  X,
  MessageSquare,
  Loader,
  Hash,
  Globe,
  ShoppingCart,
} from "lucide-react";
import clsx from "clsx";
import StatCard from "../components/ui/StatCard";
import GlassCard from "../components/ui/GlassCard";
import DataTable from "../components/ui/DataTable";
import api from "../lib/api";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface PhoneNumber {
  id: string;
  number: string;
  friendly_name: string;
  type: "local" | "toll-free" | "short-code";
  status: "active" | "pending" | "inactive";
  campaign: string | null;
  capabilities: ("sms" | "mms" | "voice")[];
  monthly_cost: number;
}

interface AvailableNumber {
  number: string;
  type: "local" | "toll-free";
  region: string;
  monthly_cost: number;
  capabilities: ("sms" | "mms" | "voice")[];
}

/* ------------------------------------------------------------------ */
/*  Constants                                                          */
/* ------------------------------------------------------------------ */

const typeBadge: Record<PhoneNumber["type"], { bg: string; text: string }> = {
  local: { bg: "bg-blue-500/20", text: "text-blue-400" },
  "toll-free": { bg: "bg-emerald-500/20", text: "text-emerald-400" },
  "short-code": { bg: "bg-amber-500/20", text: "text-amber-400" },
};

const statusBadge: Record<PhoneNumber["status"], { bg: string; text: string; dot?: boolean }> = {
  active: { bg: "bg-emerald-500/20", text: "text-emerald-400" },
  pending: { bg: "bg-amber-500/20", text: "text-amber-400", dot: true },
  inactive: { bg: "bg-gray-500/20", text: "text-gray-400" },
};

const capabilityIcons: Record<string, typeof MessageSquare> = {
  sms: MessageSquare,
  mms: Globe,
  voice: PhoneCall,
};

const container = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { staggerChildren: 0.08 } },
};

const item = {
  hidden: { opacity: 0, y: 20 },
  show: { opacity: 1, y: 0 },
};

/* ------------------------------------------------------------------ */
/*  Format phone number                                                */
/* ------------------------------------------------------------------ */

function formatPhoneNumber(num: string): string {
  const cleaned = num.replace(/\D/g, "");
  if (cleaned.length === 11 && cleaned.startsWith("1")) {
    return `+1 (${cleaned.slice(1, 4)}) ${cleaned.slice(4, 7)}-${cleaned.slice(7)}`;
  }
  if (cleaned.length === 10) {
    return `(${cleaned.slice(0, 3)}) ${cleaned.slice(3, 6)}-${cleaned.slice(6)}`;
  }
  return num;
}

/* ------------------------------------------------------------------ */
/*  Buy Numbers Modal                                                  */
/* ------------------------------------------------------------------ */

function BuyNumbersModal({ onClose }: { onClose: () => void }) {
  const [areaCode, setAreaCode] = useState("");
  const [searchType, setSearchType] = useState<"local" | "toll-free">("local");
  const queryClient = useQueryClient();

  const { data: available = [], isLoading: searching, refetch } = useQuery<AvailableNumber[]>({
    queryKey: ["available-numbers", areaCode, searchType],
    queryFn: async () => {
      const res = await api.post("/numbers/search", {
        area_code: areaCode,
        type: searchType,
      });
      return res.data.available_numbers ?? res.data;
    },
    enabled: false,
  });

  const purchaseMutation = useMutation({
    mutationFn: async (number: string) => {
      const res = await api.post("/numbers/order", { numbers: [number] });
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["phone-numbers"] });
    },
  });

  const handleSearch = () => {
    if (searchType === "local" && !areaCode) return;
    refetch();
  };

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
    >
      {/* Backdrop */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        onClick={onClose}
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
      />

      {/* Modal */}
      <motion.div
        initial={{ scale: 0.9, opacity: 0, y: 30 }}
        animate={{ scale: 1, opacity: 1, y: 0 }}
        exit={{ scale: 0.9, opacity: 0, y: 30 }}
        transition={{ type: "spring", stiffness: 300, damping: 25 }}
        className="relative w-full max-w-2xl bg-gray-900 border border-white/10 rounded-2xl shadow-2xl overflow-hidden"
      >
        {/* Header */}
        <div className="px-6 py-5 border-b border-white/10 flex items-center justify-between">
          <div>
            <h2 className="text-xl font-bold text-white">Buy Phone Numbers</h2>
            <p className="text-sm text-gray-400 mt-0.5">Search for available numbers to add to your account.</p>
          </div>
          <button onClick={onClose} className="p-2 rounded-lg hover:bg-white/10 transition-colors">
            <X className="w-5 h-5 text-gray-400" />
          </button>
        </div>

        {/* Search */}
        <div className="px-6 py-4 border-b border-white/5">
          <div className="flex gap-3">
            {/* Type toggle */}
            <div className="flex bg-white/5 rounded-xl p-0.5 border border-white/10">
              {(["local", "toll-free"] as const).map((t) => (
                <button
                  key={t}
                  onClick={() => setSearchType(t)}
                  className={clsx(
                    "px-4 py-2 rounded-lg text-sm font-medium transition-colors",
                    searchType === t ? "bg-white/10 text-white" : "text-gray-500 hover:text-gray-300"
                  )}
                >
                  {t === "local" ? "Local" : "Toll-Free"}
                </button>
              ))}
            </div>

            {searchType === "local" && (
              <div className="relative flex-1">
                <Hash className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
                <input
                  type="text"
                  value={areaCode}
                  onChange={(e) => setAreaCode(e.target.value.replace(/\D/g, "").slice(0, 3))}
                  placeholder="Area code (e.g. 212)"
                  maxLength={3}
                  className="w-full pl-10 pr-4 py-2.5 bg-white/5 border border-white/10 rounded-xl text-sm text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50 font-mono"
                />
              </div>
            )}

            <motion.button
              whileHover={{ scale: 1.03 }}
              whileTap={{ scale: 0.97 }}
              onClick={handleSearch}
              disabled={searchType === "local" && areaCode.length < 3}
              className={clsx(
                "px-5 py-2.5 rounded-xl text-sm font-semibold text-white flex items-center gap-2 transition-all",
                (searchType === "toll-free" || areaCode.length >= 3)
                  ? "bg-gradient-to-r from-blue-500 to-indigo-600 shadow-lg shadow-blue-500/25"
                  : "bg-gray-700 opacity-50 cursor-not-allowed"
              )}
            >
              <Search className="w-4 h-4" />
              Search
            </motion.button>
          </div>
        </div>

        {/* Results */}
        <div className="px-6 py-4 max-h-[400px] overflow-y-auto">
          {searching ? (
            <div className="flex items-center justify-center py-12">
              <motion.div
                animate={{ rotate: 360 }}
                transition={{ repeat: Infinity, duration: 1, ease: "linear" }}
                className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full"
              />
            </div>
          ) : available.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-gray-600">
              <Phone className="w-10 h-10 mb-3 opacity-30" />
              <p className="text-sm">Search for available numbers above.</p>
            </div>
          ) : (
            <div className="space-y-2">
              {available.map((num) => (
                <motion.div
                  key={num.number}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="flex items-center justify-between p-4 bg-white/5 rounded-xl border border-white/10 hover:border-white/20 transition-all"
                >
                  <div className="flex items-center gap-4">
                    <div className="w-10 h-10 rounded-xl bg-blue-500/20 flex items-center justify-center">
                      <Phone className="w-5 h-5 text-blue-400" />
                    </div>
                    <div>
                      <p className="text-white font-mono font-semibold">{formatPhoneNumber(num.number)}</p>
                      <div className="flex items-center gap-2 mt-0.5">
                        <span className="text-xs text-gray-500">{num.region}</span>
                        <span className="text-xs text-gray-600">|</span>
                        <div className="flex gap-1">
                          {num.capabilities.map((cap) => {
                            const Icon = capabilityIcons[cap] || MessageSquare;
                            return (
                              <span key={cap} className="text-[10px] text-gray-500 flex items-center gap-0.5">
                                <Icon className="w-3 h-3" /> {cap.toUpperCase()}
                              </span>
                            );
                          })}
                        </div>
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-4">
                    <span className="text-sm font-mono text-emerald-400">${num.monthly_cost.toFixed(2)}/mo</span>
                    <motion.button
                      whileHover={{ scale: 1.05 }}
                      whileTap={{ scale: 0.95 }}
                      onClick={() => purchaseMutation.mutate(num.number)}
                      disabled={purchaseMutation.isPending}
                      className="px-4 py-2 rounded-lg text-xs font-semibold text-white bg-gradient-to-r from-emerald-500 to-teal-600 hover:from-emerald-600 hover:to-teal-700 shadow-lg shadow-emerald-500/20 transition-all"
                    >
                      {purchaseMutation.isPending ? (
                        <Loader className="w-4 h-4 animate-spin" />
                      ) : (
                        <span className="flex items-center gap-1">
                          <ShoppingCart className="w-3 h-3" /> Buy
                        </span>
                      )}
                    </motion.button>
                  </div>
                </motion.div>
              ))}
            </div>
          )}
        </div>
      </motion.div>
    </motion.div>
  );
}

/* ------------------------------------------------------------------ */
/*  Main Component                                                     */
/* ------------------------------------------------------------------ */

export default function Numbers() {
  const [showBuyModal, setShowBuyModal] = useState(false);

  const { data: numbers = [], isLoading, error } = useQuery<PhoneNumber[]>({
    queryKey: ["phone-numbers"],
    queryFn: async () => {
      const res = await api.get("/numbers/");
      return res.data.numbers ?? res.data;
    },
  });

  if (error) return <div className="p-8 text-center text-red-400">Failed to load data. Please try again.</div>;

  const stats = {
    total: numbers.length,
    local: numbers.filter((n) => n.type === "local").length,
    tollFree: numbers.filter((n) => n.type === "toll-free").length,
    monthlyCost: numbers.reduce((sum, n) => sum + n.monthly_cost, 0),
  };

  const columns = [
    {
      key: "number",
      label: "Number",
      sortable: true,
      render: (row: PhoneNumber) => (
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-blue-500/30 to-indigo-600/30 flex items-center justify-center">
            <Phone className="w-4 h-4 text-blue-400" />
          </div>
          <div>
            <p className="text-white font-mono font-semibold text-sm">{formatPhoneNumber(row.number)}</p>
            {row.friendly_name && (
              <p className="text-xs text-gray-500">{row.friendly_name}</p>
            )}
          </div>
        </div>
      ),
    },
    {
      key: "type",
      label: "Type",
      sortable: true,
      render: (row: PhoneNumber) => {
        const badge = typeBadge[row.type];
        return (
          <span className={clsx("inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium", badge.bg, badge.text)}>
            {row.type === "toll-free" ? "Toll-Free" : row.type === "short-code" ? "Short Code" : "Local"}
          </span>
        );
      },
    },
    {
      key: "status",
      label: "Status",
      sortable: true,
      render: (row: PhoneNumber) => {
        const badge = statusBadge[row.status];
        return (
          <span className={clsx("inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium", badge.bg, badge.text)}>
            {badge.dot && <span className="w-1.5 h-1.5 rounded-full bg-current animate-pulse" />}
            {row.status.charAt(0).toUpperCase() + row.status.slice(1)}
          </span>
        );
      },
    },
    {
      key: "campaign",
      label: "Campaign",
      sortable: true,
      render: (row: PhoneNumber) =>
        row.campaign ? (
          <span className="text-sm text-gray-300">{row.campaign}</span>
        ) : (
          <span className="text-sm text-gray-600 italic">Unassigned</span>
        ),
    },
    {
      key: "capabilities",
      label: "Capabilities",
      render: (row: PhoneNumber) => (
        <div className="flex gap-2">
          {row.capabilities.map((cap) => {
            const Icon = capabilityIcons[cap] || MessageSquare;
            return (
              <div
                key={cap}
                className="w-7 h-7 rounded-lg bg-white/5 border border-white/10 flex items-center justify-center"
                title={cap.toUpperCase()}
              >
                <Icon className="w-3.5 h-3.5 text-gray-400" />
              </div>
            );
          })}
        </div>
      ),
    },
    {
      key: "monthly_cost",
      label: "Cost",
      sortable: true,
      render: (row: PhoneNumber) => (
        <span className="font-mono text-sm text-emerald-400">${row.monthly_cost.toFixed(2)}/mo</span>
      ),
    },
  ];

  return (
    <motion.div variants={container} initial="hidden" animate="show">
      {/* Header */}
      <motion.div
        variants={item}
        className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-8"
      >
        <div>
          <h1 className="text-3xl font-bold text-white">Phone Numbers</h1>
          <p className="text-gray-400 mt-1">Manage your SMS-enabled phone numbers.</p>
        </div>
        <motion.button
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          onClick={() => setShowBuyModal(true)}
          className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl font-semibold text-sm text-white bg-gradient-to-r from-blue-500 to-indigo-600 hover:from-blue-600 hover:to-indigo-700 shadow-lg shadow-blue-500/25 transition-all"
        >
          <Plus className="w-4 h-4" />
          Buy Numbers
        </motion.button>
      </motion.div>

      {/* Stats */}
      <motion.div variants={container} initial="hidden" animate="show" className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <motion.div variants={item}>
          <StatCard title="Total Numbers" value={stats.total} icon={Phone} color="blue" />
        </motion.div>
        <motion.div variants={item}>
          <StatCard title="Local" value={stats.local} icon={PhoneCall} color="emerald" />
        </motion.div>
        <motion.div variants={item}>
          <StatCard title="Toll-Free" value={stats.tollFree} icon={PhoneForwarded} color="amber" />
        </motion.div>
        <motion.div variants={item}>
          <StatCard title="Monthly Cost" value={stats.monthlyCost} icon={DollarSign} prefix="$" color="rose" />
        </motion.div>
      </motion.div>

      {/* Table */}
      <motion.div variants={item}>
        <GlassCard>
          {isLoading ? (
            <div className="flex items-center justify-center py-20">
              <motion.div
                animate={{ rotate: 360 }}
                transition={{ repeat: Infinity, duration: 1, ease: "linear" }}
                className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full"
              />
            </div>
          ) : numbers.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-20 text-gray-500">
              <Phone className="w-12 h-12 mb-4 opacity-30" />
              <p className="text-lg font-medium">No phone numbers yet</p>
              <p className="text-sm mt-1">Buy your first number to start sending messages.</p>
              <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={() => setShowBuyModal(true)}
                className="mt-4 inline-flex items-center gap-2 px-5 py-2.5 rounded-xl font-semibold text-sm text-white bg-gradient-to-r from-blue-500 to-indigo-600 shadow-lg shadow-blue-500/25"
              >
                <Plus className="w-4 h-4" />
                Buy Numbers
              </motion.button>
            </div>
          ) : (
            <DataTable
              data={numbers}
              columns={columns}
              searchable
              pageSize={15}
            />
          )}
        </GlassCard>
      </motion.div>

      {/* Buy Modal */}
      <AnimatePresence>
        {showBuyModal && <BuyNumbersModal onClose={() => setShowBuyModal(false)} />}
      </AnimatePresence>
    </motion.div>
  );
}
