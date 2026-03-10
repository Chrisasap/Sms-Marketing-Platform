import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  ClipboardCheck,
  Loader2,
  X,
  Sparkles,
  XCircle,
  AlertTriangle,
  Brain,
  Zap,
  Eye,
  ThumbsUp,
  ThumbsDown,
  RefreshCw,
} from "lucide-react";
import clsx from "clsx";
import toast from "react-hot-toast";
import GlassCard from "../../components/ui/GlassCard";
import api from "../../lib/api";

const container = { hidden: { opacity: 0 }, show: { opacity: 1, transition: { staggerChildren: 0.05 } } };
const item = { hidden: { opacity: 0, y: 20 }, show: { opacity: 1, y: 0 } };

interface DLCApplication {
  id: string;
  tenant_id: string;
  tenant_name?: string;
  application_type: string;
  status: string;
  form_data: Record<string, unknown>;
  ai_score: number | null;
  ai_verdict: string | null;
  submitted_at: string;
  reviewed_at: string | null;
}

interface AIReviewResult {
  score: number;
  verdict: string;
  issues: AIIssue[];
  suggestions: Record<string, string>;
  summary: string;
}

interface AIIssue {
  field: string;
  severity: "critical" | "warning" | "info";
  message: string;
  suggestion?: string;
}

const statusColors: Record<string, string> = {
  pending_review: "bg-amber-500/20 text-amber-400",
  pending: "bg-amber-500/20 text-amber-400",
  approved: "bg-emerald-500/20 text-emerald-400",
  rejected: "bg-rose-500/20 text-rose-400",
  ai_reviewed: "bg-purple-500/20 text-purple-400",
};

const verdictColors: Record<string, string> = {
  pass: "text-emerald-400",
  fail: "text-rose-400",
  needs_review: "text-amber-400",
  warning: "text-amber-400",
};

const severityConfig: Record<string, { bg: string; text: string; icon: typeof AlertTriangle }> = {
  critical: { bg: "bg-rose-500/20", text: "text-rose-400", icon: XCircle },
  warning: { bg: "bg-amber-500/20", text: "text-amber-400", icon: AlertTriangle },
  info: { bg: "bg-blue-500/20", text: "text-blue-400", icon: Eye },
};

function ScoreGauge({ score, size = 120 }: { score: number; size?: number }) {
  const radius = (size / 2) - 12;
  const circumference = 2 * Math.PI * radius;
  const progress = (score / 100) * circumference;
  const color = score >= 80 ? "#10b981" : score >= 60 ? "#f59e0b" : "#ef4444";

  return (
    <div className="relative mx-auto" style={{ width: size, height: size }}>
      <svg className="w-full h-full -rotate-90" viewBox={`0 0 ${size} ${size}`}>
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="rgba(255,255,255,0.05)"
          strokeWidth="8"
        />
        <motion.circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth="8"
          strokeLinecap="round"
          strokeDasharray={circumference}
          initial={{ strokeDashoffset: circumference }}
          animate={{ strokeDashoffset: circumference - progress }}
          transition={{ duration: 1.2, ease: "easeOut" }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <motion.span
          className="text-2xl font-bold font-mono text-white"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.4 }}
        >
          {score}
        </motion.span>
        <span className="text-xs text-gray-400">AI Score</span>
      </div>
    </div>
  );
}

function getScoreBadgeColor(score: number | null): string {
  if (score === null) return "bg-gray-500/20 text-gray-400";
  if (score >= 80) return "bg-emerald-500/20 text-emerald-400";
  if (score >= 60) return "bg-amber-500/20 text-amber-400";
  return "bg-rose-500/20 text-rose-400";
}

export default function AdminDLCQueueV2() {
  const queryClient = useQueryClient();
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState("");

  const { data, isLoading } = useQuery({
    queryKey: ["admin-dlc-queue", statusFilter],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (statusFilter) params.set("status", statusFilter);
      const res = await api.get(`/admin/dlc-queue?${params}`);
      return res.data;
    },
  });

  const { data: detailData, isLoading: detailLoading } = useQuery({
    queryKey: ["admin-dlc-detail", selectedId],
    queryFn: async () => {
      const res = await api.get(`/admin/dlc-queue/${selectedId}`);
      return res.data;
    },
    enabled: !!selectedId,
  });

  const { data: aiReviewData, refetch: refetchAIReview } = useQuery<AIReviewResult>({
    queryKey: ["admin-dlc-ai-review", selectedId],
    queryFn: async () => {
      const res = await api.get(`/admin/dlc-queue/${selectedId}/ai-review`);
      return res.data;
    },
    enabled: !!selectedId,
    retry: false,
  });

  const runAIReviewMutation = useMutation({
    mutationFn: async (id: string) => {
      const res = await api.post(`/admin/dlc-queue/${id}/ai-review`);
      return res.data;
    },
    onSuccess: () => {
      refetchAIReview();
      queryClient.invalidateQueries({ queryKey: ["admin-dlc-queue"] });
      toast.success("AI review completed");
    },
    onError: (err: any) => {
      toast.error(err?.response?.data?.detail || "AI review failed");
    },
  });

  const enhanceMutation = useMutation({
    mutationFn: async ({ id, field }: { id: string; field?: string }) => {
      const res = await api.post(`/admin/dlc-queue/${id}/ai-enhance`, { field });
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-dlc-detail", selectedId] });
      refetchAIReview();
      toast.success("AI enhancement applied");
    },
    onError: (err: any) => {
      toast.error(err?.response?.data?.detail || "Enhancement failed");
    },
  });

  const reviewMutation = useMutation({
    mutationFn: async ({ id, decision, notes }: { id: string; decision: "approved" | "rejected"; notes?: string }) => {
      await api.post(`/admin/dlc-queue/${id}/review`, { decision, notes });
    },
    onSuccess: (_, vars) => {
      queryClient.invalidateQueries({ queryKey: ["admin-dlc-queue"] });
      setSelectedId(null);
      toast.success(`Application ${vars.decision}`);
    },
    onError: (err: any) => {
      toast.error(err?.response?.data?.detail || "Review failed");
    },
  });

  const applications: DLCApplication[] = data?.applications || [];
  const detail: DLCApplication | null = detailData || null;

  return (
    <motion.div variants={container} initial="hidden" animate="show">
      <motion.div variants={item} className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold text-white">10DLC Review Queue</h1>
          <p className="text-gray-400 mt-1">Review and approve DLC applications with AI assistance</p>
        </div>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="px-4 py-2.5 bg-white/5 border border-white/10 rounded-xl text-sm text-gray-300 focus:outline-none"
        >
          <option value="">All Status</option>
          <option value="pending_review">Pending Review</option>
          <option value="ai_reviewed">AI Reviewed</option>
          <option value="approved">Approved</option>
          <option value="rejected">Rejected</option>
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
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Type</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Submitted</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">AI Score</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">AI Verdict</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Status</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5">
                  {applications.map((app) => (
                    <motion.tr
                      key={app.id}
                      whileHover={{ backgroundColor: "rgba(255,255,255,0.03)" }}
                      className={clsx(
                        "cursor-pointer transition-colors",
                        selectedId === app.id && "bg-white/5"
                      )}
                      onClick={() => setSelectedId(app.id)}
                    >
                      <td className="px-4 py-3">
                        <p className="text-sm font-medium text-white">{app.tenant_name || app.tenant_id.slice(0, 8)}</p>
                      </td>
                      <td className="px-4 py-3">
                        <span className="text-sm text-gray-300 capitalize">{app.application_type.replace(/_/g, " ")}</span>
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-500">
                        {new Date(app.submitted_at).toLocaleDateString()}
                      </td>
                      <td className="px-4 py-3">
                        {app.ai_score !== null ? (
                          <span className={clsx("px-2 py-1 rounded-full text-xs font-bold", getScoreBadgeColor(app.ai_score))}>
                            {app.ai_score}
                          </span>
                        ) : (
                          <span className="text-xs text-gray-600">--</span>
                        )}
                      </td>
                      <td className="px-4 py-3">
                        {app.ai_verdict ? (
                          <span className={clsx("text-sm font-medium capitalize", verdictColors[app.ai_verdict] || "text-gray-400")}>
                            {app.ai_verdict.replace(/_/g, " ")}
                          </span>
                        ) : (
                          <span className="text-xs text-gray-600">--</span>
                        )}
                      </td>
                      <td className="px-4 py-3">
                        <span className={clsx("px-2 py-1 rounded-full text-xs font-medium", statusColors[app.status] || statusColors.pending)}>
                          {app.status.replace(/_/g, " ")}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <button
                          onClick={(e) => { e.stopPropagation(); setSelectedId(app.id); }}
                          className="text-blue-400 hover:text-blue-300 text-sm flex items-center gap-1"
                        >
                          <Eye className="w-4 h-4" /> Review
                        </button>
                      </td>
                    </motion.tr>
                  ))}
                  {applications.length === 0 && (
                    <tr>
                      <td colSpan={7} className="px-4 py-12 text-center text-gray-500">
                        No applications in queue
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </GlassCard>
        </motion.div>
      )}

      {/* Detail Slide-Out Panel */}
      <AnimatePresence>
        {selectedId && (
          <>
            {/* Backdrop */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setSelectedId(null)}
              className="fixed inset-0 bg-black/50 z-50"
            />

            {/* Panel */}
            <motion.div
              initial={{ x: "100%" }}
              animate={{ x: 0 }}
              exit={{ x: "100%" }}
              transition={{ type: "spring", damping: 30, stiffness: 300 }}
              className="fixed right-0 top-0 h-screen w-full max-w-4xl bg-navy-900 border-l border-white/10 z-50 overflow-y-auto"
            >
              {detailLoading ? (
                <div className="flex items-center justify-center h-full">
                  <Loader2 className="w-8 h-8 text-blue-400 animate-spin" />
                </div>
              ) : detail ? (
                <div className="p-8">
                  {/* Panel Header */}
                  <div className="flex items-center justify-between mb-8">
                    <div>
                      <h2 className="text-2xl font-bold text-white">
                        {detail.tenant_name || "Application"} - {detail.application_type.replace(/_/g, " ")}
                      </h2>
                      <p className="text-gray-400 text-sm mt-1">ID: {detail.id}</p>
                    </div>
                    <button
                      onClick={() => setSelectedId(null)}
                      className="w-10 h-10 rounded-xl bg-white/5 hover:bg-white/10 flex items-center justify-center text-gray-400 hover:text-white transition-colors"
                    >
                      <X className="w-5 h-5" />
                    </button>
                  </div>

                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    {/* Left: Form Data */}
                    <div>
                      <h3 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
                        <ClipboardCheck className="w-4 h-4 text-blue-400" />
                        Application Data
                      </h3>
                      <div className="space-y-3">
                        {Object.entries(detail.form_data || {}).map(([key, value]) => (
                          <div key={key} className="bg-white/5 rounded-xl p-4">
                            <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">
                              {key.replace(/_/g, " ")}
                            </p>
                            <p className="text-sm text-white break-words">
                              {typeof value === "object" ? JSON.stringify(value, null, 2) : String(value)}
                            </p>
                            {aiReviewData?.suggestions?.[key] && (
                              <div className="mt-2 pt-2 border-t border-white/5">
                                <p className="text-xs text-purple-400 mb-1 flex items-center gap-1">
                                  <Sparkles className="w-3 h-3" /> AI Suggestion
                                </p>
                                <p className="text-xs text-gray-300">{aiReviewData.suggestions[key]}</p>
                                <button
                                  onClick={() => enhanceMutation.mutate({ id: detail.id, field: key })}
                                  className="mt-1.5 text-xs text-purple-400 hover:text-purple-300 font-medium"
                                >
                                  Accept Suggestion
                                </button>
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>

                    {/* Right: AI Review */}
                    <div>
                      <h3 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
                        <Brain className="w-4 h-4 text-purple-400" />
                        AI Review
                      </h3>

                      {aiReviewData ? (
                        <div className="space-y-4">
                          {/* Score Gauge */}
                          <GlassCard>
                            <ScoreGauge score={aiReviewData.score} />
                            <div className="text-center mt-3">
                              <span className={clsx(
                                "px-3 py-1 rounded-full text-sm font-bold capitalize",
                                aiReviewData.verdict === "pass" ? "bg-emerald-500/20 text-emerald-400" :
                                aiReviewData.verdict === "fail" ? "bg-rose-500/20 text-rose-400" :
                                "bg-amber-500/20 text-amber-400"
                              )}>
                                {aiReviewData.verdict.replace(/_/g, " ")}
                              </span>
                            </div>
                            {aiReviewData.summary && (
                              <p className="text-sm text-gray-400 text-center mt-3">{aiReviewData.summary}</p>
                            )}
                          </GlassCard>

                          {/* Issues */}
                          {aiReviewData.issues.length > 0 && (
                            <div>
                              <h4 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">
                                Issues ({aiReviewData.issues.length})
                              </h4>
                              <div className="space-y-2">
                                {aiReviewData.issues.map((issue, i) => {
                                  const sev = severityConfig[issue.severity] || severityConfig.info;
                                  const SevIcon = sev.icon;
                                  return (
                                    <motion.div
                                      key={i}
                                      initial={{ opacity: 0, x: 20 }}
                                      animate={{ opacity: 1, x: 0 }}
                                      transition={{ delay: i * 0.05 }}
                                      className={clsx("rounded-xl p-4 border", sev.bg, "border-white/5")}
                                    >
                                      <div className="flex items-start gap-3">
                                        <SevIcon className={clsx("w-4 h-4 mt-0.5 flex-shrink-0", sev.text)} />
                                        <div className="flex-1">
                                          <div className="flex items-center gap-2 mb-1">
                                            <span className={clsx("text-xs font-bold uppercase", sev.text)}>
                                              {issue.severity}
                                            </span>
                                            <span className="text-xs text-gray-500">{issue.field}</span>
                                          </div>
                                          <p className="text-sm text-gray-300">{issue.message}</p>
                                          {issue.suggestion && (
                                            <p className="text-xs text-gray-500 mt-1">
                                              Suggestion: {issue.suggestion}
                                            </p>
                                          )}
                                        </div>
                                      </div>
                                    </motion.div>
                                  );
                                })}
                              </div>
                            </div>
                          )}

                          {/* Accept All Suggestions */}
                          {Object.keys(aiReviewData.suggestions || {}).length > 0 && (
                            <button
                              onClick={() => enhanceMutation.mutate({ id: detail.id })}
                              disabled={enhanceMutation.isPending}
                              className="w-full flex items-center justify-center gap-2 px-4 py-3 rounded-xl bg-purple-500/20 text-purple-400 hover:bg-purple-500/30 border border-purple-500/30 transition-colors font-medium text-sm"
                            >
                              {enhanceMutation.isPending ? (
                                <Loader2 className="w-4 h-4 animate-spin" />
                              ) : (
                                <Zap className="w-4 h-4" />
                              )}
                              Accept All AI Suggestions
                            </button>
                          )}
                        </div>
                      ) : (
                        <GlassCard className="text-center py-8">
                          <Brain className="w-10 h-10 text-gray-600 mx-auto mb-3" />
                          <p className="text-gray-500 text-sm mb-4">No AI review yet</p>
                          <button
                            onClick={() => runAIReviewMutation.mutate(detail.id)}
                            disabled={runAIReviewMutation.isPending}
                            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-gradient-to-r from-purple-500 to-indigo-600 text-white font-semibold text-sm hover:from-purple-600 hover:to-indigo-700 transition-all shadow-lg shadow-purple-500/25"
                          >
                            {runAIReviewMutation.isPending ? (
                              <Loader2 className="w-4 h-4 animate-spin" />
                            ) : (
                              <Sparkles className="w-4 h-4" />
                            )}
                            Run AI Review
                          </button>
                        </GlassCard>
                      )}

                      {/* Re-run AI Review */}
                      {aiReviewData && (
                        <button
                          onClick={() => runAIReviewMutation.mutate(detail.id)}
                          disabled={runAIReviewMutation.isPending}
                          className="w-full flex items-center justify-center gap-2 mt-4 px-4 py-2 rounded-xl bg-white/5 hover:bg-white/10 text-gray-400 hover:text-white border border-white/10 transition-colors text-sm"
                        >
                          {runAIReviewMutation.isPending ? (
                            <Loader2 className="w-4 h-4 animate-spin" />
                          ) : (
                            <RefreshCw className="w-4 h-4" />
                          )}
                          Re-run AI Review
                        </button>
                      )}
                    </div>
                  </div>

                  {/* Action Buttons */}
                  <div className="flex items-center gap-4 mt-8 pt-6 border-t border-white/10">
                    <motion.button
                      whileHover={{ scale: 1.02 }}
                      whileTap={{ scale: 0.98 }}
                      onClick={() => reviewMutation.mutate({ id: detail.id, decision: "approved" })}
                      disabled={reviewMutation.isPending}
                      className="flex-1 flex items-center justify-center gap-2 px-6 py-3 rounded-xl bg-gradient-to-r from-emerald-500 to-teal-600 text-white font-semibold hover:from-emerald-600 hover:to-teal-700 shadow-lg shadow-emerald-500/25 transition-all"
                    >
                      {reviewMutation.isPending ? (
                        <Loader2 className="w-4 h-4 animate-spin" />
                      ) : (
                        <ThumbsUp className="w-4 h-4" />
                      )}
                      Approve
                    </motion.button>
                    <motion.button
                      whileHover={{ scale: 1.02 }}
                      whileTap={{ scale: 0.98 }}
                      onClick={() => reviewMutation.mutate({ id: detail.id, decision: "rejected" })}
                      disabled={reviewMutation.isPending}
                      className="flex-1 flex items-center justify-center gap-2 px-6 py-3 rounded-xl bg-gradient-to-r from-rose-500 to-pink-600 text-white font-semibold hover:from-rose-600 hover:to-pink-700 shadow-lg shadow-rose-500/25 transition-all"
                    >
                      {reviewMutation.isPending ? (
                        <Loader2 className="w-4 h-4 animate-spin" />
                      ) : (
                        <ThumbsDown className="w-4 h-4" />
                      )}
                      Reject
                    </motion.button>
                  </div>
                </div>
              ) : null}
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
