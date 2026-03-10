import { useState, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  LineChart,
  Line,
  BarChart,
  Bar,
} from "recharts";
import {
  Calendar,
  TrendingUp,
  BarChart3,
  Phone,
  DollarSign,
  Users,
  Award,
} from "lucide-react";
import clsx from "clsx";
import GlassCard from "../components/ui/GlassCard";
import AnimatedCounter from "../components/ui/AnimatedCounter";
import api from "../lib/api";

const container = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { staggerChildren: 0.1 } },
};

const item = {
  hidden: { opacity: 0, y: 20 },
  show: { opacity: 1, y: 0 },
};

const volumeData = [
  { date: "Mar 1", sent: 3200, delivered: 3050, failed: 150 },
  { date: "Mar 2", sent: 4100, delivered: 3920, failed: 180 },
  { date: "Mar 3", sent: 3800, delivered: 3650, failed: 150 },
  { date: "Mar 4", sent: 5200, delivered: 4980, failed: 220 },
  { date: "Mar 5", sent: 4800, delivered: 4600, failed: 200 },
  { date: "Mar 6", sent: 6100, delivered: 5850, failed: 250 },
  { date: "Mar 7", sent: 5500, delivered: 5280, failed: 220 },
  { date: "Mar 8", sent: 4900, delivered: 4700, failed: 200 },
  { date: "Mar 9", sent: 5800, delivered: 5560, failed: 240 },
];

const contactGrowthData = [
  { date: "Jan", contacts: 15200 },
  { date: "Feb", contacts: 17800 },
  { date: "Mar", contacts: 19400 },
  { date: "Apr", contacts: 21100 },
  { date: "May", contacts: 22900 },
  { date: "Jun", contacts: 24891 },
];

const spendData = [
  { name: "SMS", value: 2840, color: "#3b82f6" },
  { name: "MMS", value: 1260, color: "#8b5cf6" },
  { name: "Numbers", value: 360, color: "#10b981" },
  { name: "AI Agents", value: 520, color: "#f59e0b" },
];

const numberUtilization = [
  { number: "+1 (555) 100-0001", sent: 4200, capacity: 5000 },
  { number: "+1 (555) 100-0002", sent: 3800, capacity: 5000 },
  { number: "+1 (555) 100-0003", sent: 2900, capacity: 5000 },
  { number: "+1 (555) 100-0004", sent: 1200, capacity: 5000 },
  { number: "+1 (555) 100-0005", sent: 4800, capacity: 5000 },
  { number: "+1 (555) 100-0006", sent: 3100, capacity: 5000 },
];

const topCampaigns = [
  { name: "Flash Sale Q1", sent: 25400, delivered: 24200, rate: 95.3, revenue: "$12,400" },
  { name: "Welcome Series", sent: 18900, delivered: 18200, rate: 96.3, revenue: "$8,200" },
  { name: "Re-engagement Mar", sent: 15200, delivered: 14100, rate: 92.8, revenue: "$5,800" },
  { name: "Loyalty Rewards", sent: 12800, delivered: 12400, rate: 96.9, revenue: "$4,100" },
  { name: "Product Launch", sent: 9600, delivered: 9100, rate: 94.8, revenue: "$3,600" },
];

type DateRange = "7d" | "14d" | "30d" | "90d";

const dateRanges: { key: DateRange; label: string }[] = [
  { key: "7d", label: "7 Days" },
  { key: "14d", label: "14 Days" },
  { key: "30d", label: "30 Days" },
  { key: "90d", label: "90 Days" },
];

const CustomTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload) return null;
  return (
    <div className="bg-navy-900/95 backdrop-blur-xl border border-white/10 rounded-xl p-3 shadow-2xl">
      <p className="text-xs text-gray-400 mb-2">{label}</p>
      {payload.map((entry: any, i: number) => (
        <div key={i} className="flex items-center gap-2 text-sm">
          <div className="w-2 h-2 rounded-full" style={{ backgroundColor: entry.color }} />
          <span className="text-gray-400">{entry.name}:</span>
          <span className="text-white font-mono font-medium">{entry.value.toLocaleString()}</span>
        </div>
      ))}
    </div>
  );
};

export default function Analytics() {
  const [dateRange, setDateRange] = useState<DateRange>("7d");

  // Fetch analytics data based on date range
  const { data: analyticsData, error } = useQuery({
    queryKey: ["analytics", dateRange],
    queryFn: async () => {
      try {
        const res = await api.get("/analytics/volume", { params: { period: dateRange } });
        return res.data as { volume: typeof volumeData } | null;
      } catch {
        // Fallback to static data if API not available
        return null;
      }
    },
  });

  // Use API data if available, otherwise use static data
  const activeVolumeData = analyticsData?.volume ?? volumeData;

  if (error) return <div className="p-8 text-center text-red-400">Failed to load data. Please try again.</div>;

  const totalSent = useMemo(() => activeVolumeData.reduce((sum, d) => sum + d.sent, 0), [activeVolumeData]);
  const totalDelivered = useMemo(() => activeVolumeData.reduce((sum, d) => sum + d.delivered, 0), [activeVolumeData]);
  const totalFailed = useMemo(() => activeVolumeData.reduce((sum, d) => sum + d.failed, 0), [activeVolumeData]);
  const deliveryRate = totalSent > 0 ? ((totalDelivered / totalSent) * 100).toFixed(1) : "0.0";

  return (
    <motion.div variants={container} initial="hidden" animate="show">
      {/* Header */}
      <motion.div variants={item} className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-8">
        <div>
          <h1 className="text-3xl font-bold text-white">Analytics</h1>
          <p className="text-gray-400 mt-1">Track your messaging performance and ROI.</p>
        </div>

        {/* Date Range Picker */}
        <div className="flex gap-1 bg-white/5 rounded-xl p-1 border border-white/10">
          {dateRanges.map((range) => (
            <button
              key={range.key}
              onClick={() => setDateRange(range.key)}
              className={clsx(
                "relative px-4 py-2 rounded-lg text-sm font-medium transition-colors",
                dateRange === range.key ? "text-white" : "text-gray-400 hover:text-gray-200"
              )}
            >
              {dateRange === range.key && (
                <motion.div
                  layoutId="analytics-range"
                  className="absolute inset-0 bg-white/10 rounded-lg"
                  transition={{ type: "spring", stiffness: 400, damping: 30 }}
                />
              )}
              <span className="relative flex items-center gap-1.5">
                <Calendar className="w-3.5 h-3.5" />
                {range.label}
              </span>
            </button>
          ))}
        </div>
      </motion.div>

      {/* Quick Stats */}
      <motion.div variants={item} className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
        {[
          { label: "Total Sent", value: totalSent, icon: TrendingUp, color: "from-blue-500 to-indigo-600" },
          { label: "Delivered", value: totalDelivered, icon: BarChart3, color: "from-emerald-500 to-teal-600" },
          { label: "Failed", value: totalFailed, icon: BarChart3, color: "from-rose-500 to-pink-600" },
          { label: "Delivery Rate", value: 0, icon: Award, color: "from-amber-500 to-orange-600", displayValue: `${deliveryRate}%` },
        ].map((stat, i) => {
          const Icon = stat.icon;
          return (
            <GlassCard key={i}>
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs text-gray-400 mb-1">{stat.label}</p>
                  {stat.displayValue ? (
                    <p className="text-2xl font-bold font-mono text-white">{stat.displayValue}</p>
                  ) : (
                    <AnimatedCounter value={stat.value} className="text-2xl font-bold font-mono text-white" />
                  )}
                </div>
                <div className={clsx("w-10 h-10 rounded-xl bg-gradient-to-br flex items-center justify-center", stat.color)}>
                  <Icon className="w-5 h-5 text-white" />
                </div>
              </div>
            </GlassCard>
          );
        })}
      </motion.div>

      {/* Volume Chart */}
      <motion.div variants={item} className="mb-8">
        <GlassCard>
          <h3 className="text-lg font-semibold text-white mb-6">Message Volume</h3>
          <div className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={activeVolumeData}>
                <defs>
                  <linearGradient id="sentGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="deliveredGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#10b981" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="failedGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#ef4444" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#ef4444" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                <XAxis dataKey="date" stroke="rgba(255,255,255,0.3)" tick={{ fill: "rgba(255,255,255,0.4)", fontSize: 12 }} />
                <YAxis stroke="rgba(255,255,255,0.3)" tick={{ fill: "rgba(255,255,255,0.4)", fontSize: 12 }} />
                <Tooltip content={<CustomTooltip />} />
                <Area type="monotone" dataKey="sent" name="Sent" stroke="#3b82f6" strokeWidth={2} fill="url(#sentGradient)" />
                <Area type="monotone" dataKey="delivered" name="Delivered" stroke="#10b981" strokeWidth={2} fill="url(#deliveredGradient)" />
                <Area type="monotone" dataKey="failed" name="Failed" stroke="#ef4444" strokeWidth={2} fill="url(#failedGradient)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </GlassCard>
      </motion.div>

      {/* Middle Row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
        {/* Top Campaigns */}
        <motion.div variants={item} className="lg:col-span-2">
          <GlassCard>
            <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
              <Award className="w-5 h-5 text-amber-400" />
              Top Campaigns
            </h3>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-white/5">
                    <th className="text-left text-xs text-gray-400 uppercase tracking-wider pb-3 px-2">#</th>
                    <th className="text-left text-xs text-gray-400 uppercase tracking-wider pb-3 px-2">Campaign</th>
                    <th className="text-left text-xs text-gray-400 uppercase tracking-wider pb-3 px-2">Sent</th>
                    <th className="text-left text-xs text-gray-400 uppercase tracking-wider pb-3 px-2">Rate</th>
                    <th className="text-left text-xs text-gray-400 uppercase tracking-wider pb-3 px-2">Revenue</th>
                  </tr>
                </thead>
                <tbody>
                  {topCampaigns.map((camp, i) => (
                    <motion.tr
                      key={camp.name}
                      initial={{ opacity: 0, x: -10 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: 0.3 + i * 0.1 }}
                      className="border-b border-white/5 last:border-0 hover:bg-white/5 transition-colors"
                    >
                      <td className="py-3 px-2">
                        <span className={clsx(
                          "w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold",
                          i === 0 ? "bg-amber-500/20 text-amber-400" :
                          i === 1 ? "bg-gray-400/20 text-gray-300" :
                          i === 2 ? "bg-orange-500/20 text-orange-400" :
                          "bg-white/5 text-gray-500"
                        )}>
                          {i + 1}
                        </span>
                      </td>
                      <td className="py-3 px-2 text-sm text-white font-medium">{camp.name}</td>
                      <td className="py-3 px-2 text-sm text-gray-300 font-mono">{camp.sent.toLocaleString()}</td>
                      <td className="py-3 px-2">
                        <span className={clsx(
                          "text-sm font-mono font-medium",
                          camp.rate >= 95 ? "text-emerald-400" : camp.rate >= 90 ? "text-amber-400" : "text-rose-400"
                        )}>
                          {camp.rate}%
                        </span>
                      </td>
                      <td className="py-3 px-2 text-sm text-emerald-400 font-mono font-medium">{camp.revenue}</td>
                    </motion.tr>
                  ))}
                </tbody>
              </table>
            </div>
          </GlassCard>
        </motion.div>

        {/* Spend Breakdown */}
        <motion.div variants={item}>
          <GlassCard className="h-full">
            <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
              <DollarSign className="w-5 h-5 text-emerald-400" />
              Spend Breakdown
            </h3>
            <div className="h-52">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={spendData}
                    cx="50%"
                    cy="50%"
                    innerRadius={50}
                    outerRadius={80}
                    paddingAngle={4}
                    dataKey="value"
                    animationBegin={500}
                    animationDuration={1000}
                  >
                    {spendData.map((entry, i) => (
                      <Cell key={i} fill={entry.color} stroke="transparent" />
                    ))}
                  </Pie>
                  <Tooltip
                    content={({ active, payload }) =>
                      active && payload?.[0] ? (
                        <div className="bg-navy-900/95 backdrop-blur-xl border border-white/10 rounded-lg p-2 shadow-xl">
                          <p className="text-xs text-white font-medium">{payload[0].name}: ${(payload[0].value as number).toLocaleString()}</p>
                        </div>
                      ) : null
                    }
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>
            <div className="space-y-2 mt-2">
              {spendData.map((d) => (
                <div key={d.name} className="flex items-center justify-between text-sm">
                  <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full" style={{ backgroundColor: d.color }} />
                    <span className="text-gray-400">{d.name}</span>
                  </div>
                  <span className="font-mono text-white">${d.value.toLocaleString()}</span>
                </div>
              ))}
            </div>
          </GlassCard>
        </motion.div>
      </div>

      {/* Bottom Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Contact Growth */}
        <motion.div variants={item}>
          <GlassCard>
            <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
              <Users className="w-5 h-5 text-blue-400" />
              Contact Growth
            </h3>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={contactGrowthData}>
                  <defs>
                    <linearGradient id="contactLine" x1="0" y1="0" x2="1" y2="0">
                      <stop offset="0%" stopColor="#3b82f6" />
                      <stop offset="100%" stopColor="#8b5cf6" />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                  <XAxis dataKey="date" stroke="rgba(255,255,255,0.3)" tick={{ fill: "rgba(255,255,255,0.4)", fontSize: 12 }} />
                  <YAxis stroke="rgba(255,255,255,0.3)" tick={{ fill: "rgba(255,255,255,0.4)", fontSize: 12 }} />
                  <Tooltip content={<CustomTooltip />} />
                  <Line type="monotone" dataKey="contacts" name="Contacts" stroke="url(#contactLine)" strokeWidth={3} dot={{ fill: "#3b82f6", strokeWidth: 0, r: 4 }} activeDot={{ r: 6, fill: "#3b82f6", stroke: "#fff", strokeWidth: 2 }} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </GlassCard>
        </motion.div>

        {/* Number Utilization */}
        <motion.div variants={item}>
          <GlassCard>
            <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
              <Phone className="w-5 h-5 text-indigo-400" />
              Number Utilization
            </h3>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={numberUtilization} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" horizontal={false} />
                  <XAxis type="number" stroke="rgba(255,255,255,0.3)" tick={{ fill: "rgba(255,255,255,0.4)", fontSize: 12 }} />
                  <YAxis
                    type="category"
                    dataKey="number"
                    stroke="rgba(255,255,255,0.3)"
                    tick={{ fill: "rgba(255,255,255,0.4)", fontSize: 10 }}
                    width={130}
                  />
                  <Tooltip content={<CustomTooltip />} />
                  <Bar dataKey="sent" name="Messages Sent" fill="#6366f1" radius={[0, 4, 4, 0]} animationBegin={500} animationDuration={1000}>
                    {numberUtilization.map((entry, i) => (
                      <Cell
                        key={i}
                        fill={entry.sent / entry.capacity > 0.8 ? "#ef4444" : entry.sent / entry.capacity > 0.6 ? "#f59e0b" : "#6366f1"}
                      />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </GlassCard>
        </motion.div>
      </div>
    </motion.div>
  );
}
