import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useParams, useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Building2,
  Users,
  MessageSquare,
  DollarSign,
  Phone,
  ArrowLeft,
  Ban,
  PlayCircle,
  CreditCard,
  UserCog,
  ExternalLink,
  Loader2,
  Shield,
  Clock,
  Mail,
  Hash,
  Plus,
} from "lucide-react";
import clsx from "clsx";
import toast from "react-hot-toast";
import GlassCard from "../../components/ui/GlassCard";
import StatCard from "../../components/ui/StatCard";
import api from "../../lib/api";

const container = { hidden: { opacity: 0 }, show: { opacity: 1, transition: { staggerChildren: 0.06 } } };
const item = { hidden: { opacity: 0, y: 20 }, show: { opacity: 1, y: 0 } };

interface TenantUser {
  id: string;
  full_name: string;
  email: string;
  role: string;
  is_active: boolean;
  mfa_enabled: boolean;
  last_login_at: string | null;
  created_at: string;
}

interface PhoneNumber {
  id: string;
  phone_number: string;
  number_type: string;
  status: string;
  monthly_cost: number;
}

interface TenantStats {
  user_count: number;
  contact_count: number;
  messages_30d: number;
  revenue_30d: number;
}

interface TenantDetail {
  id: string;
  name: string;
  slug: string;
  plan_tier: string;
  status: string;
  credit_balance: number;
  settings: Record<string, unknown>;
  stripe_customer_id: string | null;
  stripe_subscription_id: string | null;
  bandwidth_site_id: string | null;
  bandwidth_location_id: string | null;
  bandwidth_application_id: string | null;
  created_at: string;
}

interface TenantDetailResponse {
  tenant: TenantDetail;
  users: TenantUser[];
  phone_numbers: PhoneNumber[];
  stats: TenantStats;
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

const numberStatusColors: Record<string, string> = {
  active: "bg-emerald-500/20 text-emerald-400",
  inactive: "bg-gray-500/20 text-gray-400",
  pending: "bg-amber-500/20 text-amber-400",
};

const roleColors: Record<string, string> = {
  owner: "bg-purple-500/20 text-purple-400",
  admin: "bg-blue-500/20 text-blue-400",
  member: "bg-gray-500/20 text-gray-400",
};

const plans = ["free_trial", "starter", "growth", "enterprise"];
const tabs = ["Overview", "Users", "Numbers", "Billing"];

export default function AdminTenantDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [activeTab, setActiveTab] = useState(0);
  const [showPlanDropdown, setShowPlanDropdown] = useState(false);
  const [creditsAmount, setCreditsAmount] = useState("");
  const [showAddCredits, setShowAddCredits] = useState(false);

  const { data, isLoading, error } = useQuery<TenantDetailResponse>({
    queryKey: ["admin-tenant-detail", id],
    queryFn: async () => {
      const res = await api.get(`/admin/tenants/${id}`);
      return res.data;
    },
    enabled: !!id,
  });

  const suspendMutation = useMutation({
    mutationFn: async (status: string) => {
      await api.put(`/admin/tenants/${id}`, { status });
    },
    onSuccess: (_, status) => {
      toast.success(`Tenant ${status === "suspended" ? "suspended" : "activated"} successfully`);
      queryClient.invalidateQueries({ queryKey: ["admin-tenant-detail", id] });
    },
    onError: () => {
      toast.error("Failed to update tenant status");
    },
  });

  const changePlanMutation = useMutation({
    mutationFn: async (plan_tier: string) => {
      await api.put(`/admin/tenants/${id}`, { plan_tier });
    },
    onSuccess: () => {
      toast.success("Plan updated successfully");
      setShowPlanDropdown(false);
      queryClient.invalidateQueries({ queryKey: ["admin-tenant-detail", id] });
    },
    onError: () => {
      toast.error("Failed to update plan");
    },
  });

  const addCreditsMutation = useMutation({
    mutationFn: async (amount: number) => {
      await api.post(`/admin/tenants/${id}/credits`, { amount });
    },
    onSuccess: () => {
      toast.success("Credits added successfully");
      setCreditsAmount("");
      setShowAddCredits(false);
      queryClient.invalidateQueries({ queryKey: ["admin-tenant-detail", id] });
    },
    onError: () => {
      toast.error("Failed to add credits");
    },
  });

  const impersonateMutation = useMutation({
    mutationFn: async () => {
      const res = await api.post(`/admin/tenants/${id}/impersonate`);
      return res.data;
    },
    onSuccess: (data) => {
      const token = data.access_token || data.token;
      if (token) {
        window.open(`/?impersonate_token=${token}`, "_blank");
      }
      toast.success("Impersonation session started in new tab");
    },
    onError: () => {
      toast.error("Failed to impersonate tenant");
    },
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-96">
        <Loader2 className="w-8 h-8 text-blue-400 animate-spin" />
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="text-center py-20">
        <p className="text-gray-400 mb-4">Failed to load tenant details</p>
        <button
          onClick={() => navigate("/admin/tenants")}
          className="text-blue-400 hover:text-blue-300 text-sm"
        >
          Back to Tenants
        </button>
      </div>
    );
  }

  const { tenant, users, phone_numbers, stats } = data;

  return (
    <motion.div variants={container} initial="hidden" animate="show">
      {/* Back button + Header */}
      <motion.div variants={item} className="mb-8">
        <button
          onClick={() => navigate("/admin/tenants")}
          className="inline-flex items-center gap-2 text-gray-400 hover:text-white text-sm mb-4 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Tenants
        </button>

        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
          <div className="flex items-center gap-4">
            <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center shadow-lg shadow-blue-500/25">
              <Building2 className="w-7 h-7 text-white" />
            </div>
            <div>
              <h1 className="text-3xl font-bold text-white">{tenant.name}</h1>
              <div className="flex items-center gap-3 mt-1">
                <span className="text-gray-500 text-sm">{tenant.slug}</span>
                <span className={clsx("px-2 py-0.5 rounded-full text-xs font-medium", planColors[tenant.plan_tier] || planColors.free_trial)}>
                  {tenant.plan_tier.replace(/_/g, " ")}
                </span>
                <span className={clsx("px-2 py-0.5 rounded-full text-xs font-medium", statusColors[tenant.status] || statusColors.active)}>
                  {tenant.status}
                </span>
                <span className="text-gray-500 text-xs flex items-center gap-1">
                  <Clock className="w-3 h-3" />
                  {new Date(tenant.created_at).toLocaleDateString()}
                </span>
              </div>
            </div>
          </div>

          {/* Quick Actions */}
          <div className="flex flex-wrap items-center gap-2">
            {tenant.status === "active" ? (
              <button
                onClick={() => suspendMutation.mutate("suspended")}
                disabled={suspendMutation.isPending}
                className="inline-flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium text-rose-400 bg-rose-500/10 border border-rose-500/20 hover:bg-rose-500/20 transition-all disabled:opacity-50"
              >
                <Ban className="w-4 h-4" />
                Suspend
              </button>
            ) : (
              <button
                onClick={() => suspendMutation.mutate("active")}
                disabled={suspendMutation.isPending}
                className="inline-flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 hover:bg-emerald-500/20 transition-all disabled:opacity-50"
              >
                <PlayCircle className="w-4 h-4" />
                Activate
              </button>
            )}

            <div className="relative">
              <button
                onClick={() => setShowPlanDropdown(!showPlanDropdown)}
                className="inline-flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium text-blue-400 bg-blue-500/10 border border-blue-500/20 hover:bg-blue-500/20 transition-all"
              >
                <CreditCard className="w-4 h-4" />
                Change Plan
              </button>
              <AnimatePresence>
                {showPlanDropdown && (
                  <motion.div
                    initial={{ opacity: 0, y: -5 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -5 }}
                    className="absolute right-0 top-full mt-2 w-44 bg-navy-800 border border-white/10 rounded-xl shadow-xl z-20 overflow-hidden"
                  >
                    {plans.map((plan) => (
                      <button
                        key={plan}
                        onClick={() => changePlanMutation.mutate(plan)}
                        disabled={plan === tenant.plan_tier || changePlanMutation.isPending}
                        className={clsx(
                          "w-full text-left px-4 py-2.5 text-sm transition-colors",
                          plan === tenant.plan_tier
                            ? "text-gray-500 bg-white/5 cursor-not-allowed"
                            : "text-gray-300 hover:bg-white/10 hover:text-white"
                        )}
                      >
                        {plan.replace(/_/g, " ")}
                        {plan === tenant.plan_tier && " (current)"}
                      </button>
                    ))}
                  </motion.div>
                )}
              </AnimatePresence>
            </div>

            <button
              onClick={() => impersonateMutation.mutate()}
              disabled={impersonateMutation.isPending}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium text-amber-400 bg-amber-500/10 border border-amber-500/20 hover:bg-amber-500/20 transition-all disabled:opacity-50"
            >
              <UserCog className="w-4 h-4" />
              Impersonate
            </button>

            <button
              onClick={() => setShowAddCredits(!showAddCredits)}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 hover:bg-emerald-500/20 transition-all"
            >
              <Plus className="w-4 h-4" />
              Add Credits
            </button>
          </div>
        </div>

        {/* Add Credits Form */}
        <AnimatePresence>
          {showAddCredits && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              exit={{ opacity: 0, height: 0 }}
              className="mt-4 overflow-hidden"
            >
              <div className="flex items-center gap-3 p-4 bg-white/5 border border-white/10 rounded-xl">
                <span className="text-sm text-gray-400">Amount ($):</span>
                <input
                  type="number"
                  step="0.01"
                  min="0"
                  value={creditsAmount}
                  onChange={(e) => setCreditsAmount(e.target.value)}
                  placeholder="0.00"
                  className="w-32 px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-white text-sm placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-emerald-500/50"
                />
                <button
                  onClick={() => {
                    const amount = parseFloat(creditsAmount);
                    if (isNaN(amount) || amount <= 0) {
                      toast.error("Please enter a valid amount");
                      return;
                    }
                    addCreditsMutation.mutate(amount);
                  }}
                  disabled={addCreditsMutation.isPending}
                  className="px-4 py-2 rounded-lg text-sm font-medium text-white bg-emerald-600 hover:bg-emerald-500 transition-colors disabled:opacity-50"
                >
                  {addCreditsMutation.isPending ? "Adding..." : "Add Credits"}
                </button>
                <button
                  onClick={() => { setShowAddCredits(false); setCreditsAmount(""); }}
                  className="px-3 py-2 text-sm text-gray-400 hover:text-white transition-colors"
                >
                  Cancel
                </button>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>

      {/* Tabs */}
      <motion.div variants={item} className="flex gap-1 mb-6 p-1 bg-white/5 rounded-xl w-fit">
        {tabs.map((tab, i) => (
          <button
            key={tab}
            onClick={() => setActiveTab(i)}
            className={clsx(
              "px-5 py-2 rounded-lg text-sm font-medium transition-all",
              activeTab === i
                ? "bg-white/10 text-white shadow-sm"
                : "text-gray-400 hover:text-white hover:bg-white/5"
            )}
          >
            {tab}
          </button>
        ))}
      </motion.div>

      {/* Tab Content */}
      <AnimatePresence mode="wait">
        {/* Overview Tab */}
        {activeTab === 0 && (
          <motion.div
            key="overview"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.2 }}
          >
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
              <StatCard title="Users" value={stats.user_count} icon={Users} color="blue" />
              <StatCard title="Contacts" value={stats.contact_count} icon={Hash} color="emerald" />
              <StatCard title="Messages (30d)" value={stats.messages_30d} icon={MessageSquare} color="amber" />
              <StatCard title="Revenue (30d)" value={stats.revenue_30d} prefix="$" icon={DollarSign} color="rose" />
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Credit Balance */}
              <GlassCard>
                <h3 className="text-sm font-semibold text-white mb-4">Credit Balance</h3>
                <div className="flex items-baseline gap-2 mb-4">
                  <span className="text-4xl font-bold text-emerald-400 font-mono">
                    ${tenant.credit_balance.toFixed(2)}
                  </span>
                  <span className="text-sm text-gray-500">available</span>
                </div>
                <div className="h-2 bg-white/5 rounded-full overflow-hidden">
                  <motion.div
                    initial={{ width: 0 }}
                    animate={{ width: `${Math.min(100, (tenant.credit_balance / 1000) * 100)}%` }}
                    transition={{ duration: 0.8 }}
                    className="h-full bg-gradient-to-r from-emerald-500 to-teal-600 rounded-full"
                  />
                </div>
              </GlassCard>

              {/* Tenant Settings */}
              <GlassCard>
                <h3 className="text-sm font-semibold text-white mb-4">Tenant Settings</h3>
                <div className="max-h-64 overflow-y-auto">
                  {Object.keys(tenant.settings || {}).length > 0 ? (
                    <pre className="text-xs text-gray-400 font-mono whitespace-pre-wrap break-all">
                      {JSON.stringify(tenant.settings, null, 2)}
                    </pre>
                  ) : (
                    <p className="text-gray-500 text-sm">No custom settings configured</p>
                  )}
                </div>
              </GlassCard>
            </div>
          </motion.div>
        )}

        {/* Users Tab */}
        {activeTab === 1 && (
          <motion.div
            key="users"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.2 }}
          >
            <GlassCard className="p-0 overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="bg-white/5">
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Name</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Email</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Role</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Active</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">MFA</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Last Login</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Created</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/5">
                    {users.length === 0 ? (
                      <tr>
                        <td colSpan={7} className="px-4 py-8 text-center text-gray-500 text-sm">
                          No users found
                        </td>
                      </tr>
                    ) : (
                      users.map((user, i) => (
                        <motion.tr
                          key={user.id}
                          initial={{ opacity: 0, y: 10 }}
                          animate={{ opacity: 1, y: 0 }}
                          transition={{ delay: i * 0.03 }}
                          className="hover:bg-white/5 transition-colors"
                        >
                          <td className="px-4 py-3 text-sm text-white font-medium">{user.full_name}</td>
                          <td className="px-4 py-3 text-sm text-gray-300 flex items-center gap-1.5">
                            <Mail className="w-3.5 h-3.5 text-gray-500" />
                            {user.email}
                          </td>
                          <td className="px-4 py-3">
                            <span className={clsx("px-2 py-0.5 rounded-full text-xs font-medium", roleColors[user.role] || roleColors.member)}>
                              {user.role}
                            </span>
                          </td>
                          <td className="px-4 py-3">
                            <span className={clsx("w-2.5 h-2.5 rounded-full inline-block", user.is_active ? "bg-emerald-400" : "bg-rose-400")} />
                          </td>
                          <td className="px-4 py-3">
                            <span className={clsx(
                              "px-2 py-0.5 rounded-full text-xs font-medium",
                              user.mfa_enabled ? "bg-emerald-500/20 text-emerald-400" : "bg-white/5 text-gray-500"
                            )}>
                              {user.mfa_enabled ? "Enabled" : "Off"}
                            </span>
                          </td>
                          <td className="px-4 py-3 text-sm text-gray-500">
                            {user.last_login_at ? new Date(user.last_login_at).toLocaleString() : "Never"}
                          </td>
                          <td className="px-4 py-3 text-sm text-gray-500">
                            {new Date(user.created_at).toLocaleDateString()}
                          </td>
                        </motion.tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </GlassCard>
          </motion.div>
        )}

        {/* Numbers Tab */}
        {activeTab === 2 && (
          <motion.div
            key="numbers"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.2 }}
          >
            <GlassCard className="p-0 overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="bg-white/5">
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Number</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Type</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Status</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Monthly Cost</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/5">
                    {phone_numbers.length === 0 ? (
                      <tr>
                        <td colSpan={4} className="px-4 py-8 text-center text-gray-500 text-sm">
                          No phone numbers assigned
                        </td>
                      </tr>
                    ) : (
                      phone_numbers.map((num, i) => (
                        <motion.tr
                          key={num.id}
                          initial={{ opacity: 0, y: 10 }}
                          animate={{ opacity: 1, y: 0 }}
                          transition={{ delay: i * 0.03 }}
                          className="hover:bg-white/5 transition-colors"
                        >
                          <td className="px-4 py-3 text-sm text-white font-mono flex items-center gap-2">
                            <Phone className="w-4 h-4 text-blue-400" />
                            {num.phone_number}
                          </td>
                          <td className="px-4 py-3 text-sm text-gray-300 capitalize">{num.number_type}</td>
                          <td className="px-4 py-3">
                            <span className={clsx("px-2 py-0.5 rounded-full text-xs font-medium", numberStatusColors[num.status] || numberStatusColors.active)}>
                              {num.status}
                            </span>
                          </td>
                          <td className="px-4 py-3 text-sm text-gray-300 font-mono">${num.monthly_cost.toFixed(2)}</td>
                        </motion.tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </GlassCard>
          </motion.div>
        )}

        {/* Billing Tab */}
        {activeTab === 3 && (
          <motion.div
            key="billing"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.2 }}
            className="grid grid-cols-1 lg:grid-cols-2 gap-6"
          >
            {/* Current Plan */}
            <GlassCard>
              <h3 className="text-sm font-semibold text-white mb-4">Current Plan</h3>
              <div className="flex items-center gap-4 mb-4">
                <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center">
                  <CreditCard className="w-8 h-8 text-white" />
                </div>
                <div>
                  <p className="text-2xl font-bold text-white capitalize">{tenant.plan_tier.replace(/_/g, " ")}</p>
                  <span className={clsx("px-2 py-0.5 rounded-full text-xs font-medium", statusColors[tenant.status] || statusColors.active)}>
                    {tenant.status}
                  </span>
                </div>
              </div>
              <div className="bg-white/5 rounded-xl p-4">
                <div className="flex items-baseline gap-2">
                  <span className="text-3xl font-bold text-white font-mono">${tenant.credit_balance.toFixed(2)}</span>
                  <span className="text-sm text-gray-500">credit balance</span>
                </div>
              </div>
            </GlassCard>

            {/* Integration IDs */}
            <GlassCard>
              <h3 className="text-sm font-semibold text-white mb-4">Integration IDs</h3>
              <div className="space-y-3">
                <div className="flex items-center justify-between p-3 bg-white/5 rounded-xl">
                  <div className="flex items-center gap-2">
                    <Shield className="w-4 h-4 text-purple-400" />
                    <span className="text-sm text-gray-400">Stripe Customer</span>
                  </div>
                  <span className="text-sm text-white font-mono">
                    {tenant.stripe_customer_id ? (
                      <a
                        href={`https://dashboard.stripe.com/customers/${tenant.stripe_customer_id}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1 text-blue-400 hover:text-blue-300"
                      >
                        {tenant.stripe_customer_id}
                        <ExternalLink className="w-3 h-3" />
                      </a>
                    ) : (
                      <span className="text-gray-600">Not set</span>
                    )}
                  </span>
                </div>
                <div className="flex items-center justify-between p-3 bg-white/5 rounded-xl">
                  <div className="flex items-center gap-2">
                    <Shield className="w-4 h-4 text-purple-400" />
                    <span className="text-sm text-gray-400">Stripe Subscription</span>
                  </div>
                  <span className="text-sm text-white font-mono">
                    {tenant.stripe_subscription_id || <span className="text-gray-600">Not set</span>}
                  </span>
                </div>
                <div className="flex items-center justify-between p-3 bg-white/5 rounded-xl">
                  <div className="flex items-center gap-2">
                    <Phone className="w-4 h-4 text-emerald-400" />
                    <span className="text-sm text-gray-400">BW Site ID</span>
                  </div>
                  <span className="text-sm text-white font-mono">
                    {tenant.bandwidth_site_id || <span className="text-gray-600">Not set</span>}
                  </span>
                </div>
                <div className="flex items-center justify-between p-3 bg-white/5 rounded-xl">
                  <div className="flex items-center gap-2">
                    <Phone className="w-4 h-4 text-emerald-400" />
                    <span className="text-sm text-gray-400">BW Location ID</span>
                  </div>
                  <span className="text-sm text-white font-mono">
                    {tenant.bandwidth_location_id || <span className="text-gray-600">Not set</span>}
                  </span>
                </div>
                <div className="flex items-center justify-between p-3 bg-white/5 rounded-xl">
                  <div className="flex items-center gap-2">
                    <Phone className="w-4 h-4 text-emerald-400" />
                    <span className="text-sm text-gray-400">BW Application ID</span>
                  </div>
                  <span className="text-sm text-white font-mono">
                    {tenant.bandwidth_application_id || <span className="text-gray-600">Not set</span>}
                  </span>
                </div>
              </div>
            </GlassCard>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
