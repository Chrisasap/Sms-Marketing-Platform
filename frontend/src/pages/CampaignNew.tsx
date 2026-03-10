import { useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useNavigate } from "react-router-dom";
import { useMutation } from "@tanstack/react-query";
import {
  ChevronLeft,
  ChevronRight,
  Megaphone,
  Zap,
  GitBranch,
  Repeat,
  Users,
  MessageSquare,
  Clock,
  CheckCircle2,
  Upload,
  Calendar,
  Globe,
  Sparkles,
  Rocket,
  X,
} from "lucide-react";
import clsx from "clsx";
import toast from "react-hot-toast";
import GlassCard from "../components/ui/GlassCard";
import PhoneMockup from "../components/ui/PhoneMockup";
import api from "../lib/api";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

type CampaignType = "blast" | "drip" | "triggered" | "ab";
type ScheduleMode = "now" | "scheduled";

interface WizardState {
  name: string;
  type: CampaignType;
  targetLists: string[];
  excludeLists: string[];
  message: string;
  mediaUrl: string | null;
  scheduleMode: ScheduleMode;
  scheduledAt: string;
  sendWindowStart: string;
  sendWindowEnd: string;
  timezone: string;
}

/* ------------------------------------------------------------------ */
/*  Constants                                                          */
/* ------------------------------------------------------------------ */

const steps = [
  { label: "Details", icon: Megaphone },
  { label: "Audience", icon: Users },
  { label: "Message", icon: MessageSquare },
  { label: "Schedule", icon: Clock },
  { label: "Review", icon: CheckCircle2 },
];

const campaignTypes: { key: CampaignType; label: string; desc: string; icon: typeof Megaphone }[] = [
  { key: "blast", label: "Blast", desc: "Send to all contacts at once", icon: Megaphone },
  { key: "drip", label: "Drip", desc: "Automated sequence over time", icon: Repeat },
  { key: "triggered", label: "Triggered", desc: "Send based on events", icon: Zap },
  { key: "ab", label: "A/B Test", desc: "Test message variants", icon: GitBranch },
];

const mergeTags = [
  "{{first_name}}",
  "{{last_name}}",
  "{{phone}}",
  "{{company}}",
  "{{custom_1}}",
];

const sampleLists = [
  { id: "l1", name: "All Subscribers", count: 12840 },
  { id: "l2", name: "VIP Customers", count: 1320 },
  { id: "l3", name: "New Signups (30d)", count: 2450 },
  { id: "l4", name: "Re-engagement", count: 870 },
  { id: "l5", name: "Event Attendees", count: 560 },
];

const timezones = [
  "America/New_York",
  "America/Chicago",
  "America/Denver",
  "America/Los_Angeles",
  "America/Phoenix",
  "America/Anchorage",
  "Pacific/Honolulu",
  "UTC",
];

const defaultState: WizardState = {
  name: "",
  type: "blast",
  targetLists: [],
  excludeLists: [],
  message: "",
  mediaUrl: null,
  scheduleMode: "now",
  scheduledAt: "",
  sendWindowStart: "09:00",
  sendWindowEnd: "21:00",
  timezone: "America/New_York",
};

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

function getSegmentCount(text: string): { chars: number; segments: number } {
  const chars = text.length;
  if (chars === 0) return { chars: 0, segments: 0 };
  const segments = chars <= 160 ? 1 : Math.ceil(chars / 153);
  return { chars, segments };
}

/* ------------------------------------------------------------------ */
/*  Confetti burst (lightweight CSS animation)                         */
/* ------------------------------------------------------------------ */

function ConfettiBurst() {
  const colors = ["#3b82f6", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6", "#06b6d4"];
  const particles = Array.from({ length: 50 }, (_, i) => ({
    id: i,
    x: (Math.random() - 0.5) * 600,
    y: -(Math.random() * 500 + 200),
    r: Math.random() * 360,
    color: colors[i % colors.length],
    size: Math.random() * 8 + 4,
    delay: Math.random() * 0.3,
  }));
  return (
    <div className="fixed inset-0 pointer-events-none z-50 overflow-hidden">
      {particles.map((p) => (
        <motion.div
          key={p.id}
          initial={{ x: "50vw", y: "50vh", opacity: 1, rotate: 0, scale: 1 }}
          animate={{ x: `calc(50vw + ${p.x}px)`, y: `calc(50vh + ${p.y}px)`, opacity: 0, rotate: p.r, scale: 0 }}
          transition={{ duration: 2, delay: p.delay, ease: "easeOut" }}
          style={{ width: p.size, height: p.size, backgroundColor: p.color }}
          className="absolute rounded-sm"
        />
      ))}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Step Components                                                    */
/* ------------------------------------------------------------------ */

function StepDetails({
  state,
  onChange,
}: {
  state: WizardState;
  onChange: (p: Partial<WizardState>) => void;
}) {
  return (
    <div className="space-y-8">
      {/* Campaign Name */}
      <div>
        <label className="block text-sm font-medium text-gray-300 mb-2">Campaign Name</label>
        <input
          type="text"
          value={state.name}
          onChange={(e) => onChange({ name: e.target.value })}
          placeholder="e.g. Spring Sale Blast"
          className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500/50 text-sm"
        />
      </div>

      {/* Campaign Type */}
      <div>
        <label className="block text-sm font-medium text-gray-300 mb-3">Campaign Type</label>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {campaignTypes.map((ct) => {
            const isActive = state.type === ct.key;
            const Icon = ct.icon;
            return (
              <motion.button
                key={ct.key}
                whileHover={{ scale: 1.03 }}
                whileTap={{ scale: 0.97 }}
                onClick={() => onChange({ type: ct.key })}
                className={clsx(
                  "relative p-5 rounded-2xl border text-left transition-all",
                  isActive
                    ? "bg-blue-500/10 border-blue-500/50 shadow-lg shadow-blue-500/10"
                    : "bg-white/5 border-white/10 hover:border-white/20"
                )}
              >
                {isActive && (
                  <motion.div
                    layoutId="type-active"
                    className="absolute inset-0 rounded-2xl ring-2 ring-blue-500/50"
                    transition={{ type: "spring", stiffness: 300, damping: 25 }}
                  />
                )}
                <div className={clsx(
                  "w-10 h-10 rounded-xl flex items-center justify-center mb-3",
                  isActive ? "bg-blue-500/20" : "bg-white/5"
                )}>
                  <Icon className={clsx("w-5 h-5", isActive ? "text-blue-400" : "text-gray-400")} />
                </div>
                <p className={clsx("font-semibold text-sm", isActive ? "text-white" : "text-gray-300")}>{ct.label}</p>
                <p className="text-xs text-gray-500 mt-1">{ct.desc}</p>
              </motion.button>
            );
          })}
        </div>
      </div>
    </div>
  );
}

function StepAudience({
  state,
  onChange,
}: {
  state: WizardState;
  onChange: (p: Partial<WizardState>) => void;
}) {
  const toggleList = (id: string, field: "targetLists" | "excludeLists") => {
    const current = state[field];
    const updated = current.includes(id) ? current.filter((x) => x !== id) : [...current, id];
    onChange({ [field]: updated });
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
      {/* Target Lists */}
      <div>
        <label className="block text-sm font-medium text-gray-300 mb-3">Target Lists</label>
        <div className="space-y-2">
          {sampleLists.map((list) => {
            const checked = state.targetLists.includes(list.id);
            return (
              <motion.label
                key={list.id}
                whileHover={{ x: 2 }}
                className={clsx(
                  "flex items-center gap-3 p-3 rounded-xl border cursor-pointer transition-all",
                  checked
                    ? "bg-blue-500/10 border-blue-500/40"
                    : "bg-white/5 border-white/10 hover:border-white/20"
                )}
              >
                <input
                  type="checkbox"
                  checked={checked}
                  onChange={() => toggleList(list.id, "targetLists")}
                  className="w-4 h-4 rounded border-gray-600 text-blue-500 focus:ring-blue-500/50 bg-white/10"
                />
                <div className="flex-1">
                  <p className="text-sm text-white font-medium">{list.name}</p>
                  <p className="text-xs text-gray-500">{list.count.toLocaleString()} contacts</p>
                </div>
                {checked && (
                  <motion.div
                    initial={{ scale: 0 }}
                    animate={{ scale: 1 }}
                    className="w-6 h-6 rounded-full bg-blue-500/20 flex items-center justify-center"
                  >
                    <CheckCircle2 className="w-4 h-4 text-blue-400" />
                  </motion.div>
                )}
              </motion.label>
            );
          })}
        </div>
      </div>

      {/* Exclude Lists */}
      <div>
        <label className="block text-sm font-medium text-gray-300 mb-3">Exclude Lists</label>
        <div className="space-y-2">
          {sampleLists.map((list) => {
            const checked = state.excludeLists.includes(list.id);
            return (
              <motion.label
                key={list.id}
                whileHover={{ x: 2 }}
                className={clsx(
                  "flex items-center gap-3 p-3 rounded-xl border cursor-pointer transition-all",
                  checked
                    ? "bg-rose-500/10 border-rose-500/40"
                    : "bg-white/5 border-white/10 hover:border-white/20"
                )}
              >
                <input
                  type="checkbox"
                  checked={checked}
                  onChange={() => toggleList(list.id, "excludeLists")}
                  className="w-4 h-4 rounded border-gray-600 text-rose-500 focus:ring-rose-500/50 bg-white/10"
                />
                <div className="flex-1">
                  <p className="text-sm text-white font-medium">{list.name}</p>
                  <p className="text-xs text-gray-500">{list.count.toLocaleString()} contacts</p>
                </div>
                {checked && (
                  <motion.div
                    initial={{ scale: 0 }}
                    animate={{ scale: 1 }}
                    className="w-6 h-6 rounded-full bg-rose-500/20 flex items-center justify-center"
                  >
                    <X className="w-4 h-4 text-rose-400" />
                  </motion.div>
                )}
              </motion.label>
            );
          })}
        </div>
      </div>
    </div>
  );
}

function StepMessage({
  state,
  onChange,
}: {
  state: WizardState;
  onChange: (p: Partial<WizardState>) => void;
}) {
  const { chars, segments } = getSegmentCount(state.message);

  const insertTag = (tag: string) => {
    onChange({ message: state.message + tag });
  };

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      const file = e.dataTransfer.files?.[0];
      if (file && file.type.startsWith("image/")) {
        const url = URL.createObjectURL(file);
        onChange({ mediaUrl: url });
      }
    },
    [onChange]
  );

  const previewMessage = state.message
    .replace(/\{\{first_name\}\}/g, "Sarah")
    .replace(/\{\{last_name\}\}/g, "Johnson")
    .replace(/\{\{phone\}\}/g, "(555) 123-4567")
    .replace(/\{\{company\}\}/g, "Acme Inc")
    .replace(/\{\{custom_1\}\}/g, "VIP");

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
      {/* Composer */}
      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">Message Body</label>
          <div className="relative">
            <textarea
              value={state.message}
              onChange={(e) => onChange({ message: e.target.value })}
              placeholder="Type your message here..."
              rows={8}
              className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500/50 text-sm resize-none"
            />
            {/* Character / Segment counter */}
            <div className="absolute bottom-3 right-3 flex items-center gap-3">
              <span className={clsx("text-xs font-mono", chars > 1600 ? "text-rose-400" : "text-gray-500")}>
                {chars}/1600
              </span>
              <span className="text-xs font-mono text-gray-500">
                {segments} {segments === 1 ? "segment" : "segments"}
              </span>
            </div>
          </div>
        </div>

        {/* Merge Tags */}
        <div>
          <label className="block text-xs font-medium text-gray-400 mb-2">Merge Tags</label>
          <div className="flex flex-wrap gap-2">
            {mergeTags.map((tag) => (
              <motion.button
                key={tag}
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={() => insertTag(tag)}
                className="px-3 py-1.5 bg-white/5 border border-white/10 rounded-lg text-xs text-blue-400 hover:bg-blue-500/10 hover:border-blue-500/30 transition-colors font-mono"
              >
                {tag}
              </motion.button>
            ))}
          </div>
        </div>

        {/* MMS Media Upload */}
        <div>
          <label className="block text-xs font-medium text-gray-400 mb-2">MMS Media (optional)</label>
          {state.mediaUrl ? (
            <div className="relative group w-fit">
              <img
                src={state.mediaUrl}
                alt="Media preview"
                className="w-32 h-32 object-cover rounded-xl border border-white/10"
              />
              <button
                onClick={() => onChange({ mediaUrl: null })}
                className="absolute -top-2 -right-2 w-6 h-6 bg-rose-500 rounded-full flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity"
              >
                <X className="w-3 h-3 text-white" />
              </button>
            </div>
          ) : (
            <div
              onDragOver={(e) => e.preventDefault()}
              onDrop={handleDrop}
              onClick={() => {
                const input = document.createElement("input");
                input.type = "file";
                input.accept = "image/*";
                input.onchange = (e: any) => {
                  const file = e.target.files?.[0];
                  if (file) onChange({ mediaUrl: URL.createObjectURL(file) });
                };
                input.click();
              }}
              className="border-2 border-dashed border-white/10 rounded-xl p-8 flex flex-col items-center gap-3 cursor-pointer hover:border-blue-500/30 hover:bg-blue-500/5 transition-all"
            >
              <motion.div
                animate={{ y: [0, -5, 0] }}
                transition={{ repeat: Infinity, duration: 2 }}
              >
                <Upload className="w-8 h-8 text-gray-500" />
              </motion.div>
              <p className="text-sm text-gray-500">
                Drag & drop an image, or <span className="text-blue-400">click to browse</span>
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Phone Preview */}
      <div className="flex justify-center">
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-3 text-center">Live Preview</label>
          <PhoneMockup
            messages={
              previewMessage
                ? [
                    ...(state.mediaUrl
                      ? [{ text: "[ MMS Image Attached ]", from: "sender" as const, time: "Now" }]
                      : []),
                    { text: previewMessage || "Your message will appear here...", from: "sender" as const, time: "Now" },
                  ]
                : [{ text: "Your message will appear here...", from: "sender" as const, time: "Now" }]
            }
          />
        </div>
      </div>
    </div>
  );
}

function StepSchedule({
  state,
  onChange,
}: {
  state: WizardState;
  onChange: (p: Partial<WizardState>) => void;
}) {
  return (
    <div className="max-w-xl mx-auto space-y-8">
      {/* Send Mode */}
      <div>
        <label className="block text-sm font-medium text-gray-300 mb-3">When to Send</label>
        <div className="grid grid-cols-2 gap-4">
          {(["now", "scheduled"] as const).map((mode) => (
            <motion.button
              key={mode}
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={() => onChange({ scheduleMode: mode })}
              className={clsx(
                "p-5 rounded-2xl border text-center transition-all",
                state.scheduleMode === mode
                  ? "bg-blue-500/10 border-blue-500/50"
                  : "bg-white/5 border-white/10 hover:border-white/20"
              )}
            >
              {mode === "now" ? (
                <Rocket className={clsx("w-8 h-8 mx-auto mb-2", state.scheduleMode === mode ? "text-blue-400" : "text-gray-500")} />
              ) : (
                <Calendar className={clsx("w-8 h-8 mx-auto mb-2", state.scheduleMode === mode ? "text-blue-400" : "text-gray-500")} />
              )}
              <p className={clsx("font-semibold text-sm", state.scheduleMode === mode ? "text-white" : "text-gray-400")}>
                {mode === "now" ? "Send Now" : "Schedule"}
              </p>
            </motion.button>
          ))}
        </div>
      </div>

      {/* Scheduled DateTime */}
      <AnimatePresence>
        {state.scheduleMode === "scheduled" && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="overflow-hidden"
          >
            <div className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-gray-400 mb-2">Date & Time</label>
                <input
                  type="datetime-local"
                  value={state.scheduledAt}
                  onChange={(e) => onChange({ scheduledAt: e.target.value })}
                  className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-xl text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500/50 [color-scheme:dark]"
                />
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Send Window */}
      <div>
        <label className="block text-sm font-medium text-gray-300 mb-3">Send Window</label>
        <p className="text-xs text-gray-500 mb-3">Only send messages during these hours (respects contact's timezone).</p>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-xs text-gray-400 mb-1">Start</label>
            <input
              type="time"
              value={state.sendWindowStart}
              onChange={(e) => onChange({ sendWindowStart: e.target.value })}
              className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-xl text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/50 [color-scheme:dark]"
            />
          </div>
          <div>
            <label className="block text-xs text-gray-400 mb-1">End</label>
            <input
              type="time"
              value={state.sendWindowEnd}
              onChange={(e) => onChange({ sendWindowEnd: e.target.value })}
              className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-xl text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/50 [color-scheme:dark]"
            />
          </div>
        </div>
      </div>

      {/* Timezone */}
      <div>
        <label className="block text-sm font-medium text-gray-300 mb-2">
          <Globe className="w-4 h-4 inline mr-1" /> Timezone
        </label>
        <select
          value={state.timezone}
          onChange={(e) => onChange({ timezone: e.target.value })}
          className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-xl text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/50 [color-scheme:dark]"
        >
          {timezones.map((tz) => (
            <option key={tz} value={tz} className="bg-gray-900">
              {tz}
            </option>
          ))}
        </select>
      </div>
    </div>
  );
}

function StepReview({ state }: { state: WizardState }) {
  const totalRecipients = sampleLists
    .filter((l) => state.targetLists.includes(l.id))
    .reduce((sum, l) => sum + l.count, 0);
  const excludeCount = sampleLists
    .filter((l) => state.excludeLists.includes(l.id))
    .reduce((sum, l) => sum + l.count, 0);

  const rows = [
    { label: "Campaign Name", value: state.name || "Untitled" },
    { label: "Type", value: campaignTypes.find((t) => t.key === state.type)?.label },
    { label: "Target Lists", value: `${state.targetLists.length} list(s) - ~${totalRecipients.toLocaleString()} contacts` },
    { label: "Exclude Lists", value: state.excludeLists.length > 0 ? `${state.excludeLists.length} list(s) - ~${excludeCount.toLocaleString()} contacts` : "None" },
    { label: "Message", value: state.message.slice(0, 100) + (state.message.length > 100 ? "..." : "") || "No message" },
    { label: "Media", value: state.mediaUrl ? "1 image attached" : "None" },
    { label: "Schedule", value: state.scheduleMode === "now" ? "Send immediately" : state.scheduledAt || "Not set" },
    { label: "Send Window", value: `${state.sendWindowStart} - ${state.sendWindowEnd}` },
    { label: "Timezone", value: state.timezone },
  ];

  return (
    <div className="max-w-2xl mx-auto">
      <div className="text-center mb-8">
        <motion.div
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          transition={{ type: "spring", stiffness: 300, damping: 20 }}
          className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center"
        >
          <Sparkles className="w-8 h-8 text-white" />
        </motion.div>
        <h3 className="text-xl font-bold text-white">Review Your Campaign</h3>
        <p className="text-sm text-gray-400 mt-1">Double-check everything before launching.</p>
      </div>

      <GlassCard>
        <div className="divide-y divide-white/5">
          {rows.map((row, i) => (
            <motion.div
              key={row.label}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.05 }}
              className="flex items-start justify-between py-3"
            >
              <span className="text-sm text-gray-400">{row.label}</span>
              <span className="text-sm text-white font-medium text-right max-w-[60%]">{row.value}</span>
            </motion.div>
          ))}
        </div>
      </GlassCard>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Main Wizard Component                                              */
/* ------------------------------------------------------------------ */

export default function CampaignNew() {
  const [step, setStep] = useState(0);
  const [state, setState] = useState<WizardState>(defaultState);
  const [showConfetti, setShowConfetti] = useState(false);
  const navigate = useNavigate();

  const update = (partial: Partial<WizardState>) =>
    setState((prev) => ({ ...prev, ...partial }));

  const createMutation = useMutation({
    mutationFn: async () => {
      const res = await api.post("/campaigns/", state);
      return res.data;
    },
    onSuccess: () => {
      setShowConfetti(true);
      toast.success("Campaign launched successfully!");
      setTimeout(() => navigate("/campaigns"), 3000);
    },
    onError: () => {
      toast.error("Failed to launch campaign. Please try again.");
    },
  });

  const canNext = () => {
    switch (step) {
      case 0:
        return state.name.trim().length > 0;
      case 1:
        return state.targetLists.length > 0;
      case 2:
        return state.message.trim().length > 0;
      case 3:
        return state.scheduleMode === "now" || state.scheduledAt.length > 0;
      default:
        return true;
    }
  };

  const handleLaunch = () => {
    createMutation.mutate();
  };

  const slideVariants = {
    enter: (direction: number) => ({ x: direction > 0 ? 300 : -300, opacity: 0 }),
    center: { x: 0, opacity: 1 },
    exit: (direction: number) => ({ x: direction < 0 ? 300 : -300, opacity: 0 }),
  };

  const [direction, setDirection] = useState(0);

  const goNext = () => {
    if (step < steps.length - 1) {
      setDirection(1);
      setStep((s) => s + 1);
    }
  };
  const goBack = () => {
    if (step > 0) {
      setDirection(-1);
      setStep((s) => s - 1);
    }
  };

  return (
    <div>
      {showConfetti && <ConfettiBurst />}

      {/* Header */}
      <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} className="mb-8">
        <button
          onClick={() => navigate("/campaigns")}
          className="flex items-center gap-1 text-sm text-gray-400 hover:text-white transition-colors mb-3"
        >
          <ChevronLeft className="w-4 h-4" /> Back to Campaigns
        </button>
        <h1 className="text-3xl font-bold text-white">Create Campaign</h1>
        <p className="text-gray-400 mt-1">Build and launch your SMS campaign step by step.</p>
      </motion.div>

      {/* Progress Bar */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className="mb-10"
      >
        <div className="flex items-center justify-between max-w-3xl mx-auto">
          {steps.map((s, i) => {
            const Icon = s.icon;
            const isActive = i === step;
            const isDone = i < step;
            return (
              <div key={s.label} className="flex items-center">
                <div className="flex flex-col items-center">
                  <motion.div
                    animate={{
                      scale: isActive ? 1.15 : 1,
                      backgroundColor: isDone ? "#3b82f6" : isActive ? "#3b82f680" : "transparent",
                    }}
                    className={clsx(
                      "w-10 h-10 rounded-full flex items-center justify-center border-2 transition-colors",
                      isDone
                        ? "border-blue-500 bg-blue-500"
                        : isActive
                        ? "border-blue-500 bg-blue-500/30"
                        : "border-white/20 bg-white/5"
                    )}
                  >
                    {isDone ? (
                      <CheckCircle2 className="w-5 h-5 text-white" />
                    ) : (
                      <Icon className={clsx("w-5 h-5", isActive ? "text-blue-400" : "text-gray-500")} />
                    )}
                  </motion.div>
                  <span className={clsx("text-xs mt-2 font-medium", isActive ? "text-white" : isDone ? "text-blue-400" : "text-gray-500")}>
                    {s.label}
                  </span>
                </div>
                {i < steps.length - 1 && (
                  <div className="w-16 sm:w-24 lg:w-32 h-0.5 mx-2 mt-[-1rem]">
                    <div className="h-full bg-white/10 rounded-full overflow-hidden">
                      <motion.div
                        initial={{ width: 0 }}
                        animate={{ width: isDone ? "100%" : "0%" }}
                        className="h-full bg-blue-500 rounded-full"
                        transition={{ duration: 0.5 }}
                      />
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </motion.div>

      {/* Step Content */}
      <GlassCard className="mb-8 min-h-[400px] overflow-hidden">
        <AnimatePresence mode="wait" custom={direction}>
          <motion.div
            key={step}
            custom={direction}
            variants={slideVariants}
            initial="enter"
            animate="center"
            exit="exit"
            transition={{ type: "tween", duration: 0.3 }}
          >
            {step === 0 && <StepDetails state={state} onChange={update} />}
            {step === 1 && <StepAudience state={state} onChange={update} />}
            {step === 2 && <StepMessage state={state} onChange={update} />}
            {step === 3 && <StepSchedule state={state} onChange={update} />}
            {step === 4 && <StepReview state={state} />}
          </motion.div>
        </AnimatePresence>
      </GlassCard>

      {/* Navigation Buttons */}
      <div className="flex items-center justify-between">
        <motion.button
          whileHover={{ scale: 1.03 }}
          whileTap={{ scale: 0.97 }}
          onClick={goBack}
          disabled={step === 0}
          className={clsx(
            "flex items-center gap-2 px-5 py-2.5 rounded-xl font-semibold text-sm transition-all",
            step === 0
              ? "opacity-0 pointer-events-none"
              : "text-gray-300 bg-white/5 border border-white/10 hover:bg-white/10"
          )}
        >
          <ChevronLeft className="w-4 h-4" />
          Back
        </motion.button>

        {step < steps.length - 1 ? (
          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={goNext}
            disabled={!canNext()}
            className={clsx(
              "flex items-center gap-2 px-6 py-2.5 rounded-xl font-semibold text-sm text-white shadow-lg transition-all",
              canNext()
                ? "bg-gradient-to-r from-blue-500 to-indigo-600 hover:from-blue-600 hover:to-indigo-700 shadow-blue-500/25"
                : "bg-gray-700 cursor-not-allowed opacity-50"
            )}
          >
            Next
            <ChevronRight className="w-4 h-4" />
          </motion.button>
        ) : (
          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={handleLaunch}
            disabled={createMutation.isPending || showConfetti}
            className={clsx(
              "flex items-center gap-2 px-8 py-3 rounded-xl font-bold text-sm text-white shadow-lg transition-all",
              showConfetti
                ? "bg-emerald-500 shadow-emerald-500/25"
                : "bg-gradient-to-r from-emerald-500 to-teal-600 hover:from-emerald-600 hover:to-teal-700 shadow-emerald-500/25"
            )}
          >
            {createMutation.isPending ? (
              <>
                <motion.div
                  animate={{ rotate: 360 }}
                  transition={{ repeat: Infinity, duration: 1, ease: "linear" }}
                  className="w-4 h-4 border-2 border-white border-t-transparent rounded-full"
                />
                Launching...
              </>
            ) : showConfetti ? (
              <>
                <CheckCircle2 className="w-5 h-5" />
                Campaign Launched!
              </>
            ) : (
              <>
                <Rocket className="w-5 h-5" />
                Launch Campaign
              </>
            )}
          </motion.button>
        )}
      </div>
    </div>
  );
}
