import { useState } from "react";
import { motion } from "framer-motion";
import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  Shield,
  CheckCircle2,
  Clock,
  XCircle,
  AlertTriangle,
  Plus,
  TrendingUp,
  Info,
  Ban,
  ChevronRight,
  Loader2,
} from "lucide-react";
import clsx from "clsx";
import GlassCard from "../components/ui/GlassCard";
import DataTable from "../components/ui/DataTable";
import api from "../lib/api";

const container = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { staggerChildren: 0.08 } },
};

const item = {
  hidden: { opacity: 0, y: 20 },
  show: { opacity: 1, y: 0 },
};

type BrandStatus = "registered" | "pending" | "none";

interface BrandData {
  id: string;
  legal_name: string;
  entity_type: string;
  ein: string;
  brand_id?: string;
  status: string;
}

interface CampaignData {
  id: string;
  name?: string;
  use_case: string;
  description: string;
  mps_limit?: number;
  daily_limit?: number;
  status: string;
}

interface OptOutEntry {
  id: string;
  phone: string;
  campaign: string;
  keyword: string;
  timestamp: string;
}

interface DashboardStats {
  trust_score?: number;
  trust_score_change?: number;
}

const tips = [
  { icon: Info, text: "Always include opt-out language (e.g., 'Reply STOP to unsubscribe') in every marketing message.", color: "blue" },
  { icon: AlertTriangle, text: "Messages sent outside quiet hours (9PM-8AM local time) may trigger carrier filtering.", color: "amber" },
  { icon: Shield, text: "Keep your trust score above 75 to maintain high throughput limits.", color: "emerald" },
  { icon: Ban, text: "Never send messages to numbers that have opted out. Violations can result in carrier bans.", color: "rose" },
];

const brandStatusMap: Record<string, BrandStatus> = {
  approved: "registered",
  registered: "registered",
  active: "registered",
  pending: "pending",
  pending_review: "pending",
  none: "none",
};

const statusConfig: Record<BrandStatus, { label: string; color: string; icon: typeof CheckCircle2; bg: string }> = {
  registered: { label: "Registered", color: "text-emerald-400", icon: CheckCircle2, bg: "bg-emerald-500/20" },
  pending: { label: "Pending Review", color: "text-amber-400", icon: Clock, bg: "bg-amber-500/20" },
  none: { label: "Not Registered", color: "text-rose-400", icon: XCircle, bg: "bg-rose-500/20" },
};

const campaignStatusBadge: Record<string, { bg: string; text: string }> = {
  approved: { bg: "bg-emerald-500/20", text: "text-emerald-400" },
  active: { bg: "bg-emerald-500/20", text: "text-emerald-400" },
  pending: { bg: "bg-amber-500/20", text: "text-amber-400" },
  pending_review: { bg: "bg-amber-500/20", text: "text-amber-400" },
  rejected: { bg: "bg-rose-500/20", text: "text-rose-400" },
};

function TrustScoreGauge({ score }: { score: number }) {
  const radius = 54;
  const circumference = 2 * Math.PI * radius;
  const progress = (score / 100) * circumference;
  const color = score >= 75 ? "#10b981" : score >= 50 ? "#f59e0b" : "#ef4444";

  return (
    <div className="relative w-36 h-36 mx-auto">
      <svg className="w-full h-full -rotate-90" viewBox="0 0 120 120">
        <circle cx="60" cy="60" r={radius} fill="none" stroke="rgba(255,255,255,0.05)" strokeWidth="10" />
        <motion.circle
          cx="60"
          cy="60"
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth="10"
          strokeLinecap="round"
          strokeDasharray={circumference}
          initial={{ strokeDashoffset: circumference }}
          animate={{ strokeDashoffset: circumference - progress }}
          transition={{ duration: 1.5, ease: "easeOut" }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <motion.span
          className="text-3xl font-bold font-mono text-white"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.5 }}
        >
          {score}
        </motion.span>
        <span className="text-xs text-gray-400">Trust Score</span>
      </div>
    </div>
  );
}

export default function Compliance() {
  const navigate = useNavigate();
  const [expandedTip, setExpandedTip] = useState<number | null>(null);

  // Fetch brands
  const { data: brands = [], isLoading: brandsLoading } = useQuery<BrandData[]>({
    queryKey: ["compliance-brands"],
    queryFn: async () => {
      const res = await api.get("/compliance/brands");
      return res.data;
    },
  });

  // Fetch campaigns
  const { data: campaigns = [], isLoading: campaignsLoading } = useQuery<CampaignData[]>({
    queryKey: ["compliance-campaigns"],
    queryFn: async () => {
      const res = await api.get("/compliance/campaigns");
      return res.data;
    },
  });

  // Fetch opt-outs
  const { data: optOuts = [] } = useQuery<OptOutEntry[]>({
    queryKey: ["compliance-optouts"],
    queryFn: async () => {
      const res = await api.get("/compliance/opt-outs");
      return res.data;
    },
  });

  // Fetch dashboard stats
  const { data: dashboardStats } = useQuery<DashboardStats>({
    queryKey: ["compliance-dashboard"],
    queryFn: async () => {
      const res = await api.get("/compliance/dashboard");
      return res.data;
    },
  });

  const trustScore = dashboardStats?.trust_score ?? 0;
  const trustScoreChange = dashboardStats?.trust_score_change ?? 0;

  // Determine brand status from fetched data
  const primaryBrand = brands.length > 0 ? brands[0] : null;
  const derivedBrandStatus: BrandStatus = primaryBrand
    ? brandStatusMap[primaryBrand.status] || "none"
    : "none";

  const brand = statusConfig[derivedBrandStatus];
  const BrandIcon = brand.icon;

  const optOutColumns = [
    { key: "phone" as const, label: "Phone Number", sortable: true },
    { key: "campaign" as const, label: "Campaign", sortable: true },
    { key: "keyword" as const, label: "Keyword", sortable: true },
    { key: "timestamp" as const, label: "Time", sortable: true },
  ];

  return (
    <motion.div variants={container} initial="hidden" animate="show">
      {/* Header */}
      <motion.div variants={item} className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-8">
        <div>
          <h1 className="text-3xl font-bold text-white">10DLC Compliance</h1>
          <p className="text-gray-400 mt-1">Manage your brand and campaign registrations.</p>
        </div>
        <div className="flex gap-3">
          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={() => navigate("/compliance/brands/new")}
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl font-semibold text-sm text-white bg-gradient-to-r from-blue-500 to-indigo-600 hover:from-blue-600 hover:to-indigo-700 shadow-lg shadow-blue-500/25 transition-all"
          >
            <Plus className="w-4 h-4" />
            Register Brand
          </motion.button>
          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={() => navigate("/compliance/campaigns/new")}
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl font-semibold text-sm text-white bg-white/10 hover:bg-white/15 border border-white/10 transition-all"
          >
            <Plus className="w-4 h-4" />
            Register Campaign
          </motion.button>
        </div>
      </motion.div>

      {/* Brand Registration + Trust Score */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
        <motion.div variants={item} className="lg:col-span-2">
          <GlassCard>
            <div className="flex items-start justify-between mb-6">
              <div>
                <h3 className="text-lg font-semibold text-white mb-1">Brand Registration</h3>
                <p className="text-sm text-gray-400">Your 10DLC brand status with The Campaign Registry (TCR)</p>
              </div>
              <span className={clsx("inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium", brand.bg, brand.color)}>
                <BrandIcon className="w-3.5 h-3.5" />
                {brand.label}
              </span>
            </div>
            {brandsLoading ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="w-6 h-6 text-blue-400 animate-spin" />
              </div>
            ) : primaryBrand ? (
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-white/5 rounded-xl p-4">
                  <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">Legal Name</p>
                  <p className="text-sm text-white font-medium">{primaryBrand.legal_name}</p>
                </div>
                <div className="bg-white/5 rounded-xl p-4">
                  <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">Brand ID</p>
                  <p className="text-sm text-white font-mono">{primaryBrand.brand_id || primaryBrand.id}</p>
                </div>
                <div className="bg-white/5 rounded-xl p-4">
                  <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">Entity Type</p>
                  <p className="text-sm text-white font-medium">{primaryBrand.entity_type}</p>
                </div>
                <div className="bg-white/5 rounded-xl p-4">
                  <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">EIN</p>
                  <p className="text-sm text-white font-mono">{primaryBrand.ein}</p>
                </div>
              </div>
            ) : (
              <div className="text-center py-8">
                <p className="text-gray-500 text-sm">No brand registered yet. Click &quot;Register Brand&quot; to get started.</p>
              </div>
            )}
          </GlassCard>
        </motion.div>

        <motion.div variants={item}>
          <GlassCard className="flex flex-col items-center justify-center h-full">
            <TrustScoreGauge score={trustScore} />
            <div className="flex items-center gap-2 mt-4 text-sm">
              <TrendingUp className="w-4 h-4 text-emerald-400" />
              <span className="text-emerald-400 font-medium">{trustScoreChange >= 0 ? `+${trustScoreChange}` : trustScoreChange} pts</span>
              <span className="text-gray-500">from last month</span>
            </div>
          </GlassCard>
        </motion.div>
      </div>

      {/* Campaign Registrations */}
      <motion.div variants={item} className="mb-8">
        <h3 className="text-lg font-semibold text-white mb-4">Campaign Registrations</h3>
        {campaignsLoading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="w-6 h-6 text-blue-400 animate-spin" />
          </div>
        ) : campaigns.length === 0 ? (
          <GlassCard>
            <div className="text-center py-8">
              <p className="text-gray-500 text-sm">No campaigns registered yet. Click &quot;Register Campaign&quot; to create one.</p>
            </div>
          </GlassCard>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {campaigns.map((camp) => {
              const badge = campaignStatusBadge[camp.status] || campaignStatusBadge.pending;
              return (
                <motion.div key={camp.id} whileHover={{ scale: 1.01 }}>
                  <GlassCard hover className="cursor-pointer">
                    <div className="flex items-start justify-between mb-3">
                      <h4 className="text-white font-semibold">{camp.name || camp.description?.slice(0, 40) || "Campaign"}</h4>
                      <span className={clsx("px-2.5 py-1 rounded-full text-xs font-medium", badge.bg, badge.text)}>
                        {camp.status.replace(/_/g, " ").replace(/\b\w/g, (l) => l.toUpperCase())}
                      </span>
                    </div>
                    <div className="grid grid-cols-3 gap-3">
                      <div>
                        <p className="text-xs text-gray-500 mb-0.5">Use Case</p>
                        <p className="text-sm text-gray-300">{camp.use_case}</p>
                      </div>
                      <div>
                        <p className="text-xs text-gray-500 mb-0.5">MPS Limit</p>
                        <p className="text-sm text-gray-300 font-mono">{camp.mps_limit ?? "-"}</p>
                      </div>
                      <div>
                        <p className="text-xs text-gray-500 mb-0.5">Daily Limit</p>
                        <p className="text-sm text-gray-300 font-mono">{camp.daily_limit?.toLocaleString() ?? "-"}</p>
                      </div>
                    </div>
                  </GlassCard>
                </motion.div>
              );
            })}
          </div>
        )}
      </motion.div>

      {/* Opt-Out Log */}
      <motion.div variants={item} className="mb-8">
        <GlassCard>
          <h3 className="text-lg font-semibold text-white mb-4">Recent Opt-Outs</h3>
          <DataTable data={optOuts} columns={optOutColumns} searchable pageSize={10} />
        </GlassCard>
      </motion.div>

      {/* Compliance Tips */}
      <motion.div variants={item}>
        <GlassCard>
          <h3 className="text-lg font-semibold text-white mb-4">Compliance Tips & Warnings</h3>
          <div className="space-y-3">
            {tips.map((tip, i) => {
              const TipIcon = tip.icon;
              const colorMap: Record<string, string> = {
                blue: "text-blue-400 bg-blue-500/20",
                amber: "text-amber-400 bg-amber-500/20",
                emerald: "text-emerald-400 bg-emerald-500/20",
                rose: "text-rose-400 bg-rose-500/20",
              };
              const colors = colorMap[tip.color] || colorMap.blue;
              return (
                <motion.button
                  key={i}
                  onClick={() => setExpandedTip(expandedTip === i ? null : i)}
                  className="w-full flex items-start gap-3 p-3 rounded-xl bg-white/5 hover:bg-white/8 transition-colors text-left"
                  whileHover={{ x: 4 }}
                >
                  <div className={clsx("w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0", colors.split(" ")[1])}>
                    <TipIcon className={clsx("w-4 h-4", colors.split(" ")[0])} />
                  </div>
                  <p className="text-sm text-gray-300 flex-1">{tip.text}</p>
                  <ChevronRight className={clsx("w-4 h-4 text-gray-500 transition-transform mt-0.5", expandedTip === i && "rotate-90")} />
                </motion.button>
              );
            })}
          </div>
        </GlassCard>
      </motion.div>
    </motion.div>
  );
}
