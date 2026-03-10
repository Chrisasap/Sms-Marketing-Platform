import { useState } from "react";
import { motion } from "framer-motion";
import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { Building2, Search, Loader2 } from "lucide-react";
import clsx from "clsx";
import GlassCard from "../../components/ui/GlassCard";
import api from "../../lib/api";

const container = { hidden: { opacity: 0 }, show: { opacity: 1, transition: { staggerChildren: 0.05 } } };
const item = { hidden: { opacity: 0, y: 20 }, show: { opacity: 1, y: 0 } };

interface TenantItem {
  id: string;
  name: string;
  slug: string;
  plan_tier: string;
  status: string;
  credit_balance: number;
  user_count: number;
  contact_count: number;
  phone_number_count: number;
  created_at: string;
}

const planColors: Record<string, string> = {
  free_trial: "bg-gray-500/20 text-gray-400",
  starter: "bg-blue-500/20 text-blue-400",
  growth: "bg-emerald-500/20 text-emerald-400",
  enterprise: "bg-purple-500/20 text-purple-400",
};

const statusColors: Record<string, string> = {
  active: "bg-emerald-500/20 text-emerald-400",
  suspended: "bg-rose-500/20 text-rose-400",
  canceled: "bg-gray-500/20 text-gray-400",
};

export default function AdminTenants() {
  const navigate = useNavigate();
  const [search, setSearch] = useState("");
  const [planFilter, setPlanFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [page, setPage] = useState(1);

  const { data, isLoading } = useQuery({
    queryKey: ["admin-tenants", page, search, planFilter, statusFilter],
    queryFn: async () => {
      const params = new URLSearchParams({ page: String(page), per_page: "20" });
      if (search) params.set("search", search);
      if (planFilter) params.set("plan_tier", planFilter);
      if (statusFilter) params.set("status", statusFilter);
      const res = await api.get(`/admin/tenants?${params}`);
      return res.data;
    },
  });

  const tenants: TenantItem[] = data?.tenants || [];
  const total = data?.total || 0;
  const pageCount = Math.ceil(total / 20);

  return (
    <motion.div variants={container} initial="hidden" animate="show">
      <motion.div variants={item} className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold text-white">Tenants</h1>
          <p className="text-gray-400 mt-1">{total} total organizations</p>
        </div>
      </motion.div>

      {/* Filters */}
      <motion.div variants={item} className="flex flex-wrap gap-4 mb-6">
        <div className="relative flex-1 min-w-[200px]">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
          <input
            type="text"
            placeholder="Search tenants..."
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(1); }}
            className="w-full pl-10 pr-4 py-2.5 bg-white/5 border border-white/10 rounded-xl text-sm text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50"
          />
        </div>
        <select
          value={planFilter}
          onChange={(e) => { setPlanFilter(e.target.value); setPage(1); }}
          className="px-4 py-2.5 bg-white/5 border border-white/10 rounded-xl text-sm text-gray-300 focus:outline-none"
        >
          <option value="">All Plans</option>
          <option value="free_trial">Free Trial</option>
          <option value="starter">Starter</option>
          <option value="growth">Growth</option>
          <option value="enterprise">Enterprise</option>
        </select>
        <select
          value={statusFilter}
          onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}
          className="px-4 py-2.5 bg-white/5 border border-white/10 rounded-xl text-sm text-gray-300 focus:outline-none"
        >
          <option value="">All Status</option>
          <option value="active">Active</option>
          <option value="suspended">Suspended</option>
          <option value="canceled">Canceled</option>
        </select>
      </motion.div>

      {/* Table */}
      {isLoading ? (
        <div className="flex justify-center py-12"><Loader2 className="w-6 h-6 text-blue-400 animate-spin" /></div>
      ) : (
        <motion.div variants={item}>
          <GlassCard className="p-0 overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="bg-white/5">
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Tenant</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Plan</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Status</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Users</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Contacts</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Numbers</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Credits</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Created</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5">
                  {tenants.map((t) => (
                    <motion.tr
                      key={t.id}
                      whileHover={{ backgroundColor: "rgba(255,255,255,0.03)" }}
                      className="cursor-pointer transition-colors"
                      onClick={() => navigate(`/admin/tenants/${t.id}`)}
                    >
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-3">
                          <div className="w-8 h-8 rounded-lg bg-blue-500/20 flex items-center justify-center">
                            <Building2 className="w-4 h-4 text-blue-400" />
                          </div>
                          <div>
                            <p className="text-sm font-medium text-white">{t.name}</p>
                            <p className="text-xs text-gray-500">{t.slug}</p>
                          </div>
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <span className={clsx("px-2 py-1 rounded-full text-xs font-medium", planColors[t.plan_tier] || planColors.free_trial)}>
                          {t.plan_tier.replace(/_/g, " ")}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <span className={clsx("px-2 py-1 rounded-full text-xs font-medium", statusColors[t.status] || statusColors.active)}>
                          {t.status}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-300">{t.user_count}</td>
                      <td className="px-4 py-3 text-sm text-gray-300">{t.contact_count.toLocaleString()}</td>
                      <td className="px-4 py-3 text-sm text-gray-300">{t.phone_number_count}</td>
                      <td className="px-4 py-3 text-sm text-gray-300 font-mono">${t.credit_balance.toFixed(2)}</td>
                      <td className="px-4 py-3 text-sm text-gray-500">{new Date(t.created_at).toLocaleDateString()}</td>
                    </motion.tr>
                  ))}
                </tbody>
              </table>
            </div>
            {pageCount > 1 && (
              <div className="flex items-center justify-between px-4 py-3 border-t border-white/5 text-sm text-gray-400">
                <span>{total} tenants</span>
                <div className="flex gap-2">
                  <button onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page === 1} className="px-3 py-1 rounded-lg bg-white/5 hover:bg-white/10 disabled:opacity-30">Prev</button>
                  <span className="px-3 py-1">Page {page} of {pageCount}</span>
                  <button onClick={() => setPage((p) => Math.min(pageCount, p + 1))} disabled={page === pageCount} className="px-3 py-1 rounded-lg bg-white/5 hover:bg-white/10 disabled:opacity-30">Next</button>
                </div>
              </div>
            )}
          </GlassCard>
        </motion.div>
      )}
    </motion.div>
  );
}
