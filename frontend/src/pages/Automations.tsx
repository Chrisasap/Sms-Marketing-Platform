import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  MessageSquare,
  Plus,
  ToggleLeft,
  ToggleRight,
  Layers,
  Clock,
  Users,
  Hash,
  ChevronRight,
  X,
  Trash2,
} from "lucide-react";
import clsx from "clsx";
import GlassCard from "../components/ui/GlassCard";
import DataTable from "../components/ui/DataTable";
import toast from "react-hot-toast";

const container = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { staggerChildren: 0.08 } },
};

const item = {
  hidden: { opacity: 0, y: 20 },
  show: { opacity: 1, y: 0 },
};

interface AutoReply {
  id: string;
  triggerType: "keyword" | "regex" | "all";
  triggerValue: string;
  response: string;
  active: boolean;
}

interface DripStep {
  delayMinutes: number;
  message: string;
}

interface DripSequence {
  id: string;
  name: string;
  trigger: string;
  steps: DripStep[];
  active: boolean;
  enrollmentCount: number;
}

const initialAutoReplies: AutoReply[] = [
  { id: "1", triggerType: "keyword", triggerValue: "HOURS", response: "Our business hours are Mon-Fri 9AM-6PM EST. How can we help?", active: true },
  { id: "2", triggerType: "keyword", triggerValue: "PRICING", response: "Check out our pricing at https://example.com/pricing. Reply SALES to speak with a rep!", active: true },
  { id: "3", triggerType: "keyword", triggerValue: "HELP", response: "Available commands: HOURS, PRICING, STATUS, STOP. Reply with any keyword for more info.", active: true },
  { id: "4", triggerType: "regex", triggerValue: "order\\s*#?\\d+", response: "I found your order! Let me look up the details. One moment...", active: false },
  { id: "5", triggerType: "keyword", triggerValue: "STATUS", response: "All systems operational. Current response time: <1 minute. Visit status.example.com for details.", active: true },
];

const initialSequences: DripSequence[] = [
  {
    id: "1",
    name: "Welcome Series",
    trigger: "New Contact Added",
    steps: [
      { delayMinutes: 0, message: "Welcome to {{company}}! We're glad you joined." },
      { delayMinutes: 1440, message: "Did you know? You can reply to this number anytime for support." },
      { delayMinutes: 4320, message: "Here's a special offer just for new members: 15% off with code WELCOME15!" },
    ],
    active: true,
    enrollmentCount: 1247,
  },
  {
    id: "2",
    name: "Re-engagement",
    trigger: "No Reply in 30 Days",
    steps: [
      { delayMinutes: 0, message: "Hey {{first_name}}, we haven't heard from you in a while!" },
      { delayMinutes: 2880, message: "We miss you! Here's an exclusive 20% discount: COMEBACK20" },
      { delayMinutes: 7200, message: "Last chance! Your 20% discount expires tomorrow. Don't miss out!" },
    ],
    active: true,
    enrollmentCount: 583,
  },
  {
    id: "3",
    name: "Post-Purchase Follow-up",
    trigger: "Purchase Completed",
    steps: [
      { delayMinutes: 60, message: "Thanks for your purchase! Your order is being processed." },
      { delayMinutes: 10080, message: "How was your experience? Reply 1-5 to rate us!" },
    ],
    active: false,
    enrollmentCount: 2891,
  },
  {
    id: "4",
    name: "Appointment Reminder Sequence",
    trigger: "Appointment Booked",
    steps: [
      { delayMinutes: 0, message: "Your appointment is confirmed for {{custom_1}}. We'll send a reminder!" },
      { delayMinutes: -1440, message: "Reminder: Your appointment is tomorrow at {{custom_1}}. Reply C to confirm." },
      { delayMinutes: -60, message: "Your appointment starts in 1 hour. See you soon!" },
    ],
    active: true,
    enrollmentCount: 456,
  },
];

type Tab = "auto-replies" | "drip-sequences";

const triggerTypes = [
  { value: "keyword", label: "Keyword Match" },
  { value: "regex", label: "Regex Pattern" },
  { value: "all", label: "All Messages" },
];

const inputClass =
  "w-full px-4 py-3 bg-white/5 border border-white/10 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50 transition-all";

export default function Automations() {
  const [activeTab, setActiveTab] = useState<Tab>("auto-replies");
  const [autoReplies, setAutoReplies] = useState<AutoReply[]>(initialAutoReplies);
  const [sequences, setSequences] = useState<DripSequence[]>(initialSequences);

  // Auto-reply modal
  const [showReplyModal, setShowReplyModal] = useState(false);
  const [editingReply, setEditingReply] = useState<AutoReply | null>(null);
  const [newReply, setNewReply] = useState<Omit<AutoReply, "id" | "active">>({
    triggerType: "keyword",
    triggerValue: "",
    response: "",
  });

  // Drip sequence modal
  const [showSequenceModal, setShowSequenceModal] = useState(false);
  const [editingSequence, setEditingSequence] = useState<DripSequence | null>(null);
  const [newSequence, setNewSequence] = useState({
    name: "",
    trigger: "",
    steps: [{ delayMinutes: 0, message: "" }] as DripStep[],
  });

  const toggleAutoReply = (id: string) => {
    setAutoReplies((prev) => prev.map((r) => (r.id === id ? { ...r, active: !r.active } : r)));
  };

  const toggleSequence = (id: string) => {
    setSequences((prev) => prev.map((s) => (s.id === id ? { ...s, active: !s.active } : s)));
  };

  const openCreateReply = () => {
    setEditingReply(null);
    setNewReply({ triggerType: "keyword", triggerValue: "", response: "" });
    setShowReplyModal(true);
  };

  const openEditReply = (reply: AutoReply) => {
    setEditingReply(reply);
    setNewReply({ triggerType: reply.triggerType, triggerValue: reply.triggerValue, response: reply.response });
    setShowReplyModal(true);
  };

  const saveReply = () => {
    if (!newReply.triggerValue.trim() || !newReply.response.trim()) {
      toast.error("Trigger and response are required");
      return;
    }
    if (editingReply) {
      setAutoReplies((prev) =>
        prev.map((r) => (r.id === editingReply.id ? { ...r, ...newReply } : r))
      );
      toast.success("Auto-reply updated!");
    } else {
      setAutoReplies((prev) => [
        { id: String(Date.now()), ...newReply, active: true },
        ...prev,
      ]);
      toast.success("Auto-reply created!");
    }
    setShowReplyModal(false);
  };

  const deleteReply = (id: string) => {
    setAutoReplies((prev) => prev.filter((r) => r.id !== id));
    toast.success("Auto-reply deleted");
  };

  const openCreateSequence = () => {
    setEditingSequence(null);
    setNewSequence({ name: "", trigger: "", steps: [{ delayMinutes: 0, message: "" }] });
    setShowSequenceModal(true);
  };

  const openEditSequence = (seq: DripSequence) => {
    setEditingSequence(seq);
    setNewSequence({ name: seq.name, trigger: seq.trigger, steps: [...seq.steps] });
    setShowSequenceModal(true);
  };

  const addStep = () => {
    setNewSequence((p) => ({ ...p, steps: [...p.steps, { delayMinutes: 1440, message: "" }] }));
  };

  const removeStep = (index: number) => {
    setNewSequence((p) => ({ ...p, steps: p.steps.filter((_, i) => i !== index) }));
  };

  const updateStep = (index: number, field: keyof DripStep, value: string | number) => {
    setNewSequence((p) => ({
      ...p,
      steps: p.steps.map((s, i) => (i === index ? { ...s, [field]: value } : s)),
    }));
  };

  const saveSequence = () => {
    if (!newSequence.name.trim() || !newSequence.trigger.trim()) {
      toast.error("Name and trigger are required");
      return;
    }
    if (editingSequence) {
      setSequences((prev) =>
        prev.map((s) => (s.id === editingSequence.id ? { ...s, ...newSequence } : s))
      );
      toast.success("Sequence updated!");
    } else {
      setSequences((prev) => [
        { id: String(Date.now()), ...newSequence, active: false, enrollmentCount: 0 },
        ...prev,
      ]);
      toast.success("Sequence created!");
    }
    setShowSequenceModal(false);
  };

  const formatDelay = (minutes: number) => {
    if (minutes === 0) return "Immediately";
    if (minutes < 0) return `${Math.abs(minutes / 60)}h before`;
    if (minutes < 60) return `${minutes}m`;
    if (minutes < 1440) return `${minutes / 60}h`;
    return `${minutes / 1440}d`;
  };

  const autoReplyColumns = [
    {
      key: "triggerType",
      label: "Trigger Type",
      sortable: true,
      render: (row: AutoReply) => {
        const typeConfig: Record<string, { bg: string; text: string }> = {
          keyword: { bg: "bg-blue-500/20", text: "text-blue-400" },
          regex: { bg: "bg-purple-500/20", text: "text-purple-400" },
          all: { bg: "bg-amber-500/20", text: "text-amber-400" },
        };
        const config = typeConfig[row.triggerType] || typeConfig.keyword;
        return (
          <span className={clsx("px-2.5 py-1 rounded-full text-xs font-medium", config.bg, config.text)}>
            {row.triggerType === "regex" ? "Regex" : row.triggerType === "all" ? "All" : "Keyword"}
          </span>
        );
      },
    },
    {
      key: "triggerValue",
      label: "Trigger",
      sortable: true,
      render: (row: AutoReply) => (
        <span className="font-mono text-sm text-white bg-white/5 px-2 py-0.5 rounded">{row.triggerValue}</span>
      ),
    },
    {
      key: "response",
      label: "Response",
      render: (row: AutoReply) => (
        <span className="text-gray-400 text-sm line-clamp-1 max-w-xs">{row.response}</span>
      ),
    },
    {
      key: "active",
      label: "Status",
      render: (row: AutoReply) => (
        <button onClick={() => toggleAutoReply(row.id)} className="flex-shrink-0">
          {row.active ? (
            <ToggleRight className="w-7 h-7 text-blue-400" />
          ) : (
            <ToggleLeft className="w-7 h-7 text-gray-600" />
          )}
        </button>
      ),
    },
    {
      key: "actions",
      label: "",
      render: (row: AutoReply) => (
        <div className="flex gap-1">
          <button onClick={() => openEditReply(row)} className="p-1.5 text-gray-500 hover:text-blue-400 transition-colors">
            <ChevronRight className="w-4 h-4" />
          </button>
          <button onClick={() => deleteReply(row.id)} className="p-1.5 text-gray-500 hover:text-rose-400 transition-colors">
            <Trash2 className="w-4 h-4" />
          </button>
        </div>
      ),
    },
  ];

  return (
    <motion.div variants={container} initial="hidden" animate="show">
      {/* Header */}
      <motion.div variants={item} className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-8">
        <div>
          <h1 className="text-3xl font-bold text-white">Automations</h1>
          <p className="text-gray-400 mt-1">Set up auto-replies and drip sequences.</p>
        </div>
        <motion.button
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          onClick={activeTab === "auto-replies" ? openCreateReply : openCreateSequence}
          className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl font-semibold text-sm text-white bg-gradient-to-r from-blue-500 to-indigo-600 hover:from-blue-600 hover:to-indigo-700 shadow-lg shadow-blue-500/25 transition-all"
        >
          <Plus className="w-4 h-4" />
          {activeTab === "auto-replies" ? "New Auto-Reply" : "New Sequence"}
        </motion.button>
      </motion.div>

      {/* Tab Switcher */}
      <motion.div variants={item} className="mb-6">
        <div className="flex gap-1 bg-white/5 rounded-xl p-1 border border-white/10 w-fit">
          {([
            { key: "auto-replies" as Tab, label: "Auto-Replies", icon: MessageSquare },
            { key: "drip-sequences" as Tab, label: "Drip Sequences", icon: Layers },
          ]).map((tab) => {
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
                    layoutId="auto-tab"
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

      {/* Content */}
      {activeTab === "auto-replies" ? (
        <motion.div variants={item}>
          <GlassCard>
            <DataTable data={autoReplies} columns={autoReplyColumns} searchable pageSize={10} />
          </GlassCard>
        </motion.div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {sequences.map((seq) => (
            <motion.div key={seq.id} variants={item}>
              <GlassCard hover className="cursor-pointer" >
                <div onClick={() => openEditSequence(seq)}>
                  <div className="flex items-start justify-between mb-4">
                    <div>
                      <h4 className="text-white font-semibold">{seq.name}</h4>
                      <p className="text-xs text-gray-500 mt-0.5">{seq.trigger}</p>
                    </div>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        toggleSequence(seq.id);
                      }}
                    >
                      {seq.active ? (
                        <ToggleRight className="w-7 h-7 text-blue-400" />
                      ) : (
                        <ToggleLeft className="w-7 h-7 text-gray-600" />
                      )}
                    </button>
                  </div>

                  {/* Steps visualization */}
                  <div className="space-y-2 mb-4">
                    {seq.steps.map((step, i) => (
                      <div key={i} className="flex items-center gap-3">
                        <div className="flex flex-col items-center">
                          <div className={clsx("w-3 h-3 rounded-full border-2", seq.active ? "border-blue-500 bg-blue-500/30" : "border-gray-600 bg-gray-600/30")} />
                          {i < seq.steps.length - 1 && <div className={clsx("w-0.5 h-4", seq.active ? "bg-blue-500/30" : "bg-gray-600/30")} />}
                        </div>
                        <div className="flex-1 bg-white/5 rounded-lg p-2 text-xs">
                          <span className={clsx("font-medium mr-2", seq.active ? "text-blue-400" : "text-gray-500")}>
                            {formatDelay(step.delayMinutes)}
                          </span>
                          <span className="text-gray-400 line-clamp-1">{step.message}</span>
                        </div>
                      </div>
                    ))}
                  </div>

                  <div className="flex items-center justify-between pt-3 border-t border-white/5">
                    <div className="flex items-center gap-4 text-xs text-gray-500">
                      <span className="flex items-center gap-1">
                        <Hash className="w-3.5 h-3.5" />
                        {seq.steps.length} steps
                      </span>
                      <span className="flex items-center gap-1">
                        <Users className="w-3.5 h-3.5" />
                        {seq.enrollmentCount.toLocaleString()} enrolled
                      </span>
                    </div>
                    <span className={clsx("text-xs font-medium", seq.active ? "text-emerald-400" : "text-gray-500")}>
                      {seq.active ? "Active" : "Paused"}
                    </span>
                  </div>
                </div>
              </GlassCard>
            </motion.div>
          ))}
        </div>
      )}

      {/* Auto-Reply Modal */}
      <AnimatePresence>
        {showReplyModal && (
          <>
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={() => setShowReplyModal(false)} className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50" />
            <motion.div initial={{ opacity: 0, scale: 0.95, y: 20 }} animate={{ opacity: 1, scale: 1, y: 0 }} exit={{ opacity: 0, scale: 0.95, y: 20 }} className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-full max-w-lg z-50">
              <div className="bg-navy-900/95 backdrop-blur-xl border border-white/10 rounded-2xl shadow-2xl p-6">
                <div className="flex items-center justify-between mb-6">
                  <h3 className="text-lg font-semibold text-white">
                    {editingReply ? "Edit Auto-Reply" : "New Auto-Reply"}
                  </h3>
                  <button onClick={() => setShowReplyModal(false)} className="text-gray-500 hover:text-white">
                    <X className="w-5 h-5" />
                  </button>
                </div>
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-1.5">Trigger Type</label>
                    <select
                      value={newReply.triggerType}
                      onChange={(e) => setNewReply((p) => ({ ...p, triggerType: e.target.value as AutoReply["triggerType"] }))}
                      className={inputClass}
                    >
                      {triggerTypes.map((t) => (
                        <option key={t.value} value={t.value} className="bg-navy-900">{t.label}</option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-1.5">Trigger Value</label>
                    <input
                      value={newReply.triggerValue}
                      onChange={(e) => setNewReply((p) => ({ ...p, triggerValue: e.target.value }))}
                      placeholder={newReply.triggerType === "regex" ? "e.g. order\\s*#?\\d+" : "e.g. HELP"}
                      className={clsx(inputClass, newReply.triggerType === "regex" && "font-mono")}
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-1.5">Response</label>
                    <textarea
                      value={newReply.response}
                      onChange={(e) => setNewReply((p) => ({ ...p, response: e.target.value }))}
                      rows={4}
                      placeholder="The message to send back..."
                      className={clsx(inputClass, "resize-none")}
                    />
                  </div>
                </div>
                <div className="flex justify-end gap-3 mt-6">
                  <button onClick={() => setShowReplyModal(false)} className="px-4 py-2.5 rounded-xl text-sm text-gray-400 hover:text-white bg-white/5 hover:bg-white/10 border border-white/10 transition-all">Cancel</button>
                  <motion.button whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }} onClick={saveReply} className="px-5 py-2.5 rounded-xl font-semibold text-sm text-white bg-gradient-to-r from-blue-500 to-indigo-600 shadow-lg shadow-blue-500/25 transition-all">
                    {editingReply ? "Save Changes" : "Create"}
                  </motion.button>
                </div>
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>

      {/* Drip Sequence Modal */}
      <AnimatePresence>
        {showSequenceModal && (
          <>
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={() => setShowSequenceModal(false)} className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50" />
            <motion.div initial={{ opacity: 0, scale: 0.95, y: 20 }} animate={{ opacity: 1, scale: 1, y: 0 }} exit={{ opacity: 0, scale: 0.95, y: 20 }} className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-full max-w-2xl z-50 max-h-[85vh] overflow-y-auto">
              <div className="bg-navy-900/95 backdrop-blur-xl border border-white/10 rounded-2xl shadow-2xl p-6">
                <div className="flex items-center justify-between mb-6">
                  <h3 className="text-lg font-semibold text-white">
                    {editingSequence ? "Edit Sequence" : "New Drip Sequence"}
                  </h3>
                  <button onClick={() => setShowSequenceModal(false)} className="text-gray-500 hover:text-white">
                    <X className="w-5 h-5" />
                  </button>
                </div>
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-1.5">Sequence Name</label>
                    <input
                      value={newSequence.name}
                      onChange={(e) => setNewSequence((p) => ({ ...p, name: e.target.value }))}
                      placeholder="e.g. Welcome Series"
                      className={inputClass}
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-1.5">Trigger Event</label>
                    <input
                      value={newSequence.trigger}
                      onChange={(e) => setNewSequence((p) => ({ ...p, trigger: e.target.value }))}
                      placeholder="e.g. New Contact Added"
                      className={inputClass}
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-3">Steps</label>
                    <div className="space-y-3">
                      {newSequence.steps.map((step, i) => (
                        <motion.div
                          key={i}
                          initial={{ opacity: 0, y: 10 }}
                          animate={{ opacity: 1, y: 0 }}
                          className="bg-white/5 rounded-xl p-4 space-y-3"
                        >
                          <div className="flex items-center justify-between">
                            <span className="text-xs font-medium text-blue-400">Step {i + 1}</span>
                            {newSequence.steps.length > 1 && (
                              <button onClick={() => removeStep(i)} className="text-gray-500 hover:text-rose-400">
                                <Trash2 className="w-3.5 h-3.5" />
                              </button>
                            )}
                          </div>
                          <div className="flex items-center gap-3">
                            <div className="flex items-center gap-2 flex-shrink-0">
                              <Clock className="w-4 h-4 text-gray-500" />
                              <span className="text-xs text-gray-400">Delay:</span>
                            </div>
                            <input
                              type="number"
                              value={step.delayMinutes}
                              onChange={(e) => updateStep(i, "delayMinutes", parseInt(e.target.value) || 0)}
                              className="w-24 px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-sm text-white font-mono focus:outline-none focus:ring-2 focus:ring-blue-500/50"
                            />
                            <span className="text-xs text-gray-500">minutes</span>
                          </div>
                          <textarea
                            value={step.message}
                            onChange={(e) => updateStep(i, "message", e.target.value)}
                            rows={2}
                            placeholder="Message content..."
                            className={clsx(inputClass, "resize-none text-sm")}
                          />
                        </motion.div>
                      ))}
                    </div>
                    <button
                      onClick={addStep}
                      className="mt-3 inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium text-blue-400 bg-blue-500/10 hover:bg-blue-500/20 border border-blue-500/20 transition-all"
                    >
                      <Plus className="w-4 h-4" />
                      Add Step
                    </button>
                  </div>
                </div>
                <div className="flex justify-end gap-3 mt-6">
                  <button onClick={() => setShowSequenceModal(false)} className="px-4 py-2.5 rounded-xl text-sm text-gray-400 hover:text-white bg-white/5 hover:bg-white/10 border border-white/10 transition-all">Cancel</button>
                  <motion.button whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }} onClick={saveSequence} className="px-5 py-2.5 rounded-xl font-semibold text-sm text-white bg-gradient-to-r from-blue-500 to-indigo-600 shadow-lg shadow-blue-500/25 transition-all">
                    {editingSequence ? "Save Changes" : "Create Sequence"}
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
