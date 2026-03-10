import { useState } from "react";
import { motion } from "framer-motion";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Search,
  Loader2,
  Shield,
  ShieldCheck,
  ToggleLeft,
  ToggleRight,
  Mail,
  Building2,
} from "lucide-react";
import clsx from "clsx";
import toast from "react-hot-toast";
import GlassCard from "../../components/ui/GlassCard";
import api from "../../lib/api";

const container = { hidden: { opacity: 0 }, show: { opacity: 1, transition: { staggerChildren: 0.05 } } };
const item = { hidden: { opacity: 0, y: 20 }, show: { opacity: 1, y: 0 } };

interface UserItem {
  id: string;
  email: string;
  full_name: string;
  role: string;
  is_active: boolean;
  is_superadmin: boolean;
  tenant_id: string;
  tenant_name?: string;
  last_login_at: string | null;
  created_at: string;
}

const roleColors: Record<string, string> = {
  owner: "bg-purple-500/20 text-purple-400",
  admin: "bg-blue-500/20 text-blue-400",
  manager: "bg-emerald-500/20 text-emerald-400",
  member: "bg-gray-500/20 text-gray-400",
};

function formatTimeAgo(dateStr: string | null): string {
  if (!dateStr) return "Never";
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days < 30) return `${days}d ago`;
  return new Date(dateStr).toLocaleDateString();
}

export default function AdminUsers() {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");
  const [roleFilter, setRoleFilter] = useState("");
  const [page, setPage] = useState(1);

  const { data, isLoading } = useQuery({
    queryKey: ["admin-users", page, search, roleFilter],
    queryFn: async () => {
      const params = new URLSearchParams({ page: String(page), per_page: "20" });
      if (search) params.set("search", search);
      if (roleFilter) params.set("role", roleFilter);
      const res = await api.get(`/admin/users?${params}`);
      return res.data;
    },
  });

  const toggleMutation = useMutation({
    mutationFn: async ({ userId, field, value }: { userId: string; field: string; value: boolean }) => {
      await api.put(`/admin/users/${userId}`, { [field]: value });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-users"] });
      toast.success("User updated");
    },
    onError: (err: any) => {
      const msg = err?.response?.data?.detail || "Failed to update user";
      toast.error(msg);
    },
  });

  const users: UserItem[] = data?.users || [];
  const total = data?.total || 0;
  const pageCount = Math.ceil(total / 20);

  return (
    <motion.div variants={container} initial="hidden" animate="show">
      <motion.div variants={item} className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold text-white">Users</h1>
          <p className="text-gray-400 mt-1">{total} total users across all tenants</p>
        </div>
      </motion.div>

      {/* Filters */}
      <motion.div variants={item} className="flex flex-wrap gap-4 mb-6">
        <div className="relative flex-1 min-w-[200px]">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
          <input
            type="text"
            placeholder="Search by name or email..."
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(1); }}
            className="w-full pl-10 pr-4 py-2.5 bg-white/5 border border-white/10 rounded-xl text-sm text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50"
          />
        </div>
        <select
          value={roleFilter}
          onChange={(e) => { setRoleFilter(e.target.value); setPage(1); }}
          className="px-4 py-2.5 bg-white/5 border border-white/10 rounded-xl text-sm text-gray-300 focus:outline-none"
        >
          <option value="">All Roles</option>
          <option value="owner">Owner</option>
          <option value="admin">Admin</option>
          <option value="manager">Manager</option>
          <option value="member">Member</option>
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
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">User</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Tenant</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Role</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Superadmin</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Last Login</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Active</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5">
                  {users.map((u) => (
                    <motion.tr
                      key={u.id}
                      whileHover={{ backgroundColor: "rgba(255,255,255,0.03)" }}
                      className="transition-colors"
                    >
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-3">
                          <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center text-white text-xs font-bold">
                            {u.full_name ? u.full_name.charAt(0).toUpperCase() : u.email.charAt(0).toUpperCase()}
                          </div>
                          <div>
                            <p className="text-sm font-medium text-white">{u.full_name || "Unnamed"}</p>
                            <p className="text-xs text-gray-500 flex items-center gap-1">
                              <Mail className="w-3 h-3" /> {u.email}
                            </p>
                          </div>
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <span className="text-sm text-gray-300 flex items-center gap-1.5">
                          <Building2 className="w-3.5 h-3.5 text-gray-500" />
                          {u.tenant_name || u.tenant_id.slice(0, 8)}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <span className={clsx("px-2 py-1 rounded-full text-xs font-medium", roleColors[u.role] || roleColors.member)}>
                          {u.role}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <button
                          onClick={() => toggleMutation.mutate({ userId: u.id, field: "is_superadmin", value: !u.is_superadmin })}
                          className="flex items-center gap-1.5 group"
                          title={u.is_superadmin ? "Remove superadmin" : "Make superadmin"}
                        >
                          {u.is_superadmin ? (
                            <>
                              <ShieldCheck className="w-4 h-4 text-rose-400" />
                              <span className="text-xs text-rose-400 font-medium">Yes</span>
                            </>
                          ) : (
                            <>
                              <Shield className="w-4 h-4 text-gray-600 group-hover:text-gray-400" />
                              <span className="text-xs text-gray-600 group-hover:text-gray-400">No</span>
                            </>
                          )}
                        </button>
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-500">
                        {formatTimeAgo(u.last_login_at)}
                      </td>
                      <td className="px-4 py-3">
                        <button
                          onClick={() => toggleMutation.mutate({ userId: u.id, field: "is_active", value: !u.is_active })}
                          className="flex items-center"
                          title={u.is_active ? "Deactivate user" : "Activate user"}
                        >
                          {u.is_active ? (
                            <ToggleRight className="w-7 h-7 text-emerald-400" />
                          ) : (
                            <ToggleLeft className="w-7 h-7 text-gray-600" />
                          )}
                        </button>
                      </td>
                    </motion.tr>
                  ))}
                </tbody>
              </table>
            </div>
            {pageCount > 1 && (
              <div className="flex items-center justify-between px-4 py-3 border-t border-white/5 text-sm text-gray-400">
                <span>{total} users</span>
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
