import { motion } from "framer-motion";
import { useQuery } from "@tanstack/react-query";
import { DollarSign, TrendingUp, CreditCard, Users, Loader2 } from "lucide-react";
import GlassCard from "../../components/ui/GlassCard";
import StatCard from "../../components/ui/StatCard";
import api from "../../lib/api";

const container = { hidden: { opacity: 0 }, show: { opacity: 1, transition: { staggerChildren: 0.06 } } };
const item = { hidden: { opacity: 0, y: 20 }, show: { opacity: 1, y: 0 } };

export default function AdminRevenue() {
  const { data: overview, isLoading } = useQuery({
    queryKey: ["admin-overview"],
    queryFn: async () => {
      const res = await api.get("/admin/analytics/overview");
      return res.data;
    },
  });

  const { data: revenueData } = useQuery({
    queryKey: ["admin-revenue-12m"],
    queryFn: async () => {
      const res = await api.get("/admin/analytics/revenue?period=12m");
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
  const revenuePoints = revenueData?.data || [];

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
          <StatCard title="ARR" value={mrr * 12} prefix="$" icon={TrendingUp} color="blue" />
        </motion.div>
        <motion.div variants={item}>
          <StatCard title="Paying Tenants" value={overview?.total_tenants ?? 0} icon={Users} color="blue" />
        </motion.div>
        <motion.div variants={item}>
          <StatCard title="Avg Revenue/Tenant" value={overview?.total_tenants ? Math.round(mrr / overview.total_tenants) : 0} prefix="$" icon={CreditCard} color="amber" />
        </motion.div>
      </div>

      {/* Revenue History */}
      <motion.div variants={item}>
        <GlassCard>
          <h3 className="text-sm font-semibold text-white mb-4">Monthly Revenue (Last 12 Months)</h3>
          {revenuePoints.length > 0 ? (
            <div className="space-y-3">
              {revenuePoints.map((point: { month?: string; date?: string; revenue?: number }, i: number) => {
                const label = point.month || point.date || `Month ${i + 1}`;
                const revenue = point.revenue || 0;
                const maxRev = Math.max(...revenuePoints.map((p: { revenue?: number }) => p.revenue || 0), 1);
                return (
                  <div key={i} className="flex items-center gap-4">
                    <span className="text-xs text-gray-500 w-20 text-right">{label}</span>
                    <div className="flex-1 bg-white/5 rounded-full h-6 overflow-hidden">
                      <motion.div
                        initial={{ width: 0 }}
                        animate={{ width: `${(revenue / maxRev) * 100}%` }}
                        transition={{ delay: i * 0.05, duration: 0.5 }}
                        className="h-full bg-gradient-to-r from-emerald-500 to-teal-600 rounded-full flex items-center justify-end px-2"
                      >
                        <span className="text-xs text-white font-mono">${revenue.toLocaleString()}</span>
                      </motion.div>
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <p className="text-gray-500 text-sm text-center py-8">No revenue data available yet</p>
          )}
        </GlassCard>
      </motion.div>
    </motion.div>
  );
}
