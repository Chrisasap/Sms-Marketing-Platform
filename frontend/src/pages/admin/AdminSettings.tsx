import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Settings,
  Server,
  Bot,
  Shield,
  Loader2,
  CheckCircle2,
  XCircle,
  Edit3,
  Save,
  X,
  Layers,
  Gauge,
} from "lucide-react";
import clsx from "clsx";
import toast from "react-hot-toast";
import GlassCard from "../../components/ui/GlassCard";
import api from "../../lib/api";

const container = { hidden: { opacity: 0 }, show: { opacity: 1, transition: { staggerChildren: 0.06 } } };
const item = { hidden: { opacity: 0, y: 20 }, show: { opacity: 1, y: 0 } };

interface HealthData {
  status: string;
  database: string;
  redis: string;
  redis_memory?: string;
  server_time?: string;
  version?: string;
}

interface WorkerData {
  workers?: Array<{
    name: string;
    status: string;
    queues: string[];
  }>;
  queues?: Record<string, number>;
}

interface AIPrompt {
  id: string;
  name: string;
  prompt_type: string;
  model: string;
  temperature: number;
  version: number;
  is_active: boolean;
  prompt_text?: string;
  system_prompt?: string;
}

interface PromptEditState {
  id: string;
  model: string;
  temperature: number;
  prompt_text: string;
  system_prompt: string;
  is_active: boolean;
}

const inputClass =
  "w-full px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-white text-sm placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500/50 transition-all";

export default function AdminSettings() {
  const queryClient = useQueryClient();
  const [editingPrompt, setEditingPrompt] = useState<PromptEditState | null>(null);

  const { data: health, isLoading: healthLoading } = useQuery<HealthData>({
    queryKey: ["admin-health"],
    queryFn: async () => {
      const res = await api.get("/admin/health");
      return res.data;
    },
    refetchInterval: 30000,
  });

  const { data: workers } = useQuery<WorkerData>({
    queryKey: ["admin-workers"],
    queryFn: async () => {
      const res = await api.get("/admin/workers");
      return res.data;
    },
    refetchInterval: 15000,
  });

  const { data: promptsData } = useQuery<{ prompts: AIPrompt[] }>({
    queryKey: ["admin-ai-prompts"],
    queryFn: async () => {
      const res = await api.get("/admin/dlc-queue/ai-prompts");
      return res.data;
    },
  });

  const updatePromptMutation = useMutation({
    mutationFn: async (data: PromptEditState) => {
      await api.put(`/admin/dlc-queue/ai-prompts/${data.id}`, {
        model: data.model,
        temperature: data.temperature,
        prompt_text: data.prompt_text,
        system_prompt: data.system_prompt,
        is_active: data.is_active,
      });
    },
    onSuccess: () => {
      toast.success("Prompt updated (new version created)");
      setEditingPrompt(null);
      queryClient.invalidateQueries({ queryKey: ["admin-ai-prompts"] });
    },
    onError: () => {
      toast.error("Failed to update prompt");
    },
  });

  const prompts = promptsData?.prompts || [];
  const queues = workers?.queues || {};
  const maxQueueDepth = Math.max(...Object.values(queues), 1);

  return (
    <motion.div variants={container} initial="hidden" animate="show">
      <motion.div variants={item} className="mb-8">
        <h1 className="text-3xl font-bold text-white">Settings</h1>
        <p className="text-gray-400 mt-1">Platform configuration and system health</p>
      </motion.div>

      <div className="space-y-6">
        {/* Platform Info */}
        <motion.div variants={item}>
          <GlassCard>
            <div className="flex items-center gap-3 mb-5">
              <div className="w-10 h-10 rounded-xl bg-blue-500/20 flex items-center justify-center">
                <Server className="w-5 h-5 text-blue-400" />
              </div>
              <h3 className="text-lg font-semibold text-white">Platform Info</h3>
            </div>

            {healthLoading ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="w-6 h-6 text-blue-400 animate-spin" />
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                <div className="p-4 bg-white/5 rounded-xl">
                  <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">Application</p>
                  <p className="text-sm text-white font-semibold">BlastWave SMS</p>
                </div>
                <div className="p-4 bg-white/5 rounded-xl">
                  <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">Version</p>
                  <p className="text-sm text-white font-mono">{health?.version || "1.0.0"}</p>
                </div>
                <div className="p-4 bg-white/5 rounded-xl">
                  <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">Server Time</p>
                  <p className="text-sm text-white font-mono">
                    {health?.server_time
                      ? new Date(health.server_time).toLocaleString()
                      : "N/A"}
                  </p>
                </div>
                <div className="p-4 bg-white/5 rounded-xl">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">Database</p>
                      <p className="text-sm text-white font-medium capitalize">{health?.database || "unknown"}</p>
                    </div>
                    {health?.database === "connected" || health?.database === "healthy" ? (
                      <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                    ) : (
                      <XCircle className="w-5 h-5 text-rose-400" />
                    )}
                  </div>
                </div>
                <div className="p-4 bg-white/5 rounded-xl">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">Redis</p>
                      <p className="text-sm text-white font-medium capitalize">{health?.redis || "unknown"}</p>
                    </div>
                    {health?.redis === "connected" || health?.redis === "healthy" ? (
                      <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                    ) : (
                      <XCircle className="w-5 h-5 text-rose-400" />
                    )}
                  </div>
                </div>
                <div className="p-4 bg-white/5 rounded-xl">
                  <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">Redis Memory</p>
                  <p className="text-sm text-white font-mono">{health?.redis_memory || "N/A"}</p>
                </div>
              </div>
            )}
          </GlassCard>
        </motion.div>

        {/* AI Review Configuration */}
        <motion.div variants={item}>
          <GlassCard>
            <div className="flex items-center gap-3 mb-5">
              <div className="w-10 h-10 rounded-xl bg-purple-500/20 flex items-center justify-center">
                <Bot className="w-5 h-5 text-purple-400" />
              </div>
              <h3 className="text-lg font-semibold text-white">AI Review Configuration</h3>
            </div>

            {prompts.length === 0 ? (
              <div className="text-center py-8">
                <Bot className="w-8 h-8 text-gray-600 mx-auto mb-2" />
                <p className="text-gray-500 text-sm">No AI prompts configured</p>
              </div>
            ) : (
              <div className="space-y-3">
                {prompts.map((prompt) => (
                  <div key={prompt.id}>
                    <div className="flex items-center justify-between p-4 bg-white/5 rounded-xl">
                      <div className="flex items-center gap-4 flex-1 min-w-0">
                        <div className={clsx(
                          "w-2.5 h-2.5 rounded-full flex-shrink-0",
                          prompt.is_active ? "bg-emerald-400" : "bg-gray-500"
                        )} />
                        <div className="min-w-0">
                          <p className="text-sm font-medium text-white truncate">{prompt.name}</p>
                          <div className="flex items-center gap-3 mt-1">
                            <span className="text-xs text-gray-500">
                              Type: <span className="text-gray-400">{prompt.prompt_type}</span>
                            </span>
                            <span className="text-xs text-gray-500">
                              Model: <span className="text-blue-400 font-mono">{prompt.model}</span>
                            </span>
                            <span className="text-xs text-gray-500">
                              Temp: <span className="text-amber-400 font-mono">{prompt.temperature}</span>
                            </span>
                            <span className="text-xs text-gray-500">
                              v{prompt.version}
                            </span>
                          </div>
                        </div>
                      </div>
                      <button
                        onClick={() =>
                          setEditingPrompt({
                            id: prompt.id,
                            model: prompt.model,
                            temperature: prompt.temperature,
                            prompt_text: prompt.prompt_text || "",
                            system_prompt: prompt.system_prompt || "",
                            is_active: prompt.is_active,
                          })
                        }
                        className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-blue-400 bg-blue-500/10 hover:bg-blue-500/20 transition-all flex-shrink-0 ml-3"
                      >
                        <Edit3 className="w-3.5 h-3.5" />
                        Edit
                      </button>
                    </div>

                    {/* Inline Editor */}
                    <AnimatePresence>
                      {editingPrompt?.id === prompt.id && (
                        <motion.div
                          initial={{ opacity: 0, height: 0 }}
                          animate={{ opacity: 1, height: "auto" }}
                          exit={{ opacity: 0, height: 0 }}
                          className="overflow-hidden"
                        >
                          <div className="mt-2 p-4 bg-white/[0.03] border border-white/10 rounded-xl space-y-4">
                            <div className="grid grid-cols-2 gap-4">
                              <div>
                                <label className="block text-xs text-gray-400 mb-1">Model</label>
                                <input
                                  value={editingPrompt.model}
                                  onChange={(e) => setEditingPrompt({ ...editingPrompt, model: e.target.value })}
                                  className={inputClass}
                                />
                              </div>
                              <div>
                                <label className="block text-xs text-gray-400 mb-1">Temperature</label>
                                <input
                                  type="number"
                                  step="0.1"
                                  min="0"
                                  max="2"
                                  value={editingPrompt.temperature}
                                  onChange={(e) => setEditingPrompt({ ...editingPrompt, temperature: parseFloat(e.target.value) })}
                                  className={inputClass}
                                />
                              </div>
                            </div>
                            <div>
                              <label className="block text-xs text-gray-400 mb-1">System Prompt</label>
                              <textarea
                                value={editingPrompt.system_prompt}
                                onChange={(e) => setEditingPrompt({ ...editingPrompt, system_prompt: e.target.value })}
                                rows={3}
                                className={clsx(inputClass, "resize-none font-mono text-xs")}
                              />
                            </div>
                            <div>
                              <label className="block text-xs text-gray-400 mb-1">Prompt Text</label>
                              <textarea
                                value={editingPrompt.prompt_text}
                                onChange={(e) => setEditingPrompt({ ...editingPrompt, prompt_text: e.target.value })}
                                rows={4}
                                className={clsx(inputClass, "resize-none font-mono text-xs")}
                              />
                            </div>
                            <div className="flex items-center gap-3">
                              <label className="flex items-center gap-2 cursor-pointer">
                                <input
                                  type="checkbox"
                                  checked={editingPrompt.is_active}
                                  onChange={(e) => setEditingPrompt({ ...editingPrompt, is_active: e.target.checked })}
                                  className="w-4 h-4 rounded bg-white/10 border-white/20 text-blue-500 focus:ring-blue-500/50"
                                />
                                <span className="text-sm text-gray-300">Active</span>
                              </label>
                            </div>
                            <div className="flex items-center gap-2 pt-2 border-t border-white/10">
                              <button
                                onClick={() => updatePromptMutation.mutate(editingPrompt)}
                                disabled={updatePromptMutation.isPending}
                                className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium text-white bg-blue-600 hover:bg-blue-500 transition-colors disabled:opacity-50"
                              >
                                {updatePromptMutation.isPending ? (
                                  <Loader2 className="w-4 h-4 animate-spin" />
                                ) : (
                                  <Save className="w-4 h-4" />
                                )}
                                Save (Creates New Version)
                              </button>
                              <button
                                onClick={() => setEditingPrompt(null)}
                                className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm text-gray-400 hover:text-white bg-white/5 hover:bg-white/10 transition-all"
                              >
                                <X className="w-4 h-4" />
                                Cancel
                              </button>
                            </div>
                          </div>
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </div>
                ))}
              </div>
            )}
          </GlassCard>
        </motion.div>

        {/* Queue Management */}
        <motion.div variants={item}>
          <GlassCard>
            <div className="flex items-center gap-3 mb-5">
              <div className="w-10 h-10 rounded-xl bg-amber-500/20 flex items-center justify-center">
                <Layers className="w-5 h-5 text-amber-400" />
              </div>
              <h3 className="text-lg font-semibold text-white">Queue Management</h3>
            </div>

            {Object.keys(queues).length > 0 ? (
              <div className="space-y-3">
                {Object.entries(queues).map(([name, depth], i) => (
                  <motion.div
                    key={name}
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: i * 0.05 }}
                    className="flex items-center gap-4"
                  >
                    <span className="text-sm text-gray-400 font-mono w-28 text-right">{name}</span>
                    <div className="flex-1 bg-white/5 rounded-full h-6 overflow-hidden">
                      <motion.div
                        initial={{ width: 0 }}
                        animate={{ width: `${Math.max((depth / maxQueueDepth) * 100, depth > 0 ? 5 : 0)}%` }}
                        transition={{ duration: 0.5 }}
                        className={clsx(
                          "h-full rounded-full flex items-center px-3",
                          depth === 0
                            ? "bg-emerald-500/30"
                            : depth < 10
                            ? "bg-gradient-to-r from-blue-500 to-indigo-600"
                            : depth < 100
                            ? "bg-gradient-to-r from-amber-500 to-orange-600"
                            : "bg-gradient-to-r from-rose-500 to-pink-600"
                        )}
                      >
                        {depth > 0 && (
                          <span className="text-xs text-white font-mono font-medium">{depth}</span>
                        )}
                      </motion.div>
                    </div>
                    <span className="text-sm text-gray-500 font-mono w-12 text-right">{depth}</span>
                  </motion.div>
                ))}
              </div>
            ) : (
              <div className="text-center py-8">
                <Layers className="w-8 h-8 text-gray-600 mx-auto mb-2" />
                <p className="text-gray-500 text-sm">No queue data available</p>
              </div>
            )}

            {/* Worker list */}
            {workers?.workers && workers.workers.length > 0 && (
              <div className="mt-6 pt-4 border-t border-white/10">
                <p className="text-xs text-gray-500 uppercase tracking-wider mb-3">Active Workers</p>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                  {workers.workers.map((w, i) => (
                    <div key={i} className="flex items-center gap-3 p-3 bg-white/5 rounded-xl">
                      <div className={clsx(
                        "w-2.5 h-2.5 rounded-full",
                        w.status === "active" || w.status === "online" ? "bg-emerald-400" : "bg-gray-500"
                      )} />
                      <div className="min-w-0">
                        <p className="text-sm text-white font-mono truncate">{w.name}</p>
                        <p className="text-xs text-gray-500">Queues: {w.queues?.join(", ") || "all"}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </GlassCard>
        </motion.div>

        {/* Rate Limits */}
        <motion.div variants={item}>
          <GlassCard>
            <div className="flex items-center gap-3 mb-5">
              <div className="w-10 h-10 rounded-xl bg-rose-500/20 flex items-center justify-center">
                <Gauge className="w-5 h-5 text-rose-400" />
              </div>
              <h3 className="text-lg font-semibold text-white">Rate Limits</h3>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="p-4 bg-white/5 rounded-xl">
                <div className="flex items-center gap-2 mb-2">
                  <Shield className="w-4 h-4 text-blue-400" />
                  <p className="text-sm text-white font-medium">Login</p>
                </div>
                <p className="text-2xl font-bold text-white">5</p>
                <p className="text-xs text-gray-500 mt-1">requests per IP per minute</p>
              </div>
              <div className="p-4 bg-white/5 rounded-xl">
                <div className="flex items-center gap-2 mb-2">
                  <Shield className="w-4 h-4 text-emerald-400" />
                  <p className="text-sm text-white font-medium">Registration</p>
                </div>
                <p className="text-2xl font-bold text-white">3</p>
                <p className="text-xs text-gray-500 mt-1">requests per IP per hour</p>
              </div>
              <div className="p-4 bg-white/5 rounded-xl">
                <div className="flex items-center gap-2 mb-2">
                  <Shield className="w-4 h-4 text-amber-400" />
                  <p className="text-sm text-white font-medium">Password Reset</p>
                </div>
                <p className="text-2xl font-bold text-white">5</p>
                <p className="text-xs text-gray-500 mt-1">requests per IP per minute</p>
              </div>
            </div>
            <div className="mt-4 p-3 bg-amber-500/5 border border-amber-500/10 rounded-xl">
              <p className="text-xs text-amber-300/70 flex items-center gap-2">
                <Settings className="w-3.5 h-3.5" />
                Rate limit configuration editing will be available in a future release.
              </p>
            </div>
          </GlassCard>
        </motion.div>
      </div>
    </motion.div>
  );
}
