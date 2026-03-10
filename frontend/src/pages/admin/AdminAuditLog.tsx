import { useState } from "react";
import { motion } from "framer-motion";
import { useQuery } from "@tanstack/react-query";
import { Search, Loader2 } from "lucide-react";
import clsx from "clsx";
import GlassCard from "../../components/ui/GlassCard";
import api from "../../lib/api";

const container = { hidden: { opacity: 0 }, show: { opacity: 1, transition: { staggerChildren: 0.06 } } };
const item = { hidden: { opacity: 0, y: 20 }, show: { opacity: 1, y: 0 } };

interface AuditEntry {
  id: string;
  action: string;
  resource_type: string;
  resource_id: string | null;
  user_email: string;
  tenant_id: string | null;
  details: Record<string, unknown>;
  ip_address: string | null;
  created_at: string;
}

const actionColors: Record<string, string> = {
  create: "text-emerald-400",
  update: "text-blue-400",
  delete: "text-rose-400",
  login: "text-purple-400",
  approve: "text-emerald-400",
  reject: "text-rose-400",
};

function getActionColor(action: string): string {
  for (const [key, color] of Object.entries(actionColors)) {
    if (action.toLowerCase().includes(key)) return color;
  }
  return "text-gray-400";
}

function formatDateTime(dateStr: string): string {
  const d = new Date(dateStr);
  return d.toLocaleString();
}

export default function AdminAuditLog() {
  const [search, setSearch] = useState("");
  const [actionFilter, setActionFilter] = useState("");
  const [page, setPage] = useState(1);

  const { data, isLoading } = useQuery({
    queryKey: ["admin-audit-log", page, search, actionFilter],
    queryFn: async () => {
      const params = new URLSearchParams({ page: String(page), per_page: "30" });
      if (search) params.set("search", search);
      if (actionFilter) params.set("action", actionFilter);
      const res = await api.get(`/admin/audit-log?${params}`);
      return res.data;
    },
  });

  const entries: AuditEntry[] = data?.entries || data?.events || [];
  const total = data?.total || 0;
  const pageCount = Math.ceil(total / 30);

  return (
    <motion.div variants={container} initial="hidden" animate="show">
      <motion.div variants={item} className="mb-8">
        <h1 className="text-3xl font-bold text-white">Audit Log</h1>
        <p className="text-gray-400 mt-1">Complete record of all platform actions</p>
      </motion.div>

      {/* Filters */}
      <motion.div variants={item} className="flex flex-wrap gap-4 mb-6">
        <div className="relative flex-1 min-w-[200px]">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
          <input
            type="text"
            placeholder="Search by email, action, or resource..."
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(1); }}
            className="w-full pl-10 pr-4 py-2.5 bg-white/5 border border-white/10 rounded-xl text-sm text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50"
          />
        </div>
        <select
          value={actionFilter}
          onChange={(e) => { setActionFilter(e.target.value); setPage(1); }}
          className="px-4 py-2.5 bg-white/5 border border-white/10 rounded-xl text-sm text-gray-300 focus:outline-none"
        >
          <option value="">All Actions</option>
          <option value="dlc_application_submitted">DLC Submitted</option>
          <option value="dlc_application_approved">DLC Approved</option>
          <option value="dlc_application_rejected">DLC Rejected</option>
          <option value="user_updated_by_admin">User Updated</option>
          <option value="tenant_signup">Tenant Signup</option>
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
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Timestamp</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Action</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">User</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Resource</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">IP</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Details</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5">
                  {entries.map((entry) => (
                    <tr key={entry.id} className="hover:bg-white/5 transition-colors">
                      <td className="px-4 py-3 text-xs text-gray-500 whitespace-nowrap">{formatDateTime(entry.created_at)}</td>
                      <td className="px-4 py-3">
                        <span className={clsx("text-sm font-medium", getActionColor(entry.action))}>
                          {entry.action.replace(/_/g, " ")}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-300">{entry.user_email}</td>
                      <td className="px-4 py-3">
                        <span className="text-sm text-gray-400">{entry.resource_type}</span>
                        {entry.resource_id && (
                          <span className="text-xs text-gray-600 ml-1 font-mono">#{entry.resource_id.slice(0, 8)}</span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-xs text-gray-500 font-mono">{entry.ip_address || "--"}</td>
                      <td className="px-4 py-3 text-xs text-gray-500 max-w-[200px] truncate">
                        {Object.keys(entry.details || {}).length > 0
                          ? JSON.stringify(entry.details)
                          : "--"}
                      </td>
                    </tr>
                  ))}
                  {entries.length === 0 && (
                    <tr>
                      <td colSpan={6} className="px-4 py-12 text-center text-gray-500">No audit entries found</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
            {pageCount > 1 && (
              <div className="flex items-center justify-between px-4 py-3 border-t border-white/5 text-sm text-gray-400">
                <span>{total} entries</span>
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
