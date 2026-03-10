import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { useNavigate } from "react-router-dom";
import {
  Plus,
  Megaphone,
  Clock,
  Send,
  CheckCircle2,
  XCircle,
  FileEdit,
  Filter,
} from "lucide-react";
import clsx from "clsx";
import { format } from "date-fns";
import GlassCard from "../components/ui/GlassCard";
import DataTable from "../components/ui/DataTable";
import api from "../lib/api";

interface Campaign {
  id: string;
  name: string;
  type: "blast" | "drip" | "triggered" | "ab";
  status: "draft" | "scheduled" | "sending" | "completed" | "failed";
  recipients: number;
  delivered: number;
  sent_at: string | null;
  created_at: string;
}

const statusTabs = [
  { key: "all", label: "All", icon: Filter },
  { key: "draft", label: "Draft", icon: FileEdit },
  { key: "scheduled", label: "Scheduled", icon: Clock },
  { key: "sending", label: "Sending", icon: Send },
  { key: "completed", label: "Completed", icon: CheckCircle2 },
  { key: "failed", label: "Failed", icon: XCircle },
] as const;

const statusBadge: Record<Campaign["status"], { bg: string; text: string; dot?: string }> = {
  draft: { bg: "bg-gray-500/20", text: "text-gray-400" },
  scheduled: { bg: "bg-amber-500/20", text: "text-amber-400" },
  sending: { bg: "bg-blue-500/20", text: "text-blue-400", dot: "animate-pulse" },
  completed: { bg: "bg-emerald-500/20", text: "text-emerald-400" },
  failed: { bg: "bg-rose-500/20", text: "text-rose-400" },
};

const typeBadge: Record<Campaign["type"], string> = {
  blast: "Blast",
  drip: "Drip",
  triggered: "Triggered",
  ab: "A/B Test",
};

const container = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { staggerChildren: 0.08 } },
};

const item = {
  hidden: { opacity: 0, y: 20 },
  show: { opacity: 1, y: 0 },
};

export default function Campaigns() {
  const [activeTab, setActiveTab] = useState<string>("all");
  const navigate = useNavigate();

  const { data: campaigns = [], isLoading, error } = useQuery<Campaign[]>({
    queryKey: ["campaigns"],
    queryFn: async () => {
      const res = await api.get("/campaigns/");
      return res.data.campaigns ?? res.data;
    },
  });

  if (error) return <div className="p-8 text-center text-red-400">Failed to load data. Please try again.</div>;

  const filtered =
    activeTab === "all"
      ? campaigns
      : campaigns.filter((c) => c.status === activeTab);

  const columns = [
    {
      key: "name",
      label: "Campaign",
      sortable: true,
      render: (row: Campaign) => (
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-blue-500/30 to-indigo-600/30 flex items-center justify-center">
            <Megaphone className="w-4 h-4 text-blue-400" />
          </div>
          <div>
            <p className="text-white font-medium">{row.name}</p>
            <p className="text-xs text-gray-500">{typeBadge[row.type]}</p>
          </div>
        </div>
      ),
    },
    {
      key: "status",
      label: "Status",
      sortable: true,
      render: (row: Campaign) => {
        const badge = statusBadge[row.status];
        return (
          <span
            className={clsx(
              "inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium",
              badge.bg,
              badge.text
            )}
          >
            {badge.dot && (
              <span className={clsx("w-1.5 h-1.5 rounded-full bg-current", badge.dot)} />
            )}
            {row.status.charAt(0).toUpperCase() + row.status.slice(1)}
          </span>
        );
      },
    },
    {
      key: "recipients",
      label: "Recipients",
      sortable: true,
      render: (row: Campaign) => (
        <span className="font-mono text-gray-300">{row.recipients.toLocaleString()}</span>
      ),
    },
    {
      key: "delivered",
      label: "Delivered",
      sortable: true,
      render: (row: Campaign) => {
        const pct = row.recipients > 0 ? ((row.delivered / row.recipients) * 100).toFixed(1) : "0.0";
        const color =
          Number(pct) >= 90
            ? "text-emerald-400"
            : Number(pct) >= 70
            ? "text-amber-400"
            : "text-rose-400";
        return (
          <div className="flex items-center gap-2">
            <div className="w-16 h-1.5 bg-white/10 rounded-full overflow-hidden">
              <motion.div
                initial={{ width: 0 }}
                animate={{ width: `${pct}%` }}
                transition={{ duration: 1, ease: "easeOut" }}
                className={clsx(
                  "h-full rounded-full",
                  Number(pct) >= 90
                    ? "bg-emerald-500"
                    : Number(pct) >= 70
                    ? "bg-amber-500"
                    : "bg-rose-500"
                )}
              />
            </div>
            <span className={clsx("font-mono text-sm", color)}>{pct}%</span>
          </div>
        );
      },
    },
    {
      key: "sent_at",
      label: "Sent Date",
      sortable: true,
      render: (row: Campaign) =>
        row.sent_at ? (
          <span className="text-gray-400 text-sm">
            {format(new Date(row.sent_at), "MMM d, yyyy h:mm a")}
          </span>
        ) : (
          <span className="text-gray-600 text-sm italic">Not sent</span>
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
          <h1 className="text-3xl font-bold text-white">Campaigns</h1>
          <p className="text-gray-400 mt-1">
            Manage and monitor your SMS campaigns.
          </p>
        </div>
        <motion.button
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          onClick={() => navigate("/campaigns/new")}
          className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl font-semibold text-sm text-white bg-gradient-to-r from-blue-500 to-indigo-600 hover:from-blue-600 hover:to-indigo-700 shadow-lg shadow-blue-500/25 transition-all"
        >
          <Plus className="w-4 h-4" />
          New Campaign
        </motion.button>
      </motion.div>

      {/* Status Tabs */}
      <motion.div variants={item} className="mb-6">
        <div className="flex gap-1 bg-white/5 rounded-xl p-1 border border-white/10 overflow-x-auto">
          {statusTabs.map((tab) => {
            const isActive = activeTab === tab.key;
            const Icon = tab.icon;
            return (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key)}
                className={clsx(
                  "relative flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors whitespace-nowrap",
                  isActive ? "text-white" : "text-gray-400 hover:text-gray-200"
                )}
              >
                {isActive && (
                  <motion.div
                    layoutId="campaign-tab"
                    className="absolute inset-0 bg-white/10 rounded-lg"
                    transition={{ type: "spring", stiffness: 400, damping: 30 }}
                  />
                )}
                <span className="relative flex items-center gap-2">
                  <Icon className="w-4 h-4" />
                  {tab.label}
                </span>
              </button>
            );
          })}
        </div>
      </motion.div>

      {/* Data Table */}
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
          ) : filtered.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-20 text-gray-500">
              <Megaphone className="w-12 h-12 mb-4 opacity-30" />
              <p className="text-lg font-medium">No campaigns found</p>
              <p className="text-sm mt-1">
                {activeTab === "all"
                  ? "Create your first campaign to get started."
                  : `No ${activeTab} campaigns.`}
              </p>
            </div>
          ) : (
            <DataTable
              data={filtered}
              columns={columns}
              searchable
              pageSize={15}
            />
          )}
        </GlassCard>
      </motion.div>
    </motion.div>
  );
}
