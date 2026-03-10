import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Settings as SettingsIcon,
  Users,
  Key,
  Webhook,
  Globe,
  Clock,
  Phone,
  Moon,
  Plus,
  X,
  Copy,
  Eye,
  EyeOff,
  Trash2,
  Send,
  Check,
  Loader2,
  Shield,
  Mail,
} from "lucide-react";
import clsx from "clsx";
import GlassCard from "../components/ui/GlassCard";
import toast from "react-hot-toast";

const container = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { staggerChildren: 0.08 } },
};

const item = {
  hidden: { opacity: 0, y: 20 },
  show: { opacity: 1, y: 0 },
};

type SettingsTab = "general" | "team" | "api-keys" | "webhooks";

const tabs: { key: SettingsTab; label: string; icon: typeof SettingsIcon }[] = [
  { key: "general", label: "General", icon: SettingsIcon },
  { key: "team", label: "Team", icon: Users },
  { key: "api-keys", label: "API Keys", icon: Key },
  { key: "webhooks", label: "Webhooks", icon: Webhook },
];

interface TeamMember {
  id: string;
  name: string;
  email: string;
  role: "owner" | "admin" | "member" | "viewer";
  lastActive: string;
}

interface ApiKey {
  id: string;
  name: string;
  key: string;
  created: string;
  lastUsed: string;
}

interface WebhookConfig {
  id: string;
  url: string;
  events: string[];
  active: boolean;
  lastTriggered: string;
}

const teamMembers: TeamMember[] = [
  { id: "1", name: "Katie Johnson", email: "katie@blastwave.io", role: "owner", lastActive: "Just now" },
  { id: "2", name: "Alex Chen", email: "alex@blastwave.io", role: "admin", lastActive: "5 min ago" },
  { id: "3", name: "Sarah Kim", email: "sarah@blastwave.io", role: "member", lastActive: "2 hours ago" },
  { id: "4", name: "Mike Torres", email: "mike@blastwave.io", role: "viewer", lastActive: "1 day ago" },
];

const initialApiKeys: ApiKey[] = [
  { id: "1", name: "Production", key: "bw_live_sk_a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6", created: "2026-01-15", lastUsed: "2 min ago" },
  { id: "2", name: "Staging", key: "bw_test_sk_z9y8x7w6v5u4t3s2r1q0p9o8n7m6l5k4", created: "2026-02-20", lastUsed: "3 days ago" },
];

const initialWebhooks: WebhookConfig[] = [
  {
    id: "1",
    url: "https://api.example.com/webhooks/sms",
    events: ["message.sent", "message.delivered", "message.failed"],
    active: true,
    lastTriggered: "1 min ago",
  },
  {
    id: "2",
    url: "https://api.example.com/webhooks/contacts",
    events: ["contact.created", "contact.opted_out"],
    active: true,
    lastTriggered: "1 hour ago",
  },
];

const allEventTypes = [
  "message.sent",
  "message.delivered",
  "message.failed",
  "message.received",
  "contact.created",
  "contact.updated",
  "contact.opted_out",
  "campaign.completed",
  "campaign.failed",
];

const roleBadge: Record<string, { bg: string; text: string }> = {
  owner: { bg: "bg-amber-500/20", text: "text-amber-400" },
  admin: { bg: "bg-blue-500/20", text: "text-blue-400" },
  member: { bg: "bg-emerald-500/20", text: "text-emerald-400" },
  viewer: { bg: "bg-gray-500/20", text: "text-gray-400" },
};

const timezones = [
  "America/New_York",
  "America/Chicago",
  "America/Denver",
  "America/Los_Angeles",
  "America/Phoenix",
  "Pacific/Honolulu",
  "UTC",
];

const inputClass =
  "w-full px-4 py-3 bg-white/5 border border-white/10 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50 transition-all";
const labelClass = "block text-sm font-medium text-gray-300 mb-1.5";

export default function Settings() {
  const [activeTab, setActiveTab] = useState<SettingsTab>("general");
  const [saving, setSaving] = useState(false);

  // General settings
  const [general, setGeneral] = useState({
    companyName: "BlastWave Technologies",
    timezone: "America/New_York",
    defaultFromNumber: "+1 (555) 100-0001",
    quietHoursEnabled: true,
    quietStart: "21:00",
    quietEnd: "08:00",
  });

  // Team
  const [showInvite, setShowInvite] = useState(false);
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState("member");

  // API Keys
  const [apiKeys, setApiKeys] = useState(initialApiKeys);
  const [showCreateKey, setShowCreateKey] = useState(false);
  const [newKeyName, setNewKeyName] = useState("");
  const [revealedKeys, setRevealedKeys] = useState<Set<string>>(new Set());

  // Webhooks
  const [webhooks, setWebhooks] = useState(initialWebhooks);
  const [showAddWebhook, setShowAddWebhook] = useState(false);
  const [newWebhook, setNewWebhook] = useState({ url: "", events: [] as string[] });
  const [testingWebhook, setTestingWebhook] = useState<string | null>(null);

  const handleSaveGeneral = async () => {
    setSaving(true);
    await new Promise((r) => setTimeout(r, 1000));
    setSaving(false);
    toast.success("Settings saved!");
  };

  const handleInvite = () => {
    if (!inviteEmail.trim()) {
      toast.error("Email is required");
      return;
    }
    toast.success(`Invitation sent to ${inviteEmail}`);
    setShowInvite(false);
    setInviteEmail("");
  };

  const createApiKey = () => {
    if (!newKeyName.trim()) {
      toast.error("Key name is required");
      return;
    }
    const key: ApiKey = {
      id: String(Date.now()),
      name: newKeyName,
      key: `bw_live_sk_${Array.from({ length: 32 }, () => "abcdefghijklmnopqrstuvwxyz0123456789"[Math.floor(Math.random() * 36)]).join("")}`,
      created: "Just now",
      lastUsed: "Never",
    };
    setApiKeys((prev) => [key, ...prev]);
    setRevealedKeys((prev) => new Set(prev).add(key.id));
    setShowCreateKey(false);
    setNewKeyName("");
    toast.success("API key created! Make sure to copy it now.");
  };

  const deleteApiKey = (id: string) => {
    setApiKeys((prev) => prev.filter((k) => k.id !== id));
    toast.success("API key deleted");
  };

  const maskKey = (key: string) => key.slice(0, 12) + "..." + key.slice(-4);

  const toggleKeyReveal = (id: string) => {
    setRevealedKeys((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  };

  const copyKey = (key: string) => {
    navigator.clipboard.writeText(key);
    toast.success("Copied to clipboard!");
  };

  const addWebhook = () => {
    if (!newWebhook.url.trim() || newWebhook.events.length === 0) {
      toast.error("URL and at least one event type required");
      return;
    }
    setWebhooks((prev) => [
      { id: String(Date.now()), ...newWebhook, active: true, lastTriggered: "Never" },
      ...prev,
    ]);
    setShowAddWebhook(false);
    setNewWebhook({ url: "", events: [] });
    toast.success("Webhook added!");
  };

  const toggleWebhookEvent = (event: string) => {
    setNewWebhook((p) => ({
      ...p,
      events: p.events.includes(event) ? p.events.filter((e) => e !== event) : [...p.events, event],
    }));
  };

  const testWebhook = async (id: string) => {
    setTestingWebhook(id);
    await new Promise((r) => setTimeout(r, 2000));
    setTestingWebhook(null);
    toast.success("Test event sent!");
  };

  const deleteWebhook = (id: string) => {
    setWebhooks((prev) => prev.filter((w) => w.id !== id));
    toast.success("Webhook deleted");
  };

  return (
    <motion.div variants={container} initial="hidden" animate="show">
      {/* Header */}
      <motion.div variants={item} className="mb-8">
        <h1 className="text-3xl font-bold text-white">Settings</h1>
        <p className="text-gray-400 mt-1">Manage your account, team, and integrations.</p>
      </motion.div>

      {/* Tab Navigation */}
      <motion.div variants={item} className="mb-8">
        <div className="flex gap-1 bg-white/5 rounded-xl p-1 border border-white/10 w-fit">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.key;
            return (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key)}
                className={clsx(
                  "relative flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-medium transition-colors",
                  isActive ? "text-white" : "text-gray-400 hover:text-gray-200"
                )}
              >
                {isActive && (
                  <motion.div
                    layoutId="settings-tab"
                    className="absolute inset-0 bg-white/10 rounded-lg"
                    transition={{ type: "spring", stiffness: 400, damping: 30 }}
                  />
                )}
                <span className="relative flex items-center gap-2">
                  <Icon className="w-4 h-4" />
                  {tab.label}
                </span>
              </button>
            );
          })}
        </div>
      </motion.div>

      {/* General */}
      {activeTab === "general" && (
        <motion.div variants={item}>
          <GlassCard>
            <h3 className="text-lg font-semibold text-white mb-6">General Settings</h3>
            <div className="space-y-6 max-w-2xl">
              <div>
                <label className={labelClass}>Company Name</label>
                <div className="relative">
                  <Globe className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-500" />
                  <input
                    value={general.companyName}
                    onChange={(e) => setGeneral((g) => ({ ...g, companyName: e.target.value }))}
                    className={clsx(inputClass, "pl-11")}
                  />
                </div>
              </div>
              <div>
                <label className={labelClass}>Timezone</label>
                <div className="relative">
                  <Clock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-500" />
                  <select
                    value={general.timezone}
                    onChange={(e) => setGeneral((g) => ({ ...g, timezone: e.target.value }))}
                    className={clsx(inputClass, "pl-11")}
                  >
                    {timezones.map((tz) => (
                      <option key={tz} value={tz} className="bg-navy-900">{tz}</option>
                    ))}
                  </select>
                </div>
              </div>
              <div>
                <label className={labelClass}>Default From Number</label>
                <div className="relative">
                  <Phone className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-500" />
                  <input
                    value={general.defaultFromNumber}
                    onChange={(e) => setGeneral((g) => ({ ...g, defaultFromNumber: e.target.value }))}
                    className={clsx(inputClass, "pl-11")}
                  />
                </div>
              </div>
              <div className="border-t border-white/10 pt-6">
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-3">
                    <Moon className="w-5 h-5 text-indigo-400" />
                    <div>
                      <p className="text-sm font-medium text-white">Quiet Hours</p>
                      <p className="text-xs text-gray-400">Pause outbound messages during set hours</p>
                    </div>
                  </div>
                  <button
                    onClick={() => setGeneral((g) => ({ ...g, quietHoursEnabled: !g.quietHoursEnabled }))}
                    className={clsx(
                      "w-12 h-6 rounded-full transition-colors relative",
                      general.quietHoursEnabled ? "bg-blue-500" : "bg-white/10"
                    )}
                  >
                    <motion.div
                      animate={{ x: general.quietHoursEnabled ? 24 : 2 }}
                      className="w-5 h-5 bg-white rounded-full absolute top-0.5"
                    />
                  </button>
                </div>
                {general.quietHoursEnabled && (
                  <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: "auto" }}
                    className="grid grid-cols-2 gap-4 ml-8"
                  >
                    <div>
                      <label className={labelClass}>Start Time</label>
                      <input
                        type="time"
                        value={general.quietStart}
                        onChange={(e) => setGeneral((g) => ({ ...g, quietStart: e.target.value }))}
                        className={inputClass}
                      />
                    </div>
                    <div>
                      <label className={labelClass}>End Time</label>
                      <input
                        type="time"
                        value={general.quietEnd}
                        onChange={(e) => setGeneral((g) => ({ ...g, quietEnd: e.target.value }))}
                        className={inputClass}
                      />
                    </div>
                  </motion.div>
                )}
              </div>
              <div className="pt-4">
                <motion.button
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  onClick={handleSaveGeneral}
                  disabled={saving}
                  className="inline-flex items-center gap-2 px-6 py-2.5 rounded-xl font-semibold text-sm text-white bg-gradient-to-r from-blue-500 to-indigo-600 shadow-lg shadow-blue-500/25 disabled:opacity-60 transition-all"
                >
                  {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Check className="w-4 h-4" />}
                  {saving ? "Saving..." : "Save Changes"}
                </motion.button>
              </div>
            </div>
          </GlassCard>
        </motion.div>
      )}

      {/* Team */}
      {activeTab === "team" && (
        <motion.div variants={item} className="space-y-6">
          <GlassCard>
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-lg font-semibold text-white">Team Members</h3>
              <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={() => setShowInvite(true)}
                className="inline-flex items-center gap-2 px-4 py-2 rounded-xl font-semibold text-sm text-white bg-gradient-to-r from-blue-500 to-indigo-600 shadow-lg shadow-blue-500/25 transition-all"
              >
                <Plus className="w-4 h-4" />
                Invite User
              </motion.button>
            </div>
            <div className="space-y-3">
              {teamMembers.map((member) => {
                const badge = roleBadge[member.role];
                return (
                  <motion.div
                    key={member.id}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="flex items-center justify-between p-4 bg-white/5 rounded-xl hover:bg-white/8 transition-colors"
                  >
                    <div className="flex items-center gap-4">
                      <div className="w-10 h-10 rounded-full bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center text-white font-bold text-sm">
                        {member.name.split(" ").map((n) => n[0]).join("")}
                      </div>
                      <div>
                        <p className="text-sm font-medium text-white">{member.name}</p>
                        <p className="text-xs text-gray-500">{member.email}</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-4">
                      <span className={clsx("px-2.5 py-1 rounded-full text-xs font-medium", badge.bg, badge.text)}>
                        {member.role.charAt(0).toUpperCase() + member.role.slice(1)}
                      </span>
                      <span className="text-xs text-gray-500">{member.lastActive}</span>
                    </div>
                  </motion.div>
                );
              })}
            </div>
          </GlassCard>

          {/* Invite Modal */}
          <AnimatePresence>
            {showInvite && (
              <>
                <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={() => setShowInvite(false)} className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50" />
                <motion.div initial={{ opacity: 0, scale: 0.95, y: 20 }} animate={{ opacity: 1, scale: 1, y: 0 }} exit={{ opacity: 0, scale: 0.95, y: 20 }} className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-full max-w-md z-50">
                  <div className="bg-navy-900/95 backdrop-blur-xl border border-white/10 rounded-2xl shadow-2xl p-6">
                    <div className="flex items-center justify-between mb-6">
                      <h3 className="text-lg font-semibold text-white">Invite Team Member</h3>
                      <button onClick={() => setShowInvite(false)} className="text-gray-500 hover:text-white"><X className="w-5 h-5" /></button>
                    </div>
                    <div className="space-y-4">
                      <div>
                        <label className={labelClass}>Email Address</label>
                        <div className="relative">
                          <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-500" />
                          <input value={inviteEmail} onChange={(e) => setInviteEmail(e.target.value)} placeholder="colleague@company.com" className={clsx(inputClass, "pl-11")} />
                        </div>
                      </div>
                      <div>
                        <label className={labelClass}>Role</label>
                        <select value={inviteRole} onChange={(e) => setInviteRole(e.target.value)} className={inputClass}>
                          <option value="admin" className="bg-navy-900">Admin</option>
                          <option value="member" className="bg-navy-900">Member</option>
                          <option value="viewer" className="bg-navy-900">Viewer</option>
                        </select>
                      </div>
                    </div>
                    <div className="flex justify-end gap-3 mt-6">
                      <button onClick={() => setShowInvite(false)} className="px-4 py-2.5 rounded-xl text-sm text-gray-400 hover:text-white bg-white/5 hover:bg-white/10 border border-white/10 transition-all">Cancel</button>
                      <motion.button whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }} onClick={handleInvite} className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl font-semibold text-sm text-white bg-gradient-to-r from-blue-500 to-indigo-600 shadow-lg shadow-blue-500/25 transition-all">
                        <Send className="w-4 h-4" />
                        Send Invite
                      </motion.button>
                    </div>
                  </div>
                </motion.div>
              </>
            )}
          </AnimatePresence>
        </motion.div>
      )}

      {/* API Keys */}
      {activeTab === "api-keys" && (
        <motion.div variants={item}>
          <GlassCard>
            <div className="flex items-center justify-between mb-6">
              <div>
                <h3 className="text-lg font-semibold text-white">API Keys</h3>
                <p className="text-sm text-gray-400 mt-1">Manage your API keys for programmatic access.</p>
              </div>
              <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={() => setShowCreateKey(true)}
                className="inline-flex items-center gap-2 px-4 py-2 rounded-xl font-semibold text-sm text-white bg-gradient-to-r from-blue-500 to-indigo-600 shadow-lg shadow-blue-500/25 transition-all"
              >
                <Plus className="w-4 h-4" />
                Create Key
              </motion.button>
            </div>
            <div className="space-y-3">
              {apiKeys.map((apiKey) => {
                const isRevealed = revealedKeys.has(apiKey.id);
                return (
                  <motion.div
                    key={apiKey.id}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="p-4 bg-white/5 rounded-xl"
                  >
                    <div className="flex items-center justify-between mb-3">
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-lg bg-amber-500/20 flex items-center justify-center">
                          <Key className="w-4 h-4 text-amber-400" />
                        </div>
                        <div>
                          <p className="text-sm font-medium text-white">{apiKey.name}</p>
                          <p className="text-xs text-gray-500">Created {apiKey.created}</p>
                        </div>
                      </div>
                      <span className="text-xs text-gray-500">Last used: {apiKey.lastUsed}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <code className="flex-1 px-3 py-2 bg-black/30 rounded-lg text-sm font-mono text-gray-300 overflow-hidden">
                        {isRevealed ? apiKey.key : maskKey(apiKey.key)}
                      </code>
                      <button
                        onClick={() => toggleKeyReveal(apiKey.id)}
                        className="p-2 rounded-lg text-gray-500 hover:text-white hover:bg-white/10 transition-all"
                      >
                        {isRevealed ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                      </button>
                      <button
                        onClick={() => copyKey(apiKey.key)}
                        className="p-2 rounded-lg text-gray-500 hover:text-blue-400 hover:bg-blue-500/10 transition-all"
                      >
                        <Copy className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => deleteApiKey(apiKey.id)}
                        className="p-2 rounded-lg text-gray-500 hover:text-rose-400 hover:bg-rose-500/10 transition-all"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </motion.div>
                );
              })}
            </div>
          </GlassCard>

          {/* Create Key Modal */}
          <AnimatePresence>
            {showCreateKey && (
              <>
                <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={() => setShowCreateKey(false)} className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50" />
                <motion.div initial={{ opacity: 0, scale: 0.95, y: 20 }} animate={{ opacity: 1, scale: 1, y: 0 }} exit={{ opacity: 0, scale: 0.95, y: 20 }} className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-full max-w-md z-50">
                  <div className="bg-navy-900/95 backdrop-blur-xl border border-white/10 rounded-2xl shadow-2xl p-6">
                    <div className="flex items-center justify-between mb-6">
                      <h3 className="text-lg font-semibold text-white">Create API Key</h3>
                      <button onClick={() => setShowCreateKey(false)} className="text-gray-500 hover:text-white"><X className="w-5 h-5" /></button>
                    </div>
                    <div>
                      <label className={labelClass}>Key Name</label>
                      <input
                        value={newKeyName}
                        onChange={(e) => setNewKeyName(e.target.value)}
                        placeholder="e.g. Production, Staging"
                        className={inputClass}
                      />
                    </div>
                    <div className="mt-4 p-3 bg-amber-500/10 border border-amber-500/20 rounded-xl">
                      <div className="flex gap-2">
                        <Shield className="w-4 h-4 text-amber-400 flex-shrink-0 mt-0.5" />
                        <p className="text-xs text-amber-300">Your API key will only be shown once. Make sure to copy and store it securely.</p>
                      </div>
                    </div>
                    <div className="flex justify-end gap-3 mt-6">
                      <button onClick={() => setShowCreateKey(false)} className="px-4 py-2.5 rounded-xl text-sm text-gray-400 hover:text-white bg-white/5 hover:bg-white/10 border border-white/10 transition-all">Cancel</button>
                      <motion.button whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }} onClick={createApiKey} className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl font-semibold text-sm text-white bg-gradient-to-r from-blue-500 to-indigo-600 shadow-lg shadow-blue-500/25 transition-all">
                        <Key className="w-4 h-4" />
                        Create Key
                      </motion.button>
                    </div>
                  </div>
                </motion.div>
              </>
            )}
          </AnimatePresence>
        </motion.div>
      )}

      {/* Webhooks */}
      {activeTab === "webhooks" && (
        <motion.div variants={item}>
          <GlassCard>
            <div className="flex items-center justify-between mb-6">
              <div>
                <h3 className="text-lg font-semibold text-white">Webhooks</h3>
                <p className="text-sm text-gray-400 mt-1">Receive real-time event notifications.</p>
              </div>
              <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={() => setShowAddWebhook(true)}
                className="inline-flex items-center gap-2 px-4 py-2 rounded-xl font-semibold text-sm text-white bg-gradient-to-r from-blue-500 to-indigo-600 shadow-lg shadow-blue-500/25 transition-all"
              >
                <Plus className="w-4 h-4" />
                Add Webhook
              </motion.button>
            </div>
            <div className="space-y-4">
              {webhooks.map((webhook) => (
                <motion.div
                  key={webhook.id}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="p-4 bg-white/5 rounded-xl"
                >
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-3">
                      <div className={clsx("w-2 h-2 rounded-full", webhook.active ? "bg-emerald-400 animate-pulse" : "bg-gray-600")} />
                      <code className="text-sm font-mono text-white">{webhook.url}</code>
                    </div>
                    <span className="text-xs text-gray-500">Last triggered: {webhook.lastTriggered}</span>
                  </div>
                  <div className="flex flex-wrap gap-1.5 mb-3">
                    {webhook.events.map((event) => (
                      <span key={event} className="px-2 py-0.5 rounded-md text-xs bg-blue-500/10 text-blue-400 border border-blue-500/20">
                        {event}
                      </span>
                    ))}
                  </div>
                  <div className="flex gap-2">
                    <motion.button
                      whileHover={{ scale: 1.02 }}
                      whileTap={{ scale: 0.98 }}
                      onClick={() => testWebhook(webhook.id)}
                      disabled={testingWebhook === webhook.id}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-blue-400 bg-blue-500/10 hover:bg-blue-500/20 border border-blue-500/20 transition-all disabled:opacity-60"
                    >
                      {testingWebhook === webhook.id ? <Loader2 className="w-3 h-3 animate-spin" /> : <Send className="w-3 h-3" />}
                      {testingWebhook === webhook.id ? "Sending..." : "Send Test"}
                    </motion.button>
                    <button
                      onClick={() => deleteWebhook(webhook.id)}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-rose-400 bg-rose-500/10 hover:bg-rose-500/20 border border-rose-500/20 transition-all"
                    >
                      <Trash2 className="w-3 h-3" />
                      Delete
                    </button>
                  </div>
                </motion.div>
              ))}
            </div>
          </GlassCard>

          {/* Add Webhook Modal */}
          <AnimatePresence>
            {showAddWebhook && (
              <>
                <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={() => setShowAddWebhook(false)} className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50" />
                <motion.div initial={{ opacity: 0, scale: 0.95, y: 20 }} animate={{ opacity: 1, scale: 1, y: 0 }} exit={{ opacity: 0, scale: 0.95, y: 20 }} className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-full max-w-md z-50">
                  <div className="bg-navy-900/95 backdrop-blur-xl border border-white/10 rounded-2xl shadow-2xl p-6">
                    <div className="flex items-center justify-between mb-6">
                      <h3 className="text-lg font-semibold text-white">Add Webhook</h3>
                      <button onClick={() => setShowAddWebhook(false)} className="text-gray-500 hover:text-white"><X className="w-5 h-5" /></button>
                    </div>
                    <div className="space-y-4">
                      <div>
                        <label className={labelClass}>Webhook URL</label>
                        <input
                          value={newWebhook.url}
                          onChange={(e) => setNewWebhook((p) => ({ ...p, url: e.target.value }))}
                          placeholder="https://api.example.com/webhooks"
                          className={inputClass}
                        />
                      </div>
                      <div>
                        <label className={labelClass}>Event Types</label>
                        <div className="grid grid-cols-1 gap-2 max-h-48 overflow-y-auto">
                          {allEventTypes.map((event) => (
                            <label
                              key={event}
                              className={clsx(
                                "flex items-center gap-3 p-2.5 rounded-lg cursor-pointer transition-colors",
                                newWebhook.events.includes(event) ? "bg-blue-500/10 border border-blue-500/20" : "bg-white/5 border border-transparent hover:bg-white/8"
                              )}
                            >
                              <input
                                type="checkbox"
                                checked={newWebhook.events.includes(event)}
                                onChange={() => toggleWebhookEvent(event)}
                                className="rounded"
                              />
                              <span className="text-sm text-gray-300 font-mono">{event}</span>
                            </label>
                          ))}
                        </div>
                      </div>
                    </div>
                    <div className="flex justify-end gap-3 mt-6">
                      <button onClick={() => setShowAddWebhook(false)} className="px-4 py-2.5 rounded-xl text-sm text-gray-400 hover:text-white bg-white/5 hover:bg-white/10 border border-white/10 transition-all">Cancel</button>
                      <motion.button whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }} onClick={addWebhook} className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl font-semibold text-sm text-white bg-gradient-to-r from-blue-500 to-indigo-600 shadow-lg shadow-blue-500/25 transition-all">
                        <Webhook className="w-4 h-4" />
                        Add Webhook
                      </motion.button>
                    </div>
                  </div>
                </motion.div>
              </>
            )}
          </AnimatePresence>
        </motion.div>
      )}
    </motion.div>
  );
}
