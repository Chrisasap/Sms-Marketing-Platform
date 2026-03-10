import { useState, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Shield,
  Clock,
  CheckCircle2,
  XCircle,
  Loader2,
  X,
  ChevronRight,
  Building2,
  Megaphone,
  AlertTriangle,
} from "lucide-react";
import clsx from "clsx";
import GlassCard from "../components/ui/GlassCard";
import toast from "react-hot-toast";
import api from "../lib/api";
import { format } from "date-fns";

interface QueueItem {
  id: string;
  tenant_name: string;
  type: "brand" | "campaign";
  status: "pending_review" | "approved" | "rejected";
  created_at: string;
  form_data: Record<string, unknown>;
  tenant_id: string;
  admin_notes?: string;
  rejection_reason?: string;
}

type FilterStatus = "all" | "pending_review" | "approved" | "rejected";

const statusConfig = {
  pending_review: {
    label: "Pending",
    color: "text-amber-400",
    bg: "bg-amber-500/20",
    icon: Clock,
  },
  approved: {
    label: "Approved",
    color: "text-emerald-400",
    bg: "bg-emerald-500/20",
    icon: CheckCircle2,
  },
  rejected: {
    label: "Rejected",
    color: "text-rose-400",
    bg: "bg-rose-500/20",
    icon: XCircle,
  },
};

const filterButtons: { value: FilterStatus; label: string }[] = [
  { value: "all", label: "All" },
  { value: "pending_review", label: "Pending" },
  { value: "approved", label: "Approved" },
  { value: "rejected", label: "Rejected" },
];

export default function AdminDLCQueue() {
  const [items, setItems] = useState<QueueItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<FilterStatus>("pending_review");
  const [selectedItem, setSelectedItem] = useState<QueueItem | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [reviewAction, setReviewAction] = useState<"approve" | "reject" | null>(
    null
  );
  const [adminNotes, setAdminNotes] = useState("");
  const [rejectionReason, setRejectionReason] = useState("");
  const [submittingReview, setSubmittingReview] = useState(false);

  const fetchQueue = useCallback(async () => {
    setLoading(true);
    try {
      const params =
        filter === "all" ? {} : { status: filter };
      const res = await api.get("/admin/dlc-queue", { params });
      setItems(res.data.applications ?? res.data);
    } catch {
      toast.error("Failed to load DLC queue");
    } finally {
      setLoading(false);
    }
  }, [filter]);

  useEffect(() => {
    fetchQueue();
  }, [fetchQueue]);

  const openDetail = async (item: QueueItem) => {
    setDetailLoading(true);
    setSelectedItem(item);
    setReviewAction(null);
    setAdminNotes("");
    setRejectionReason("");
    try {
      const res = await api.get(`/admin/dlc-queue/${item.id}`);
      setSelectedItem(res.data);
    } catch {
      toast.error("Failed to load details");
    } finally {
      setDetailLoading(false);
    }
  };

  const closeDetail = () => {
    setSelectedItem(null);
    setReviewAction(null);
    setAdminNotes("");
    setRejectionReason("");
  };

  const submitReview = async () => {
    if (!selectedItem || !reviewAction) return;
    if (reviewAction === "reject" && !rejectionReason.trim()) {
      toast.error("Please provide a rejection reason");
      return;
    }

    setSubmittingReview(true);
    try {
      await api.post(`/admin/dlc-queue/${selectedItem.id}/review`, {
        action: reviewAction,
        admin_notes: adminNotes || null,
        rejection_reason:
          reviewAction === "reject" ? rejectionReason : null,
      });
      toast.success(
        reviewAction === "approve"
          ? "Application approved successfully!"
          : "Application rejected."
      );
      closeDetail();
      fetchQueue();
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string } } };
      toast.error(error?.response?.data?.detail || "Failed to submit review");
    } finally {
      setSubmittingReview(false);
    }
  };

  const inputClass =
    "w-full px-4 py-3 bg-white/5 border border-white/10 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500/50 transition-all";

  return (
    <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-8">
        <div>
          <h1 className="text-3xl font-bold text-white flex items-center gap-3">
            <Shield className="w-8 h-8 text-blue-400" />
            10DLC Review Queue
          </h1>
          <p className="text-gray-400 mt-1">
            Review and approve or reject 10DLC brand and campaign registrations.
          </p>
        </div>
      </div>

      {/* Filter Buttons */}
      <div className="flex gap-2 mb-6">
        {filterButtons.map((btn) => (
          <button
            key={btn.value}
            onClick={() => setFilter(btn.value)}
            className={clsx(
              "px-4 py-2 rounded-xl text-sm font-medium border transition-all",
              filter === btn.value
                ? "bg-blue-500/20 border-blue-500/50 text-blue-300"
                : "bg-white/5 border-white/10 text-gray-400 hover:bg-white/10 hover:text-white"
            )}
          >
            {btn.label}
          </button>
        ))}
      </div>

      {/* Queue Table */}
      <GlassCard>
        {loading ? (
          <div className="flex items-center justify-center py-16">
            <Loader2 className="w-8 h-8 text-blue-400 animate-spin" />
          </div>
        ) : items.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 text-gray-500">
            <CheckCircle2 className="w-12 h-12 mb-3 text-gray-600" />
            <p className="text-lg font-medium">No applications found</p>
            <p className="text-sm mt-1">
              {filter === "pending_review"
                ? "All caught up! No pending reviews."
                : "No applications match this filter."}
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-white/10">
                  <th className="text-left text-xs font-medium text-gray-500 uppercase tracking-wider py-3 px-4">
                    Tenant
                  </th>
                  <th className="text-left text-xs font-medium text-gray-500 uppercase tracking-wider py-3 px-4">
                    Type
                  </th>
                  <th className="text-left text-xs font-medium text-gray-500 uppercase tracking-wider py-3 px-4">
                    Status
                  </th>
                  <th className="text-left text-xs font-medium text-gray-500 uppercase tracking-wider py-3 px-4">
                    Submitted
                  </th>
                  <th className="text-right text-xs font-medium text-gray-500 uppercase tracking-wider py-3 px-4">
                    Action
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {items.map((item) => {
                  const status = statusConfig[item.status];
                  const StatusIcon = status.icon;
                  return (
                    <motion.tr
                      key={item.id}
                      whileHover={{ backgroundColor: "rgba(255,255,255,0.03)" }}
                      className="cursor-pointer transition-colors"
                      onClick={() => openDetail(item)}
                    >
                      <td className="py-4 px-4">
                        <span className="text-sm text-white font-medium">
                          {item.tenant_name}
                        </span>
                      </td>
                      <td className="py-4 px-4">
                        <span className="inline-flex items-center gap-1.5 text-sm text-gray-300">
                          {item.type === "brand" ? (
                            <Building2 className="w-3.5 h-3.5 text-blue-400" />
                          ) : (
                            <Megaphone className="w-3.5 h-3.5 text-indigo-400" />
                          )}
                          {item.type === "brand" ? "Brand" : "Campaign"}
                        </span>
                      </td>
                      <td className="py-4 px-4">
                        <span
                          className={clsx(
                            "inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium",
                            status.bg,
                            status.color
                          )}
                        >
                          <StatusIcon className="w-3 h-3" />
                          {status.label}
                        </span>
                      </td>
                      <td className="py-4 px-4">
                        <span className="text-sm text-gray-400">
                          {format(new Date(item.created_at), "MMM d, yyyy h:mm a")}
                        </span>
                      </td>
                      <td className="py-4 px-4 text-right">
                        <ChevronRight className="w-4 h-4 text-gray-500 ml-auto" />
                      </td>
                    </motion.tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </GlassCard>

      {/* Detail Panel / Modal */}
      <AnimatePresence>
        {selectedItem && (
          <>
            {/* Backdrop */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={closeDetail}
              className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50"
            />

            {/* Panel */}
            <motion.div
              initial={{ x: "100%" }}
              animate={{ x: 0 }}
              exit={{ x: "100%" }}
              transition={{ type: "spring", damping: 25, stiffness: 200 }}
              className="fixed right-0 top-0 h-screen w-full max-w-2xl bg-navy-900/95 backdrop-blur-xl border-l border-white/10 z-50 overflow-y-auto"
            >
              <div className="p-6">
                {/* Panel Header */}
                <div className="flex items-center justify-between mb-6">
                  <h2 className="text-xl font-bold text-white">
                    Application Details
                  </h2>
                  <button
                    onClick={closeDetail}
                    className="p-2 rounded-xl bg-white/5 hover:bg-white/10 text-gray-400 hover:text-white transition-all"
                  >
                    <X className="w-5 h-5" />
                  </button>
                </div>

                {detailLoading ? (
                  <div className="flex items-center justify-center py-16">
                    <Loader2 className="w-8 h-8 text-blue-400 animate-spin" />
                  </div>
                ) : (
                  <div className="space-y-6">
                    {/* Status Badge */}
                    <div className="flex items-center gap-3">
                      {(() => {
                        const status = statusConfig[selectedItem.status];
                        const StatusIcon = status.icon;
                        return (
                          <span
                            className={clsx(
                              "inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-sm font-medium",
                              status.bg,
                              status.color
                            )}
                          >
                            <StatusIcon className="w-4 h-4" />
                            {status.label}
                          </span>
                        );
                      })()}
                      <span className="inline-flex items-center gap-1.5 text-sm text-gray-400">
                        {selectedItem.type === "brand" ? (
                          <Building2 className="w-4 h-4" />
                        ) : (
                          <Megaphone className="w-4 h-4" />
                        )}
                        {selectedItem.type === "brand"
                          ? "Brand Registration"
                          : "Campaign Registration"}
                      </span>
                    </div>

                    {/* Tenant Info */}
                    <div className="bg-white/5 rounded-xl p-4">
                      <h4 className="text-xs text-gray-500 uppercase tracking-wider mb-3">
                        Tenant Information
                      </h4>
                      <div className="grid grid-cols-2 gap-3 text-sm">
                        <div>
                          <span className="text-gray-500">Tenant:</span>{" "}
                          <span className="text-white ml-1">
                            {selectedItem.tenant_name}
                          </span>
                        </div>
                        <div>
                          <span className="text-gray-500">Submitted:</span>{" "}
                          <span className="text-white ml-1">
                            {format(
                              new Date(selectedItem.created_at),
                              "MMM d, yyyy h:mm a"
                            )}
                          </span>
                        </div>
                      </div>
                    </div>

                    {/* Form Data */}
                    <div className="bg-white/5 rounded-xl p-4">
                      <h4 className="text-xs text-gray-500 uppercase tracking-wider mb-3">
                        {selectedItem.type === "brand"
                          ? "Brand Details"
                          : "Campaign Details"}
                      </h4>
                      <div className="space-y-2 text-sm">
                        {Object.entries(selectedItem.form_data || {}).map(
                          ([key, value]) => {
                            if (value === null || value === undefined)
                              return null;
                            const label = key
                              .replace(/_/g, " ")
                              .replace(/\b\w/g, (l) => l.toUpperCase());
                            let displayValue: string;
                            if (Array.isArray(value)) {
                              displayValue = value.join(", ");
                            } else if (typeof value === "boolean") {
                              displayValue = value ? "Yes" : "No";
                            } else {
                              displayValue = String(value);
                            }
                            return (
                              <div
                                key={key}
                                className="flex justify-between py-1 border-b border-white/5 last:border-0"
                              >
                                <span className="text-gray-500">{label}</span>
                                <span className="text-white text-right max-w-[60%] break-words">
                                  {displayValue}
                                </span>
                              </div>
                            );
                          }
                        )}
                      </div>
                    </div>

                    {/* Existing Admin Notes / Rejection Reason */}
                    {selectedItem.admin_notes && (
                      <div className="bg-blue-500/10 border border-blue-500/20 rounded-xl p-4">
                        <h4 className="text-xs text-blue-400 uppercase tracking-wider mb-2">
                          Admin Notes
                        </h4>
                        <p className="text-sm text-gray-300">
                          {selectedItem.admin_notes}
                        </p>
                      </div>
                    )}
                    {selectedItem.rejection_reason && (
                      <div className="bg-rose-500/10 border border-rose-500/20 rounded-xl p-4">
                        <h4 className="text-xs text-rose-400 uppercase tracking-wider mb-2">
                          Rejection Reason
                        </h4>
                        <p className="text-sm text-gray-300">
                          {selectedItem.rejection_reason}
                        </p>
                      </div>
                    )}

                    {/* Review Actions (only for pending) */}
                    {selectedItem.status === "pending_review" && (
                      <div className="space-y-4">
                        <div className="border-t border-white/10 pt-4">
                          <h4 className="text-sm font-semibold text-white mb-3">
                            Review Actions
                          </h4>

                          <div>
                            <label className="block text-sm font-medium text-gray-300 mb-1.5">
                              Admin Notes{" "}
                              <span className="text-gray-500">(optional)</span>
                            </label>
                            <textarea
                              value={adminNotes}
                              onChange={(e) => setAdminNotes(e.target.value)}
                              rows={2}
                              placeholder="Internal notes about this review..."
                              className={clsx(inputClass, "resize-none")}
                            />
                          </div>

                          {reviewAction === "reject" && (
                            <motion.div
                              initial={{ opacity: 0, height: 0 }}
                              animate={{ opacity: 1, height: "auto" }}
                              className="mt-3"
                            >
                              <label className="block text-sm font-medium text-gray-300 mb-1.5">
                                Rejection Reason{" "}
                                <span className="text-rose-400">*</span>
                              </label>
                              <textarea
                                value={rejectionReason}
                                onChange={(e) =>
                                  setRejectionReason(e.target.value)
                                }
                                rows={2}
                                placeholder="Explain why this application is being rejected..."
                                className={clsx(
                                  inputClass,
                                  "resize-none border-rose-500/30 focus:ring-rose-500/50"
                                )}
                              />
                            </motion.div>
                          )}

                          <div className="flex gap-3 mt-4">
                            <motion.button
                              type="button"
                              onClick={() => {
                                setReviewAction("approve");
                                // If already set to approve, submit
                                if (reviewAction === "approve") {
                                  submitReview();
                                }
                              }}
                              whileHover={{ scale: 1.02 }}
                              whileTap={{ scale: 0.98 }}
                              disabled={submittingReview}
                              className={clsx(
                                "flex-1 inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-xl font-semibold text-sm transition-all disabled:opacity-60",
                                reviewAction === "approve"
                                  ? "bg-gradient-to-r from-emerald-500 to-teal-600 text-white shadow-lg shadow-emerald-500/25"
                                  : "bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 hover:bg-emerald-500/20"
                              )}
                            >
                              {submittingReview &&
                              reviewAction === "approve" ? (
                                <Loader2 className="w-4 h-4 animate-spin" />
                              ) : (
                                <CheckCircle2 className="w-4 h-4" />
                              )}
                              {reviewAction === "approve"
                                ? "Confirm Approve"
                                : "Approve"}
                            </motion.button>

                            <motion.button
                              type="button"
                              onClick={() => {
                                if (reviewAction === "reject") {
                                  submitReview();
                                } else {
                                  setReviewAction("reject");
                                }
                              }}
                              whileHover={{ scale: 1.02 }}
                              whileTap={{ scale: 0.98 }}
                              disabled={submittingReview}
                              className={clsx(
                                "flex-1 inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-xl font-semibold text-sm transition-all disabled:opacity-60",
                                reviewAction === "reject"
                                  ? "bg-gradient-to-r from-rose-500 to-red-600 text-white shadow-lg shadow-rose-500/25"
                                  : "bg-rose-500/10 border border-rose-500/20 text-rose-400 hover:bg-rose-500/20"
                              )}
                            >
                              {submittingReview &&
                              reviewAction === "reject" ? (
                                <Loader2 className="w-4 h-4 animate-spin" />
                              ) : (
                                <XCircle className="w-4 h-4" />
                              )}
                              {reviewAction === "reject"
                                ? "Confirm Reject"
                                : "Reject"}
                            </motion.button>
                          </div>

                          {reviewAction && (
                            <div className="mt-3 flex items-start gap-2 bg-amber-500/10 border border-amber-500/20 rounded-xl p-3">
                              <AlertTriangle className="w-4 h-4 text-amber-400 mt-0.5 flex-shrink-0" />
                              <p className="text-xs text-amber-300">
                                {reviewAction === "approve"
                                  ? "Approving will forward this registration to Bandwidth/TCR for processing."
                                  : "Rejecting will notify the tenant and require them to resubmit."}
                              </p>
                            </div>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
