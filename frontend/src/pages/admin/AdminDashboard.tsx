import { motion } from "framer-motion";
import { useQuery } from "@tanstack/react-query";
import {
  Building2,
  Users,
  MessageSquare,
  DollarSign,
  ClipboardList,
  Activity,
  TrendingUp,
  Loader2,
} from "lucide-react";
import GlassCard from "../../components/ui/GlassCard";
import StatCard from "../../components/ui/StatCard";
import api from "../../lib/api";

const container = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { staggerChildren: 0.06 } },
};
const item = {
  hidden: { opacity: 0, y: 20 },
  show: { opacity: 1, y: 0 },
};

interface OverviewData {
  total_tenants: number;
  active_tenants_24h: number;
  new_tenants_7d: number;
  new_tenants_30d: number;
  total_users: number;
  active_users_24h: number;
  messages_24h: number;
  messages_7d: number;
  messages_30d: number;
  mrr: number;
  dlc_queue_pending: number;
  system_health: string;
}

interface TimeSeriesPoint {
  date?: string;
  month?: string;
  count?: number;
  revenue?: number;
}

interface ActivityEvent {
  id: string;
  action: string;
  resource_type: string;
  resource_id: string | null;
  user_email: string;
  details: Record<string, unknown>;
  created_at: string;
}

function MiniBarChart({ data, color = "#3b82f6" }: { data: number[]; color?: string }) {
  const max = Math.max(...data, 1);
  return (
    <div className="flex items-end gap-1 h-16">
      {data.map((val, i) => (
        <motion.div
          key={i}
          initial={{ height: 0 }}
          animate={{ height: `${(val / max) * 100}%` }}
          transition={{ delay: i * 0.03, duration: 0.4 }}
          className="flex-1 rounded-t-sm min-w-[3px]"
          style={{ backgroundColor: color, opacity: 0.4 + (val / max) * 0.6 }}
        />
      ))}
    </div>
  );
}

const actionLabels: Record<string, string> = {
  dlc_application_approved: "DLC Application Approved",
  dlc_application_submitted: "DLC Application Submitted",
  dlc_application_rejected: "DLC Application Rejected",
  dlc_ai_enhancement_applied: "AI Enhancement Applied",
  ai_prompt_updated: "AI Prompt Updated",
  user_updated_by_admin: "User Updated",
  tenant_signup: "New Tenant Signup",
};

const actionColors: Record<string, string> = {
  dlc_application_approved: "text-emerald-400",
  dlc_application_submitted: "text-blue-400",
  dlc_application_rejected: "text-rose-400",
  dlc_ai_enhancement_applied: "text-purple-400",
  user_updated_by_admin: "text-amber-400",
  tenant_signup: "text-emerald-400",
};

function formatTimeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

export default function AdminDashboard() {
  const { data: overview, isLoading } = useQuery<OverviewData>({
    queryKey: ["admin-overview"],
    queryFn: async () => {
      const res = await api.get("/admin/analytics/overview");
      return res.data;
    },
    refetchInterval: 60000,
  });

  const { data: msgData } = useQuery<{ data: TimeSeriesPoint[] }>({
    queryKey: ["admin-messages-30d"],
    queryFn: async () => {
      const res = await api.get("/admin/analytics/messages?period=30d");
      return res.data;
    },
  });

  const { data: tenantGrowth } = useQuery<{ data: TimeSeriesPoint[] }>({
    queryKey: ["admin-tenant-growth"],
    queryFn: async () => {
      const res = await api.get("/admin/analytics/tenants/growth?period=90d");
      return res.data;
    },
  });

  const { data: revenueData } = useQuery<{ data: TimeSeriesPoint[] }>({
    queryKey: ["admin-revenue-12m"],
    queryFn: async () => {
      const res = await api.get("/admin/analytics/revenue?period=12m");
      return res.data;
    },
  });

  const { data: activityData } = useQuery<{ events: ActivityEvent[] }>({
    queryKey: ["admin-activity"],
    queryFn: async () => {
      const res = await api.get("/admin/activity-feed?limit=15");
      return res.data;
    },
    refetchInterval: 30000,
  });

  const { data: complianceData } = useQuery({
    queryKey: ["admin-compliance-stats"],
    queryFn: async () => {
      const res = await api.get("/admin/analytics/compliance");
      return res.data;
    },
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-96">
        <Loader2 className="w-8 h-8 text-rose-400 animate-spin" />
      </div>
    );
  }

  const o = overview!;
  const msgCounts = (msgData?.data || []).map((d) => d.count || 0);
  const growthCounts = (tenantGrowth?.data || []).map((d) => d.count || 0);
  const revCounts = (revenueData?.data || []).map((d) => d.revenue || 0);

  return (
    <motion.div variants={container} initial="hidden" animate="show">
      {/* Header */}
      <motion.div variants={item} className="mb-8">
        <h1 className="text-3xl font-bold text-white">Admin Dashboard</h1>
        <p className="text-gray-400 mt-1">Platform overview and real-time metrics</p>
      </motion.div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4 mb-8">
        <motion.div variants={item}>
          <StatCard title="Total Tenants" value={o.total_tenants} icon={Building2} color="blue" />
        </motion.div>
        <motion.div variants={item}>
          <StatCard title="Active Today" value={o.active_users_24h} icon={Users} color="emerald" />
        </motion.div>
        <motion.div variants={item}>
          <StatCard title="Messages (24h)" value={o.messages_24h} icon={MessageSquare} color="blue" />
        </motion.div>
        <motion.div variants={item}>
          <StatCard title="MRR" value={o.mrr} icon={DollarSign} prefix="$" color="emerald" />
        </motion.div>
        <motion.div variants={item}>
          <StatCard title="DLC Queue" value={o.dlc_queue_pending} icon={ClipboardList} color="amber" />
        </motion.div>
        <motion.div variants={item}>
          <GlassCard hover>
            <div className="flex items-start justify-between">
              <div>
                <p className="text-sm text-gray-400 mb-1">System</p>
                <p className={`text-2xl font-bold ${o.system_health === "healthy" ? "text-emerald-400" : "text-amber-400"}`}>
                  {o.system_health === "healthy" ? "Healthy" : "Degraded"}
                </p>
              </div>
              <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${o.system_health === "healthy" ? "bg-emerald-500/20" : "bg-amber-500/20"}`}>
                <Activity className={`w-6 h-6 ${o.system_health === "healthy" ? "text-emerald-400" : "text-amber-400"}`} />
              </div>
            </div>
          </GlassCard>
        </motion.div>
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
        <motion.div variants={item}>
          <GlassCard>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-semibold text-white">Message Volume (30d)</h3>
              <span className="text-xs text-gray-500">{o.messages_30d.toLocaleString()} total</span>
            </div>
            <MiniBarChart data={msgCounts.length > 0 ? msgCounts : [0]} color="#3b82f6" />
          </GlassCard>
        </motion.div>
        <motion.div variants={item}>
          <GlassCard>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-semibold text-white">Tenant Growth (90d)</h3>
              <span className="text-xs text-emerald-400 flex items-center gap-1">
                <TrendingUp className="w-3 h-3" /> +{o.new_tenants_30d} this month
              </span>
            </div>
            <MiniBarChart data={growthCounts.length > 0 ? growthCounts : [0]} color="#10b981" />
          </GlassCard>
        </motion.div>
        <motion.div variants={item}>
          <GlassCard>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-semibold text-white">Revenue (12m)</h3>
              <span className="text-xs text-gray-500">${o.mrr.toLocaleString()} MRR</span>
            </div>
            <MiniBarChart data={revCounts.length > 0 ? revCounts : [0]} color="#f59e0b" />
          </GlassCard>
        </motion.div>
      </div>

      {/* Bottom Row: Compliance + Activity */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Compliance Summary */}
        <motion.div variants={item}>
          <GlassCard>
            <h3 className="text-sm font-semibold text-white mb-4">10DLC Compliance</h3>
            <div className="grid grid-cols-2 gap-4 mb-4">
              <div className="bg-white/5 rounded-xl p-4 text-center">
                <p className="text-2xl font-bold text-emerald-400">{complianceData?.approval_rate ?? 0}%</p>
                <p className="text-xs text-gray-500 mt-1">Approval Rate</p>
              </div>
              <div className="bg-white/5 rounded-xl p-4 text-center">
                <p className="text-2xl font-bold text-blue-400">{complianceData?.ai_metrics?.total_reviews ?? 0}</p>
                <p className="text-xs text-gray-500 mt-1">AI Reviews</p>
              </div>
              <div className="bg-white/5 rounded-xl p-4 text-center">
                <p className="text-2xl font-bold text-amber-400">{complianceData?.total_pending ?? 0}</p>
                <p className="text-xs text-gray-500 mt-1">Pending Review</p>
              </div>
              <div className="bg-white/5 rounded-xl p-4 text-center">
                <p className="text-2xl font-bold text-white">{complianceData?.ai_metrics?.avg_score ?? 0}</p>
                <p className="text-xs text-gray-500 mt-1">Avg AI Score</p>
              </div>
            </div>
          </GlassCard>
        </motion.div>

        {/* Activity Feed */}
        <motion.div variants={item}>
          <GlassCard>
            <h3 className="text-sm font-semibold text-white mb-4">Recent Activity</h3>
            <div className="space-y-3 max-h-72 overflow-y-auto">
              {(activityData?.events || []).length === 0 ? (
                <p className="text-gray-500 text-sm text-center py-8">No recent activity</p>
              ) : (
                (activityData?.events || []).map((event) => (
                  <div key={event.id} className="flex items-start gap-3 py-2 border-b border-white/5 last:border-0">
                    <div className="w-2 h-2 rounded-full bg-blue-500 mt-2 flex-shrink-0" />
                    <div className="flex-1 min-w-0">
                      <p className={`text-sm font-medium ${actionColors[event.action] || "text-gray-300"}`}>
                        {actionLabels[event.action] || event.action.replace(/_/g, " ")}
                      </p>
                      <p className="text-xs text-gray-500 truncate">
                        {event.user_email} &middot; {event.resource_type}
                        {event.resource_id ? ` #${event.resource_id.slice(0, 8)}` : ""}
                      </p>
                    </div>
                    <span className="text-xs text-gray-600 whitespace-nowrap">{formatTimeAgo(event.created_at)}</span>
                  </div>
                ))
              )}
            </div>
          </GlassCard>
        </motion.div>
      </div>
    </motion.div>
  );
}
