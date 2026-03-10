import { motion } from "framer-motion";
import { useQuery } from "@tanstack/react-query";
import {
  Shield,
  CheckCircle2,
  Clock,
  Brain,
  Loader2,
} from "lucide-react";
import clsx from "clsx";
import GlassCard from "../../components/ui/GlassCard";
import StatCard from "../../components/ui/StatCard";
import api from "../../lib/api";

const container = { hidden: { opacity: 0 }, show: { opacity: 1, transition: { staggerChildren: 0.06 } } };
const item = { hidden: { opacity: 0, y: 20 }, show: { opacity: 1, y: 0 } };

interface ComplianceStats {
  total_applications: number;
  total_pending: number;
  total_approved: number;
  total_rejected: number;
  approval_rate: number;
  ai_metrics: {
    total_reviews: number;
    avg_score: number;
    pass_rate: number;
  };
}

interface RecentApplication {
  id: string;
  tenant_name: string;
  application_type: string;
  status: string;
  ai_score: number | null;
  submitted_at: string;
}

const statusColors: Record<string, string> = {
  pending_review: "bg-amber-500/20 text-amber-400",
  pending: "bg-amber-500/20 text-amber-400",
  approved: "bg-emerald-500/20 text-emerald-400",
  rejected: "bg-rose-500/20 text-rose-400",
  ai_reviewed: "bg-purple-500/20 text-purple-400",
};

function getScoreBadgeColor(score: number | null): string {
  if (score === null) return "bg-gray-500/20 text-gray-400";
  if (score >= 80) return "bg-emerald-500/20 text-emerald-400";
  if (score >= 60) return "bg-amber-500/20 text-amber-400";
  return "bg-rose-500/20 text-rose-400";
}

export default function AdminDLCAnalytics() {
  const { data: stats, isLoading } = useQuery<ComplianceStats>({
    queryKey: ["admin-compliance-stats"],
    queryFn: async () => {
      const res = await api.get("/admin/analytics/compliance");
      return res.data;
    },
  });

  const { data: recentData } = useQuery<{ applications: RecentApplication[] }>({
    queryKey: ["admin-dlc-recent"],
    queryFn: async () => {
      const res = await api.get("/admin/dlc-queue?per_page=20");
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

  const s = stats!;
  const applications = recentData?.applications || [];

  return (
    <motion.div variants={container} initial="hidden" animate="show">
      <motion.div variants={item} className="mb-8">
        <h1 className="text-3xl font-bold text-white">DLC Analytics</h1>
        <p className="text-gray-400 mt-1">10DLC compliance metrics and trends</p>
      </motion.div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <motion.div variants={item}>
          <StatCard title="Approval Rate" value={s.approval_rate} suffix="%" icon={CheckCircle2} color="emerald" />
        </motion.div>
        <motion.div variants={item}>
          <StatCard title="Avg AI Score" value={s.ai_metrics?.avg_score ?? 0} icon={Brain} color="blue" />
        </motion.div>
        <motion.div variants={item}>
          <StatCard title="Pending Review" value={s.total_pending} icon={Clock} color="amber" />
        </motion.div>
        <motion.div variants={item}>
          <StatCard title="Total Applications" value={s.total_applications} icon={Shield} color="blue" />
        </motion.div>
      </div>

      {/* Additional Metrics */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
        <motion.div variants={item}>
          <GlassCard>
            <h3 className="text-sm font-semibold text-white mb-4">Breakdown</h3>
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-400">Approved</span>
                <span className="text-sm font-bold text-emerald-400">{s.total_approved}</span>
              </div>
              <div className="w-full bg-white/5 rounded-full h-2">
                <div className="bg-emerald-500 h-2 rounded-full" style={{ width: `${s.total_applications ? (s.total_approved / s.total_applications) * 100 : 0}%` }} />
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-400">Rejected</span>
                <span className="text-sm font-bold text-rose-400">{s.total_rejected}</span>
              </div>
              <div className="w-full bg-white/5 rounded-full h-2">
                <div className="bg-rose-500 h-2 rounded-full" style={{ width: `${s.total_applications ? (s.total_rejected / s.total_applications) * 100 : 0}%` }} />
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-400">Pending</span>
                <span className="text-sm font-bold text-amber-400">{s.total_pending}</span>
              </div>
              <div className="w-full bg-white/5 rounded-full h-2">
                <div className="bg-amber-500 h-2 rounded-full" style={{ width: `${s.total_applications ? (s.total_pending / s.total_applications) * 100 : 0}%` }} />
              </div>
            </div>
          </GlassCard>
        </motion.div>
        <motion.div variants={item}>
          <GlassCard>
            <h3 className="text-sm font-semibold text-white mb-4">AI Review Metrics</h3>
            <div className="space-y-4">
              <div className="bg-white/5 rounded-xl p-4 text-center">
                <p className="text-2xl font-bold text-purple-400">{s.ai_metrics?.total_reviews ?? 0}</p>
                <p className="text-xs text-gray-500 mt-1">Total AI Reviews</p>
              </div>
              <div className="bg-white/5 rounded-xl p-4 text-center">
                <p className="text-2xl font-bold text-emerald-400">{s.ai_metrics?.pass_rate ?? 0}%</p>
                <p className="text-xs text-gray-500 mt-1">AI Pass Rate</p>
              </div>
            </div>
          </GlassCard>
        </motion.div>
        <motion.div variants={item}>
          <GlassCard>
            <h3 className="text-sm font-semibold text-white mb-4">Score Distribution</h3>
            <div className="space-y-3">
              <div className="flex items-center gap-3">
                <div className="w-3 h-3 rounded-full bg-emerald-500" />
                <span className="text-sm text-gray-400 flex-1">80-100 (Pass)</span>
                <span className="text-sm font-mono text-gray-300">--</span>
              </div>
              <div className="flex items-center gap-3">
                <div className="w-3 h-3 rounded-full bg-amber-500" />
                <span className="text-sm text-gray-400 flex-1">60-79 (Needs Review)</span>
                <span className="text-sm font-mono text-gray-300">--</span>
              </div>
              <div className="flex items-center gap-3">
                <div className="w-3 h-3 rounded-full bg-rose-500" />
                <span className="text-sm text-gray-400 flex-1">0-59 (Fail)</span>
                <span className="text-sm font-mono text-gray-300">--</span>
              </div>
            </div>
          </GlassCard>
        </motion.div>
      </div>

      {/* Recent Applications Table */}
      <motion.div variants={item}>
        <GlassCard className="p-0 overflow-hidden">
          <div className="px-6 py-4 border-b border-white/5">
            <h3 className="text-sm font-semibold text-white">Recent Applications</h3>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="bg-white/5">
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Tenant</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Type</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">AI Score</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Status</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Submitted</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {applications.map((app) => (
                  <tr key={app.id} className="hover:bg-white/5 transition-colors">
                    <td className="px-4 py-3 text-sm text-white">{app.tenant_name}</td>
                    <td className="px-4 py-3 text-sm text-gray-300 capitalize">{app.application_type.replace(/_/g, " ")}</td>
                    <td className="px-4 py-3">
                      {app.ai_score !== null ? (
                        <span className={clsx("px-2 py-1 rounded-full text-xs font-bold", getScoreBadgeColor(app.ai_score))}>
                          {app.ai_score}
                        </span>
                      ) : (
                        <span className="text-xs text-gray-600">--</span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <span className={clsx("px-2 py-1 rounded-full text-xs font-medium", statusColors[app.status] || statusColors.pending)}>
                        {app.status.replace(/_/g, " ")}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-500">{new Date(app.submitted_at).toLocaleDateString()}</td>
                  </tr>
                ))}
                {applications.length === 0 && (
                  <tr>
                    <td colSpan={5} className="px-4 py-12 text-center text-gray-500">No applications found</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </GlassCard>
      </motion.div>
    </motion.div>
  );
}
