import { motion } from "framer-motion";
import { useQuery } from "@tanstack/react-query";
import { Send, CheckCircle, XCircle, MessageSquare, TrendingUp, Users, DollarSign, Phone } from "lucide-react";
import StatCard from "../components/ui/StatCard";
import GlassCard from "../components/ui/GlassCard";
import api from "../lib/api";

const container = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: { staggerChildren: 0.1 },
  },
};

const item = {
  hidden: { opacity: 0, y: 20 },
  show: { opacity: 1, y: 0 },
};

export default function Dashboard() {
  const { error } = useQuery({
    queryKey: ["dashboard"],
    queryFn: async () => {
      const res = await api.get("/dashboard");
      return res.data;
    },
    retry: 1,
  });

  if (error) return <div className="p-8 text-center text-red-400">Failed to load data. Please try again.</div>;

  return (
    <div>
      <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} className="mb-8">
        <h1 className="text-3xl font-bold text-white">Dashboard</h1>
        <p className="text-gray-400 mt-1">Welcome back. Here's your messaging overview.</p>
      </motion.div>

      <motion.div variants={container} initial="hidden" animate="show" className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <motion.div variants={item}>
          <StatCard title="Messages Sent" value={12847} icon={Send} trend={12.5} color="blue" />
        </motion.div>
        <motion.div variants={item}>
          <StatCard title="Delivered" value={12203} icon={CheckCircle} trend={8.3} color="emerald" />
        </motion.div>
        <motion.div variants={item}>
          <StatCard title="Failed" value={644} icon={XCircle} trend={-2.1} color="rose" />
        </motion.div>
        <motion.div variants={item}>
          <StatCard title="Responses" value={3891} icon={MessageSquare} trend={15.7} color="amber" />
        </motion.div>
      </motion.div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <motion.div variants={item} initial="hidden" animate="show" className="lg:col-span-2">
          <GlassCard>
            <h3 className="text-lg font-semibold text-white mb-4">Message Volume</h3>
            <div className="h-64 flex items-center justify-center text-gray-500">
              Chart placeholder — Recharts area chart will render here
            </div>
          </GlassCard>
        </motion.div>
        <motion.div variants={item} initial="hidden" animate="show">
          <GlassCard>
            <h3 className="text-lg font-semibold text-white mb-4">Quick Stats</h3>
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-gray-400">
                  <TrendingUp className="w-4 h-4" />
                  <span className="text-sm">Delivery Rate</span>
                </div>
                <span className="text-sm font-mono font-bold text-emerald-400">94.9%</span>
              </div>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-gray-400">
                  <Users className="w-4 h-4" />
                  <span className="text-sm">Active Contacts</span>
                </div>
                <span className="text-sm font-mono font-bold text-blue-400">24,891</span>
              </div>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-gray-400">
                  <Phone className="w-4 h-4" />
                  <span className="text-sm">Active Numbers</span>
                </div>
                <span className="text-sm font-mono font-bold text-indigo-400">12</span>
              </div>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-gray-400">
                  <DollarSign className="w-4 h-4" />
                  <span className="text-sm">Spent Today</span>
                </div>
                <span className="text-sm font-mono font-bold text-amber-400">$142.30</span>
              </div>
            </div>
          </GlassCard>
        </motion.div>
      </div>
    </div>
  );
}
