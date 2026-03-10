import { motion } from "framer-motion";
import { useQuery } from "@tanstack/react-query";
import {
  Activity,
  Database,
  Cpu,
  HardDrive,
  CheckCircle2,
  XCircle,
  Loader2,
  RefreshCw,
} from "lucide-react";
import clsx from "clsx";
import GlassCard from "../../components/ui/GlassCard";
import api from "../../lib/api";

const container = { hidden: { opacity: 0 }, show: { opacity: 1, transition: { staggerChildren: 0.06 } } };
const item = { hidden: { opacity: 0, y: 20 }, show: { opacity: 1, y: 0 } };

interface HealthCheck {
  status: string;
  database: string;
  redis: string;
  celery: string;
  uptime?: string;
  version?: string;
}

interface WorkerInfo {
  name: string;
  status: string;
  queues: string[];
  active_tasks: number;
  processed: number;
}

export default function AdminSystem() {
  const { data: health, isLoading: healthLoading, refetch: refetchHealth } = useQuery<HealthCheck>({
    queryKey: ["admin-health"],
    queryFn: async () => {
      const res = await api.get("/admin/health");
      return res.data;
    },
    refetchInterval: 30000,
  });

  const { data: workersData, isLoading: workersLoading, refetch: refetchWorkers } = useQuery<{ workers: WorkerInfo[] }>({
    queryKey: ["admin-workers"],
    queryFn: async () => {
      const res = await api.get("/admin/workers");
      return res.data;
    },
    refetchInterval: 30000,
  });

  const isLoading = healthLoading || workersLoading;

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-96">
        <Loader2 className="w-8 h-8 text-rose-400 animate-spin" />
      </div>
    );
  }

  const workers = workersData?.workers || [];

  const serviceStatus = [
    { name: "Database", status: health?.database || "unknown", icon: Database },
    { name: "Redis", status: health?.redis || "unknown", icon: HardDrive },
    { name: "Celery", status: health?.celery || "unknown", icon: Cpu },
  ];

  return (
    <motion.div variants={container} initial="hidden" animate="show">
      <motion.div variants={item} className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold text-white">System Health</h1>
          <p className="text-gray-400 mt-1">Infrastructure and service monitoring</p>
        </div>
        <button
          onClick={() => { refetchHealth(); refetchWorkers(); }}
          className="flex items-center gap-2 px-4 py-2 rounded-xl bg-white/5 border border-white/10 text-gray-400 hover:text-white hover:bg-white/10 transition-colors text-sm"
        >
          <RefreshCw className="w-4 h-4" /> Refresh
        </button>
      </motion.div>

      {/* Overall Status */}
      <motion.div variants={item} className="mb-8">
        <GlassCard>
          <div className="flex items-center gap-4">
            <div className={clsx(
              "w-16 h-16 rounded-2xl flex items-center justify-center",
              health?.status === "healthy" ? "bg-emerald-500/20" : "bg-amber-500/20"
            )}>
              <Activity className={clsx(
                "w-8 h-8",
                health?.status === "healthy" ? "text-emerald-400" : "text-amber-400"
              )} />
            </div>
            <div>
              <h2 className={clsx(
                "text-2xl font-bold",
                health?.status === "healthy" ? "text-emerald-400" : "text-amber-400"
              )}>
                {health?.status === "healthy" ? "All Systems Operational" : "Degraded Performance"}
              </h2>
              <p className="text-gray-400 text-sm mt-1">
                {health?.version && `Version: ${health.version}`}
                {health?.uptime && ` | Uptime: ${health.uptime}`}
              </p>
            </div>
          </div>
        </GlassCard>
      </motion.div>

      {/* Service Status Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
        {serviceStatus.map((service) => {
          const isHealthy = service.status === "healthy" || service.status === "ok" || service.status === "connected";
          return (
            <motion.div key={service.name} variants={item}>
              <GlassCard hover>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className={clsx("w-10 h-10 rounded-xl flex items-center justify-center", isHealthy ? "bg-emerald-500/20" : "bg-rose-500/20")}>
                      <service.icon className={clsx("w-5 h-5", isHealthy ? "text-emerald-400" : "text-rose-400")} />
                    </div>
                    <div>
                      <p className="text-sm font-medium text-white">{service.name}</p>
                      <p className={clsx("text-xs", isHealthy ? "text-emerald-400" : "text-rose-400")}>
                        {service.status}
                      </p>
                    </div>
                  </div>
                  {isHealthy ? (
                    <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                  ) : (
                    <XCircle className="w-5 h-5 text-rose-400" />
                  )}
                </div>
              </GlassCard>
            </motion.div>
          );
        })}
      </div>

      {/* Workers */}
      <motion.div variants={item}>
        <GlassCard className="p-0 overflow-hidden">
          <div className="px-6 py-4 border-b border-white/5">
            <h3 className="text-sm font-semibold text-white">Celery Workers</h3>
          </div>
          {workers.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="bg-white/5">
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Worker</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Status</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Queues</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Active Tasks</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Processed</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5">
                  {workers.map((w, i) => (
                    <tr key={i} className="hover:bg-white/5 transition-colors">
                      <td className="px-4 py-3 text-sm text-white font-mono">{w.name}</td>
                      <td className="px-4 py-3">
                        <span className={clsx(
                          "px-2 py-1 rounded-full text-xs font-medium",
                          w.status === "online" ? "bg-emerald-500/20 text-emerald-400" : "bg-rose-500/20 text-rose-400"
                        )}>
                          {w.status}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex gap-1 flex-wrap">
                          {w.queues.map((q) => (
                            <span key={q} className="px-2 py-0.5 rounded-md bg-white/5 text-xs text-gray-400">{q}</span>
                          ))}
                        </div>
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-300 font-mono">{w.active_tasks}</td>
                      <td className="px-4 py-3 text-sm text-gray-300 font-mono">{w.processed.toLocaleString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="px-6 py-12 text-center text-gray-500 text-sm">
              No worker data available
            </div>
          )}
        </GlassCard>
      </motion.div>
    </motion.div>
  );
}
