import { useState, useRef, useEffect } from "react";
import { motion } from "framer-motion";
import { useNavigate, useParams } from "react-router-dom";
import {
  Bot,
  Save,
  Play,
  Send,
  Plus,
  Trash2,
  ArrowLeft,
  Loader2,
  BookOpen,
  AlertTriangle,
  Sparkles,
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

interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

interface FAQPair {
  question: string;
  answer: string;
}

interface EscalationRule {
  trigger: string;
  action: string;
  destination: string;
}

const modelOptions = ["GPT-4o", "GPT-4o Mini", "Claude 3.5 Sonnet", "Claude 3 Haiku"];

const inputClass =
  "w-full px-4 py-3 bg-white/5 border border-white/10 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50 transition-all";
const labelClass = "block text-sm font-medium text-gray-300 mb-1.5";

const sampleResponses = [
  "Hello! I'd be happy to help you with that. Could you provide me with your order number?",
  "I found your order #12345. It's currently being processed and should ship within 24 hours. Would you like me to send you tracking updates via SMS?",
  "Done! You'll receive a text message with tracking info once it ships. Is there anything else I can help you with?",
  "Of course! Our return policy allows returns within 30 days of purchase. Would you like me to start a return for this order?",
  "I've initiated the return process. You'll receive a prepaid shipping label via email shortly. The refund will be processed within 5-7 business days after we receive the item.",
];

export default function AIAgentConfig() {
  const { id: _agentId } = useParams();
  const navigate = useNavigate();
  const chatEndRef = useRef<HTMLDivElement>(null);

  const [config, setConfig] = useState({
    name: "Support Assistant",
    systemPrompt:
      "You are a friendly and helpful customer support assistant for an e-commerce company. Answer questions about orders, returns, and products. Be concise but thorough. Always maintain a professional yet warm tone.",
    model: "GPT-4o",
    temperature: 0.7,
    maxTokens: 500,
  });

  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([
    { role: "assistant", content: "Hi there! I'm your AI support assistant. How can I help you today?" },
  ]);
  const [chatInput, setChatInput] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const [responseIndex, setResponseIndex] = useState(0);

  const [faqs, setFaqs] = useState<FAQPair[]>([
    { question: "What are your business hours?", answer: "We're available Monday-Friday, 9AM-6PM EST." },
    { question: "How do I track my order?", answer: "Reply with your order number and I'll look it up for you." },
  ]);
  const [newFaq, setNewFaq] = useState<FAQPair>({ question: "", answer: "" });

  const [escalationRules, setEscalationRules] = useState<EscalationRule[]>([
    { trigger: "angry customer", action: "Transfer to agent", destination: "Support Team" },
    { trigger: "billing dispute", action: "Create ticket", destination: "Billing Queue" },
  ]);
  const [newRule, setNewRule] = useState<EscalationRule>({ trigger: "", action: "Transfer to agent", destination: "" });

  const [saving, setSaving] = useState(false);
  const [isActive, setIsActive] = useState(true);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chatMessages]);

  const handleSendMessage = async () => {
    if (!chatInput.trim()) return;
    const userMsg: ChatMessage = { role: "user", content: chatInput };
    setChatMessages((prev) => [...prev, userMsg]);
    setChatInput("");
    setIsTyping(true);

    await new Promise((r) => setTimeout(r, 1000 + Math.random() * 1500));

    const response = sampleResponses[responseIndex % sampleResponses.length];
    setResponseIndex((i) => i + 1);
    setChatMessages((prev) => [...prev, { role: "assistant", content: response }]);
    setIsTyping(false);
  };

  const addFaq = () => {
    if (!newFaq.question.trim() || !newFaq.answer.trim()) {
      toast.error("Both question and answer are required");
      return;
    }
    setFaqs((prev) => [...prev, newFaq]);
    setNewFaq({ question: "", answer: "" });
    toast.success("FAQ pair added");
  };

  const removeFaq = (index: number) => {
    setFaqs((prev) => prev.filter((_, i) => i !== index));
  };

  const addEscalationRule = () => {
    if (!newRule.trigger.trim() || !newRule.destination.trim()) {
      toast.error("Trigger and destination are required");
      return;
    }
    setEscalationRules((prev) => [...prev, newRule]);
    setNewRule({ trigger: "", action: "Transfer to agent", destination: "" });
    toast.success("Escalation rule added");
  };

  const removeEscalationRule = (index: number) => {
    setEscalationRules((prev) => prev.filter((_, i) => i !== index));
  };

  const handleSave = async () => {
    setSaving(true);
    await new Promise((r) => setTimeout(r, 1500));
    setSaving(false);
    toast.success("Agent configuration saved!");
  };

  return (
    <motion.div variants={container} initial="hidden" animate="show">
      {/* Header */}
      <motion.div variants={item} className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-8">
        <div className="flex items-center gap-4">
          <button
            onClick={() => navigate("/ai-agents")}
            className="w-10 h-10 rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 flex items-center justify-center text-gray-400 hover:text-white transition-all"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div>
            <h1 className="text-3xl font-bold text-white">{config.name}</h1>
            <p className="text-gray-400 mt-1">Configure agent behavior, knowledge base, and escalation rules.</p>
          </div>
        </div>
        <div className="flex gap-3">
          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={() => {
              setIsActive(!isActive);
              toast.success(isActive ? "Agent deactivated" : "Agent activated");
            }}
            className={clsx(
              "inline-flex items-center gap-2 px-5 py-2.5 rounded-xl font-semibold text-sm border transition-all",
              isActive
                ? "text-emerald-400 bg-emerald-500/10 border-emerald-500/30 hover:bg-emerald-500/20"
                : "text-gray-400 bg-white/5 border-white/10 hover:bg-white/10"
            )}
          >
            <Play className="w-4 h-4" />
            {isActive ? "Active" : "Activate"}
          </motion.button>
          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={handleSave}
            disabled={saving}
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl font-semibold text-sm text-white bg-gradient-to-r from-blue-500 to-indigo-600 shadow-lg shadow-blue-500/25 disabled:opacity-60 transition-all"
          >
            {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
            {saving ? "Saving..." : "Save Changes"}
          </motion.button>
        </div>
      </motion.div>

      {/* Main content: Left settings, Right chat */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6 mb-8">
        {/* Left: Settings */}
        <motion.div variants={item} className="space-y-6">
          <GlassCard>
            <h3 className="text-lg font-semibold text-white mb-5 flex items-center gap-2">
              <Bot className="w-5 h-5 text-blue-400" />
              Agent Settings
            </h3>
            <div className="space-y-5">
              <div>
                <label className={labelClass}>Agent Name</label>
                <input
                  value={config.name}
                  onChange={(e) => setConfig((c) => ({ ...c, name: e.target.value }))}
                  className={inputClass}
                />
              </div>
              <div>
                <label className={labelClass}>System Prompt</label>
                <textarea
                  value={config.systemPrompt}
                  onChange={(e) => setConfig((c) => ({ ...c, systemPrompt: e.target.value }))}
                  rows={5}
                  className={clsx(inputClass, "resize-none font-mono text-sm")}
                />
              </div>
              <div>
                <label className={labelClass}>AI Model</label>
                <select
                  value={config.model}
                  onChange={(e) => setConfig((c) => ({ ...c, model: e.target.value }))}
                  className={inputClass}
                >
                  {modelOptions.map((m) => (
                    <option key={m} value={m} className="bg-navy-900">{m}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className={labelClass}>
                  Temperature: <span className="text-blue-400 font-mono">{config.temperature.toFixed(1)}</span>
                </label>
                <input
                  type="range"
                  min="0"
                  max="2"
                  step="0.1"
                  value={config.temperature}
                  onChange={(e) => setConfig((c) => ({ ...c, temperature: parseFloat(e.target.value) }))}
                  className="w-full h-2 bg-white/10 rounded-full appearance-none cursor-pointer [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-5 [&::-webkit-slider-thumb]:h-5 [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-blue-500 [&::-webkit-slider-thumb]:shadow-lg [&::-webkit-slider-thumb]:shadow-blue-500/50"
                />
                <div className="flex justify-between text-xs text-gray-500 mt-1">
                  <span>Precise</span>
                  <span>Creative</span>
                </div>
              </div>
              <div>
                <label className={labelClass}>
                  Max Tokens: <span className="text-blue-400 font-mono">{config.maxTokens}</span>
                </label>
                <input
                  type="range"
                  min="100"
                  max="2000"
                  step="50"
                  value={config.maxTokens}
                  onChange={(e) => setConfig((c) => ({ ...c, maxTokens: parseInt(e.target.value) }))}
                  className="w-full h-2 bg-white/10 rounded-full appearance-none cursor-pointer [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-5 [&::-webkit-slider-thumb]:h-5 [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-blue-500 [&::-webkit-slider-thumb]:shadow-lg [&::-webkit-slider-thumb]:shadow-blue-500/50"
                />
                <div className="flex justify-between text-xs text-gray-500 mt-1">
                  <span>100</span>
                  <span>2000</span>
                </div>
              </div>
            </div>
          </GlassCard>
        </motion.div>

        {/* Right: Test Chat */}
        <motion.div variants={item}>
          <GlassCard className="flex flex-col h-full">
            <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-amber-400" />
              Test Conversation
            </h3>
            <div className="flex-1 bg-white/5 rounded-xl p-4 overflow-y-auto max-h-[400px] space-y-3 mb-4">
              {chatMessages.map((msg, i) => (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className={clsx("flex", msg.role === "user" ? "justify-end" : "justify-start")}
                >
                  <div
                    className={clsx(
                      "max-w-[80%] px-4 py-2.5 rounded-2xl text-sm",
                      msg.role === "user"
                        ? "bg-blue-500 text-white rounded-br-md"
                        : "bg-white/10 text-gray-200 rounded-bl-md"
                    )}
                  >
                    {msg.content}
                  </div>
                </motion.div>
              ))}
              {isTyping && (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="flex justify-start"
                >
                  <div className="bg-white/10 px-4 py-3 rounded-2xl rounded-bl-md">
                    <div className="flex gap-1.5">
                      <motion.div
                        animate={{ y: [0, -4, 0] }}
                        transition={{ repeat: Infinity, duration: 0.6, delay: 0 }}
                        className="w-2 h-2 bg-gray-400 rounded-full"
                      />
                      <motion.div
                        animate={{ y: [0, -4, 0] }}
                        transition={{ repeat: Infinity, duration: 0.6, delay: 0.15 }}
                        className="w-2 h-2 bg-gray-400 rounded-full"
                      />
                      <motion.div
                        animate={{ y: [0, -4, 0] }}
                        transition={{ repeat: Infinity, duration: 0.6, delay: 0.3 }}
                        className="w-2 h-2 bg-gray-400 rounded-full"
                      />
                    </div>
                  </div>
                </motion.div>
              )}
              <div ref={chatEndRef} />
            </div>
            <div className="flex gap-2">
              <input
                value={chatInput}
                onChange={(e) => setChatInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleSendMessage()}
                placeholder="Type a test message..."
                className={clsx(inputClass, "flex-1")}
              />
              <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={handleSendMessage}
                disabled={isTyping}
                className="w-12 h-12 rounded-xl bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center text-white shadow-lg shadow-blue-500/25 disabled:opacity-60"
              >
                <Send className="w-5 h-5" />
              </motion.button>
            </div>
          </GlassCard>
        </motion.div>
      </div>

      {/* Knowledge Base */}
      <motion.div variants={item} className="mb-8">
        <GlassCard>
          <h3 className="text-lg font-semibold text-white mb-5 flex items-center gap-2">
            <BookOpen className="w-5 h-5 text-emerald-400" />
            Knowledge Base
          </h3>
          <div className="space-y-3 mb-5">
            {faqs.map((faq, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="bg-white/5 rounded-xl p-4 flex items-start gap-4"
              >
                <div className="flex-1 grid grid-cols-1 md:grid-cols-2 gap-3">
                  <div>
                    <p className="text-xs text-gray-500 mb-1">Question</p>
                    <p className="text-sm text-white">{faq.question}</p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-500 mb-1">Answer</p>
                    <p className="text-sm text-gray-300">{faq.answer}</p>
                  </div>
                </div>
                <button onClick={() => removeFaq(i)} className="text-gray-500 hover:text-rose-400 transition-colors mt-1">
                  <Trash2 className="w-4 h-4" />
                </button>
              </motion.div>
            ))}
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-3">
            <input
              value={newFaq.question}
              onChange={(e) => setNewFaq((p) => ({ ...p, question: e.target.value }))}
              placeholder="Question..."
              className={inputClass}
            />
            <input
              value={newFaq.answer}
              onChange={(e) => setNewFaq((p) => ({ ...p, answer: e.target.value }))}
              placeholder="Answer..."
              className={inputClass}
            />
          </div>
          <motion.button
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            onClick={addFaq}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium text-blue-400 bg-blue-500/10 hover:bg-blue-500/20 border border-blue-500/20 transition-all"
          >
            <Plus className="w-4 h-4" />
            Add FAQ Pair
          </motion.button>
        </GlassCard>
      </motion.div>

      {/* Escalation Rules */}
      <motion.div variants={item}>
        <GlassCard>
          <h3 className="text-lg font-semibold text-white mb-5 flex items-center gap-2">
            <AlertTriangle className="w-5 h-5 text-amber-400" />
            Escalation Rules
          </h3>
          <div className="space-y-3 mb-5">
            {escalationRules.map((rule, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="bg-white/5 rounded-xl p-4 flex items-center gap-4"
              >
                <div className="flex-1 grid grid-cols-3 gap-3">
                  <div>
                    <p className="text-xs text-gray-500 mb-1">Trigger</p>
                    <p className="text-sm text-white">{rule.trigger}</p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-500 mb-1">Action</p>
                    <p className="text-sm text-amber-400">{rule.action}</p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-500 mb-1">Destination</p>
                    <p className="text-sm text-gray-300">{rule.destination}</p>
                  </div>
                </div>
                <button onClick={() => removeEscalationRule(i)} className="text-gray-500 hover:text-rose-400 transition-colors">
                  <Trash2 className="w-4 h-4" />
                </button>
              </motion.div>
            ))}
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-3">
            <input
              value={newRule.trigger}
              onChange={(e) => setNewRule((p) => ({ ...p, trigger: e.target.value }))}
              placeholder="Trigger keyword..."
              className={inputClass}
            />
            <select
              value={newRule.action}
              onChange={(e) => setNewRule((p) => ({ ...p, action: e.target.value }))}
              className={inputClass}
            >
              <option value="Transfer to agent" className="bg-navy-900">Transfer to agent</option>
              <option value="Create ticket" className="bg-navy-900">Create ticket</option>
              <option value="Send webhook" className="bg-navy-900">Send webhook</option>
              <option value="End conversation" className="bg-navy-900">End conversation</option>
            </select>
            <input
              value={newRule.destination}
              onChange={(e) => setNewRule((p) => ({ ...p, destination: e.target.value }))}
              placeholder="Destination..."
              className={inputClass}
            />
          </div>
          <motion.button
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            onClick={addEscalationRule}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium text-amber-400 bg-amber-500/10 hover:bg-amber-500/20 border border-amber-500/20 transition-all"
          >
            <Plus className="w-4 h-4" />
            Add Escalation Rule
          </motion.button>
        </GlassCard>
      </motion.div>
    </motion.div>
  );
}
