import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useNavigate } from "react-router-dom";
import {
  Bot,
  Plus,
  MessageSquare,
  Clock,
  ToggleLeft,
  ToggleRight,
  Sparkles,
  Zap,
  X,
  Loader2,
} from "lucide-react";
import clsx from "clsx";
import GlassCard from "../components/ui/GlassCard";
import toast from "react-hot-toast";

const container = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { staggerChildren: 0.1 } },
};

const item = {
  hidden: { opacity: 0, y: 20 },
  show: { opacity: 1, y: 0 },
};

interface Agent {
  id: string;
  name: string;
  model: string;
  active: boolean;
  conversationCount: number;
  avgResponseTime: number;
  description: string;
  lastActive: string;
}

const initialAgents: Agent[] = [
  {
    id: "1",
    name: "Support Assistant",
    model: "GPT-4o",
    active: true,
    conversationCount: 2847,
    avgResponseTime: 1.2,
    description: "Handles customer support inquiries, returns, and order tracking.",
    lastActive: "2 min ago",
  },
  {
    id: "2",
    name: "Sales Qualifier",
    model: "Claude 3.5 Sonnet",
    active: true,
    conversationCount: 1563,
    avgResponseTime: 0.8,
    description: "Qualifies inbound leads and schedules demos with sales team.",
    lastActive: "5 min ago",
  },
  {
    id: "3",
    name: "Appointment Booker",
    model: "GPT-4o Mini",
    active: false,
    conversationCount: 891,
    avgResponseTime: 1.5,
    description: "Books and manages appointments via SMS conversation.",
    lastActive: "3 hours ago",
  },
  {
    id: "4",
    name: "FAQ Bot",
    model: "Claude 3 Haiku",
    active: true,
    conversationCount: 4210,
    avgResponseTime: 0.5,
    description: "Answers frequently asked questions from knowledge base.",
    lastActive: "Just now",
  },
  {
    id: "5",
    name: "Feedback Collector",
    model: "GPT-4o Mini",
    active: false,
    conversationCount: 342,
    avgResponseTime: 2.1,
    description: "Collects NPS scores and customer feedback after interactions.",
    lastActive: "1 day ago",
  },
];

const modelOptions = ["GPT-4o", "GPT-4o Mini", "Claude 3.5 Sonnet", "Claude 3 Haiku"];

const inputClass =
  "w-full px-4 py-3 bg-white/5 border border-white/10 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50 transition-all";

export default function AIAgents() {
  const navigate = useNavigate();
  const [agents, setAgents] = useState<Agent[]>(initialAgents);
  const [showCreate, setShowCreate] = useState(false);
  const [newAgent, setNewAgent] = useState({ name: "", model: "GPT-4o", description: "" });
  const [creating, setCreating] = useState(false);

  const toggleAgent = (id: string) => {
    setAgents((prev) =>
      prev.map((a) => (a.id === id ? { ...a, active: !a.active } : a))
    );
    const agent = agents.find((a) => a.id === id);
    if (agent) {
      toast.success(`${agent.name} ${agent.active ? "deactivated" : "activated"}`);
    }
  };

  const handleCreate = async () => {
    if (!newAgent.name.trim()) {
      toast.error("Agent name is required");
      return;
    }
    setCreating(true);
    await new Promise((r) => setTimeout(r, 1000));
    const created: Agent = {
      id: String(Date.now()),
      name: newAgent.name,
      model: newAgent.model,
      active: false,
      conversationCount: 0,
      avgResponseTime: 0,
      description: newAgent.description,
      lastActive: "Never",
    };
    setAgents((prev) => [created, ...prev]);
    setShowCreate(false);
    setNewAgent({ name: "", model: "GPT-4o", description: "" });
    setCreating(false);
    toast.success("Agent created successfully!");
  };

  return (
    <motion.div variants={container} initial="hidden" animate="show">
      {/* Header */}
      <motion.div variants={item} className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-8">
        <div>
          <h1 className="text-3xl font-bold text-white">AI Agents</h1>
          <p className="text-gray-400 mt-1">Manage your intelligent SMS conversational agents.</p>
        </div>
        <motion.button
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          onClick={() => setShowCreate(true)}
          className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl font-semibold text-sm text-white bg-gradient-to-r from-blue-500 to-indigo-600 hover:from-blue-600 hover:to-indigo-700 shadow-lg shadow-blue-500/25 transition-all"
        >
          <Plus className="w-4 h-4" />
          Create Agent
        </motion.button>
      </motion.div>

      {/* Stats */}
      <motion.div variants={item} className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
        <GlassCard>
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500/30 to-indigo-600/30 flex items-center justify-center">
              <Bot className="w-5 h-5 text-blue-400" />
            </div>
            <div>
              <p className="text-2xl font-bold font-mono text-white">{agents.filter((a) => a.active).length}</p>
              <p className="text-xs text-gray-400">Active Agents</p>
            </div>
          </div>
        </GlassCard>
        <GlassCard>
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-emerald-500/30 to-teal-600/30 flex items-center justify-center">
              <MessageSquare className="w-5 h-5 text-emerald-400" />
            </div>
            <div>
              <p className="text-2xl font-bold font-mono text-white">
                {agents.reduce((sum, a) => sum + a.conversationCount, 0).toLocaleString()}
              </p>
              <p className="text-xs text-gray-400">Total Conversations</p>
            </div>
          </div>
        </GlassCard>
        <GlassCard>
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-amber-500/30 to-orange-600/30 flex items-center justify-center">
              <Zap className="w-5 h-5 text-amber-400" />
            </div>
            <div>
              <p className="text-2xl font-bold font-mono text-white">
                {(agents.filter((a) => a.active).reduce((sum, a) => sum + a.avgResponseTime, 0) / Math.max(agents.filter((a) => a.active).length, 1)).toFixed(1)}s
              </p>
              <p className="text-xs text-gray-400">Avg Response Time</p>
            </div>
          </div>
        </GlassCard>
      </motion.div>

      {/* Agent Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
        {agents.map((agent) => (
          <motion.div key={agent.id} variants={item}>
            <GlassCard hover className="cursor-pointer h-full">
              <div onClick={() => navigate(`/ai-agents/${agent.id}`)} className="flex-1">
                <div className="flex items-start justify-between mb-4">
                  <div className="flex items-center gap-3">
                    <div
                      className={clsx(
                        "w-11 h-11 rounded-xl flex items-center justify-center",
                        agent.active
                          ? "bg-gradient-to-br from-blue-500 to-indigo-600"
                          : "bg-white/10"
                      )}
                    >
                      <Sparkles className={clsx("w-5 h-5", agent.active ? "text-white" : "text-gray-500")} />
                    </div>
                    <div>
                      <h3 className="text-white font-semibold">{agent.name}</h3>
                      <p className="text-xs text-gray-500">{agent.model}</p>
                    </div>
                  </div>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      toggleAgent(agent.id);
                    }}
                    className="flex-shrink-0"
                  >
                    {agent.active ? (
                      <ToggleRight className="w-8 h-8 text-blue-400" />
                    ) : (
                      <ToggleLeft className="w-8 h-8 text-gray-600" />
                    )}
                  </button>
                </div>

                <p className="text-sm text-gray-400 mb-4 line-clamp-2">{agent.description}</p>

                <div className="grid grid-cols-2 gap-3">
                  <div className="bg-white/5 rounded-lg p-2.5">
                    <div className="flex items-center gap-1.5 text-gray-500 mb-1">
                      <MessageSquare className="w-3.5 h-3.5" />
                      <span className="text-xs">Conversations</span>
                    </div>
                    <p className="text-sm font-mono font-bold text-white">
                      {agent.conversationCount.toLocaleString()}
                    </p>
                  </div>
                  <div className="bg-white/5 rounded-lg p-2.5">
                    <div className="flex items-center gap-1.5 text-gray-500 mb-1">
                      <Clock className="w-3.5 h-3.5" />
                      <span className="text-xs">Avg Response</span>
                    </div>
                    <p className="text-sm font-mono font-bold text-white">{agent.avgResponseTime}s</p>
                  </div>
                </div>

                <div className="flex items-center justify-between mt-4 pt-3 border-t border-white/5">
                  <span
                    className={clsx(
                      "inline-flex items-center gap-1.5 text-xs font-medium",
                      agent.active ? "text-emerald-400" : "text-gray-500"
                    )}
                  >
                    <span
                      className={clsx(
                        "w-1.5 h-1.5 rounded-full",
                        agent.active ? "bg-emerald-400 animate-pulse" : "bg-gray-600"
                      )}
                    />
                    {agent.active ? "Active" : "Inactive"}
                  </span>
                  <span className="text-xs text-gray-500">{agent.lastActive}</span>
                </div>
              </div>
            </GlassCard>
          </motion.div>
        ))}
      </div>

      {/* Create Agent Modal */}
      <AnimatePresence>
        {showCreate && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setShowCreate(false)}
              className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50"
            />
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 20 }}
              className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-full max-w-lg z-50"
            >
              <div className="bg-navy-900/95 backdrop-blur-xl border border-white/10 rounded-2xl shadow-2xl p-6">
                <div className="flex items-center justify-between mb-6">
                  <h3 className="text-lg font-semibold text-white">Create New Agent</h3>
                  <button onClick={() => setShowCreate(false)} className="text-gray-500 hover:text-white">
                    <X className="w-5 h-5" />
                  </button>
                </div>
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-1.5">Agent Name</label>
                    <input
                      value={newAgent.name}
                      onChange={(e) => setNewAgent((p) => ({ ...p, name: e.target.value }))}
                      placeholder="e.g. Support Assistant"
                      className={inputClass}
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-1.5">AI Model</label>
                    <select
                      value={newAgent.model}
                      onChange={(e) => setNewAgent((p) => ({ ...p, model: e.target.value }))}
                      className={inputClass}
                    >
                      {modelOptions.map((m) => (
                        <option key={m} value={m} className="bg-navy-900">{m}</option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-1.5">Description</label>
                    <textarea
                      value={newAgent.description}
                      onChange={(e) => setNewAgent((p) => ({ ...p, description: e.target.value }))}
                      rows={3}
                      placeholder="What will this agent do?"
                      className={clsx(inputClass, "resize-none")}
                    />
                  </div>
                </div>
                <div className="flex justify-end gap-3 mt-6">
                  <button
                    onClick={() => setShowCreate(false)}
                    className="px-4 py-2.5 rounded-xl text-sm text-gray-400 hover:text-white bg-white/5 hover:bg-white/10 border border-white/10 transition-all"
                  >
                    Cancel
                  </button>
                  <motion.button
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                    onClick={handleCreate}
                    disabled={creating}
                    className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl font-semibold text-sm text-white bg-gradient-to-r from-blue-500 to-indigo-600 shadow-lg shadow-blue-500/25 disabled:opacity-60 transition-all"
                  >
                    {creating ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}
                    {creating ? "Creating..." : "Create Agent"}
                  </motion.button>
                </div>
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
