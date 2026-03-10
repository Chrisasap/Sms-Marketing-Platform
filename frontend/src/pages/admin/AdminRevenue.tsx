import { useState } from "react";
import { motion } from "framer-motion";
import { useQuery } from "@tanstack/react-query";
import {
  DollarSign,
  TrendingUp,
  CreditCard,
  Users,
  Loader2,
  Building2,
  Crown,
} from "lucide-react";
import clsx from "clsx";
import GlassCard from "../../components/ui/GlassCard";
import StatCard from "../../components/ui/StatCard";
import api from "../../lib/api";

const container = { hidden: { opacity: 0 }, show: { opacity: 1, transition: { staggerChildren: 0.06 } } };
const item = { hidden: { opacity: 0, y: 20 }, show: { opacity: 1, y: 0 } };

type Period = "3m" | "6m" | "12m";

interface RevenuePoint {
  month?: string;
  date?: string;
  revenue?: number;
}

interface PlanBreakdown {
  plan: string;
  count: number;
}

interface TenantItem {
  id: string;
  name: string;
  slug: string;
  plan_tier: string;
  credit_balance: number;
  user_count: number;
  created_at: string;
}

const planColors: Record<string, { bg: string; text: string; bar: string }> = {
  free_trial: { bg: "bg-gray-500/20", text: "text-gray-400", bar: "from-gray-500 to-gray-600" },
  starter: { bg: "bg-blue-500/20", text: "text-blue-400", bar: "from-blue-500 to-indigo-600" },
  growth: { bg: "bg-emerald-500/20", text: "text-emerald-400", bar: "from-emerald-500 to-teal-600" },
  enterprise: { bg: "bg-purple-500/20", text: "text-purple-400", bar: "from-purple-500 to-indigo-600" },
};

export default function AdminRevenue() {
  const [period, setPeriod] = useState<Period>("12m");

  const { data: overview, isLoading } = useQuery({
    queryKey: ["admin-overview"],
    queryFn: async () => {
      const res = await api.get("/admin/analytics/overview");
      return res.data;
    },
  });

  const { data: statsData } = useQuery({
    queryKey: ["admin-stats"],
    queryFn: async () => {
      const res = await api.get("/admin/stats");
      return res.data;
    },
  });

  const { data: revenueData } = useQuery({
    queryKey: ["admin-revenue", period],
    queryFn: async () => {
      const res = await api.get(`/admin/analytics/revenue?period=${period}`);
      return res.data;
    },
  });

  const { data: topTenantsData } = useQuery({
    queryKey: ["admin-top-tenants"],
    queryFn: async () => {
      const res = await api.get("/admin/tenants?per_page=10");
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

  const mrr = overview?.mrr ?? 0;
  const revenueThisMonth = statsData?.revenue_this_month ?? 0;
  const totalTenants = overview?.total_tenants ?? 0;
  const activeSubscriptions = statsData?.active_subscriptions ?? totalTenants;
  const planBreakdown: PlanBreakdown[] = statsData?.plan_breakdown ?? [];
  const revenuePoints: RevenuePoint[] = revenueData?.data || [];
  const maxRevenue = Math.max(...revenuePoints.map((p) => p.revenue || 0), 1);

  const tenants: TenantItem[] = topTenantsData?.tenants || [];
  const topSpenders = [...tenants].sort((a, b) => b.credit_balance - a.credit_balance).slice(0, 10);

  const totalPlanCount = planBreakdown.reduce((sum, p) => sum + p.count, 0) || 1;

  return (
    <motion.div variants={container} initial="hidden" animate="show">
      <motion.div variants={item} className="mb-8">
        <h1 className="text-3xl font-bold text-white">Revenue</h1>
        <p className="text-gray-400 mt-1">Platform revenue overview and billing metrics</p>
      </motion.div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <motion.div variants={item}>
          <StatCard title="MRR" value={mrr} prefix="$" icon={DollarSign} color="emerald" />
        </motion.div>
        <motion.div variants={item}>
          <StatCard title="Revenue This Month" value={revenueThisMonth} prefix="$" icon={TrendingUp} color="blue" />
        </motion.div>
        <motion.div variants={item}>
          <StatCard title="Total Tenants" value={totalTenants} icon={Users} color="amber" />
        </motion.div>
        <motion.div variants={item}>
          <StatCard title="Active Subscriptions" value={activeSubscriptions} icon={CreditCard} color="rose" />
        </motion.div>
      </div>

      {/* Revenue Trend */}
      <motion.div variants={item} className="mb-8">
        <GlassCard>
          <div className="flex items-center justify-between mb-6">
            <h3 className="text-sm font-semibold text-white">Monthly Revenue</h3>
            <div className="flex gap-1 p-1 bg-white/5 rounded-lg">
              {(["3m", "6m", "12m"] as Period[]).map((p) => (
                <button
                  key={p}
                  onClick={() => setPeriod(p)}
                  className={clsx(
                    "px-3 py-1.5 rounded-md text-xs font-medium transition-all",
                    period === p
                      ? "bg-white/10 text-white shadow-sm"
                      : "text-gray-500 hover:text-white hover:bg-white/5"
                  )}
                >
                  {p.toUpperCase()}
                </button>
              ))}
            </div>
          </div>
          {revenuePoints.length > 0 ? (
            <div className="space-y-3">
              {revenuePoints.map((point, i) => {
                const label = point.month || point.date || `Month ${i + 1}`;
                const revenue = point.revenue || 0;
                const pct = (revenue / maxRevenue) * 100;
                return (
                  <div key={i} className="flex items-center gap-4">
                    <span className="text-xs text-gray-500 w-20 text-right font-mono">{label}</span>
                    <div className="flex-1 bg-white/5 rounded-full h-7 overflow-hidden">
                      <motion.div
                        initial={{ width: 0 }}
                        animate={{ width: `${pct}%` }}
                        transition={{ delay: i * 0.05, duration: 0.5 }}
                        className="h-full bg-gradient-to-r from-emerald-500 to-teal-600 rounded-full flex items-center justify-end px-3"
                      >
                        {pct > 15 && (
                          <span className="text-xs text-white font-mono font-medium">
                            ${revenue.toLocaleString()}
                          </span>
                        )}
                      </motion.div>
                    </div>
                    {pct <= 15 && (
                      <span className="text-xs text-gray-500 font-mono w-20">${revenue.toLocaleString()}</span>
                    )}
                  </div>
                );
              })}
            </div>
          ) : (
            <p className="text-gray-500 text-sm text-center py-8">No revenue data available yet</p>
          )}
        </GlassCard>
      </motion.div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Plan Distribution */}
        <motion.div variants={item}>
          <GlassCard>
            <h3 className="text-sm font-semibold text-white mb-4">Plan Distribution</h3>
            {planBreakdown.length > 0 ? (
              <div className="grid grid-cols-2 gap-3">
                {planBreakdown.map((plan) => {
                  const colors = planColors[plan.plan] || planColors.free_trial;
                  const pct = ((plan.count / totalPlanCount) * 100).toFixed(1);
                  return (
                    <motion.div
                      key={plan.plan}
                      whileHover={{ scale: 1.02 }}
                      className={clsx("p-4 rounded-xl border border-white/10", colors.bg)}
                    >
                      <div className="flex items-center justify-between mb-2">
                        <span className={clsx("text-sm font-semibold capitalize", colors.text)}>
                          {plan.plan.replace(/_/g, " ")}
                        </span>
                        <span className="text-xs text-gray-500">{pct}%</span>
                      </div>
                      <p className="text-2xl font-bold text-white">{plan.count}</p>
                      <div className="mt-2 h-1.5 bg-white/10 rounded-full overflow-hidden">
                        <motion.div
                          initial={{ width: 0 }}
                          animate={{ width: `${pct}%` }}
                          transition={{ duration: 0.6 }}
                          className={clsx("h-full rounded-full bg-gradient-to-r", colors.bar)}
                        />
                      </div>
                    </motion.div>
                  );
                })}
              </div>
            ) : (
              <div className="text-center py-8">
                <Users className="w-8 h-8 text-gray-600 mx-auto mb-2" />
                <p className="text-gray-500 text-sm">No plan distribution data</p>
              </div>
            )}
          </GlassCard>
        </motion.div>

        {/* Top Spenders */}
        <motion.div variants={item}>
          <GlassCard>
            <div className="flex items-center gap-2 mb-4">
              <Crown className="w-4 h-4 text-amber-400" />
              <h3 className="text-sm font-semibold text-white">Top Spenders</h3>
            </div>
            {topSpenders.length > 0 ? (
              <div className="space-y-2">
                {topSpenders.map((t, i) => {
                  const colors = planColors[t.plan_tier] || planColors.free_trial;
                  return (
                    <motion.div
                      key={t.id}
                      initial={{ opacity: 0, x: -10 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: i * 0.04 }}
                      className="flex items-center gap-3 p-2.5 rounded-xl hover:bg-white/5 transition-colors"
                    >
                      <span className="text-xs text-gray-600 font-mono w-5 text-right">
                        {i + 1}.
                      </span>
                      <div className="w-8 h-8 rounded-lg bg-blue-500/10 flex items-center justify-center flex-shrink-0">
                        <Building2 className="w-4 h-4 text-blue-400" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm text-white font-medium truncate">{t.name}</p>
                        <span className={clsx("px-1.5 py-0.5 rounded text-[10px] font-medium", colors.bg, colors.text)}>
                          {t.plan_tier.replace(/_/g, " ")}
                        </span>
                      </div>
                      <span className="text-sm text-emerald-400 font-mono font-medium">
                        ${t.credit_balance.toFixed(2)}
                      </span>
                    </motion.div>
                  );
                })}
              </div>
            ) : (
              <div className="text-center py-8">
                <Building2 className="w-8 h-8 text-gray-600 mx-auto mb-2" />
                <p className="text-gray-500 text-sm">No tenant data available</p>
              </div>
            )}
          </GlassCard>
        </motion.div>
      </div>
    </motion.div>
  );
}
