import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  FileText,
  Plus,
  Search,
  Image,
  X,
  Edit3,
  Copy,
  Trash2,
} from "lucide-react";
import clsx from "clsx";
import GlassCard from "../components/ui/GlassCard";
import PhoneMockup from "../components/ui/PhoneMockup";
import toast from "react-hot-toast";

const container = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { staggerChildren: 0.08 } },
};

const item = {
  hidden: { opacity: 0, y: 20 },
  show: { opacity: 1, y: 0 },
};

type Category = "All" | "Marketing" | "Transactional" | "Opt-In" | "Custom";

interface Template {
  id: string;
  name: string;
  category: Exclude<Category, "All">;
  body: string;
  mediaUrl?: string;
  createdAt: string;
}

const categoryColors: Record<Exclude<Category, "All">, { bg: string; text: string }> = {
  Marketing: { bg: "bg-blue-500/20", text: "text-blue-400" },
  Transactional: { bg: "bg-emerald-500/20", text: "text-emerald-400" },
  "Opt-In": { bg: "bg-amber-500/20", text: "text-amber-400" },
  Custom: { bg: "bg-purple-500/20", text: "text-purple-400" },
};

const categories: Category[] = ["All", "Marketing", "Transactional", "Opt-In", "Custom"];

const mergeTags = ["{{first_name}}", "{{last_name}}", "{{company}}", "{{phone}}", "{{custom_1}}", "{{opt_out_link}}"];

const initialTemplates: Template[] = [
  {
    id: "1",
    name: "Welcome Message",
    category: "Opt-In",
    body: "Welcome to {{company}}, {{first_name}}! You're now subscribed to our updates. Reply HELP for help or STOP to unsubscribe.",
    createdAt: "2026-03-01",
  },
  {
    id: "2",
    name: "Flash Sale Alert",
    category: "Marketing",
    body: "Hey {{first_name}}! 24-HOUR FLASH SALE: Get 40% off everything at {{company}}! Use code FLASH40 at checkout. Shop now: https://example.com {{opt_out_link}}",
    createdAt: "2026-03-03",
  },
  {
    id: "3",
    name: "Order Confirmation",
    category: "Transactional",
    body: "Hi {{first_name}}, your order #{{custom_1}} has been confirmed! We'll send tracking info once it ships. Questions? Reply to this message.",
    createdAt: "2026-03-05",
  },
  {
    id: "4",
    name: "Appointment Reminder",
    category: "Transactional",
    body: "Reminder: {{first_name}}, you have an appointment with {{company}} tomorrow at {{custom_1}}. Reply C to confirm or R to reschedule.",
    createdAt: "2026-03-06",
  },
  {
    id: "5",
    name: "Loyalty Reward",
    category: "Marketing",
    body: "Congrats {{first_name}}! You've earned a reward at {{company}}. Show this text in-store for a FREE item. Valid through end of month. {{opt_out_link}}",
    createdAt: "2026-03-07",
  },
  {
    id: "6",
    name: "Re-engagement",
    category: "Marketing",
    body: "We miss you, {{first_name}}! It's been a while since your last visit to {{company}}. Come back and enjoy 20% off your next purchase! {{opt_out_link}}",
    createdAt: "2026-03-08",
  },
  {
    id: "7",
    name: "Custom Promo",
    category: "Custom",
    body: "{{first_name}}, {{custom_1}} - Brought to you by {{company}}. {{opt_out_link}}",
    createdAt: "2026-03-08",
  },
  {
    id: "8",
    name: "Shipping Update",
    category: "Transactional",
    body: "Great news, {{first_name}}! Your {{company}} order has shipped. Track it here: {{custom_1}}. Delivery expected in 2-3 business days.",
    createdAt: "2026-03-09",
  },
];

const inputClass =
  "w-full px-4 py-3 bg-white/5 border border-white/10 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50 transition-all";

export default function Templates() {
  const [templates, setTemplates] = useState<Template[]>(initialTemplates);
  const [activeCategory, setActiveCategory] = useState<Category>("All");
  const [search, setSearch] = useState("");
  const [selectedTemplate, setSelectedTemplate] = useState<Template | null>(null);
  const [showModal, setShowModal] = useState(false);
  const [editingTemplate, setEditingTemplate] = useState<Template | null>(null);
  const [newTemplate, setNewTemplate] = useState({
    name: "",
    category: "Marketing" as Exclude<Category, "All">,
    body: "",
  });

  const filtered = templates.filter((t) => {
    const matchesCategory = activeCategory === "All" || t.category === activeCategory;
    const matchesSearch =
      !search ||
      t.name.toLowerCase().includes(search.toLowerCase()) ||
      t.body.toLowerCase().includes(search.toLowerCase());
    return matchesCategory && matchesSearch;
  });

  const openCreateModal = () => {
    setEditingTemplate(null);
    setNewTemplate({ name: "", category: "Marketing", body: "" });
    setShowModal(true);
  };

  const openEditModal = (template: Template) => {
    setEditingTemplate(template);
    setNewTemplate({ name: template.name, category: template.category, body: template.body });
    setShowModal(true);
  };

  const handleSaveTemplate = () => {
    if (!newTemplate.name.trim() || !newTemplate.body.trim()) {
      toast.error("Name and body are required");
      return;
    }

    if (editingTemplate) {
      setTemplates((prev) =>
        prev.map((t) =>
          t.id === editingTemplate.id
            ? { ...t, name: newTemplate.name, category: newTemplate.category, body: newTemplate.body }
            : t
        )
      );
      toast.success("Template updated!");
    } else {
      const created: Template = {
        id: String(Date.now()),
        name: newTemplate.name,
        category: newTemplate.category,
        body: newTemplate.body,
        createdAt: new Date().toISOString().split("T")[0],
      };
      setTemplates((prev) => [created, ...prev]);
      toast.success("Template created!");
    }
    setShowModal(false);
  };

  const deleteTemplate = (id: string) => {
    setTemplates((prev) => prev.filter((t) => t.id !== id));
    if (selectedTemplate?.id === id) setSelectedTemplate(null);
    toast.success("Template deleted");
  };

  const insertMergeTag = (tag: string) => {
    setNewTemplate((p) => ({ ...p, body: p.body + tag }));
  };

  const previewMessages = selectedTemplate
    ? [{ text: selectedTemplate.body.replace(/\{\{first_name\}\}/g, "Sarah").replace(/\{\{company\}\}/g, "BlastWave").replace(/\{\{custom_1\}\}/g, "12345").replace(/\{\{last_name\}\}/g, "Johnson").replace(/\{\{phone\}\}/g, "(555) 123-4567").replace(/\{\{opt_out_link\}\}/g, "Reply STOP to opt out"), from: "sender" as const, time: "Now" }]
    : [{ text: "Select a template to preview", from: "sender" as const }];

  return (
    <motion.div variants={container} initial="hidden" animate="show">
      {/* Header */}
      <motion.div variants={item} className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-8">
        <div>
          <h1 className="text-3xl font-bold text-white">Templates</h1>
          <p className="text-gray-400 mt-1">Manage your message templates and merge tags.</p>
        </div>
        <motion.button
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          onClick={openCreateModal}
          className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl font-semibold text-sm text-white bg-gradient-to-r from-blue-500 to-indigo-600 hover:from-blue-600 hover:to-indigo-700 shadow-lg shadow-blue-500/25 transition-all"
        >
          <Plus className="w-4 h-4" />
          New Template
        </motion.button>
      </motion.div>

      {/* Category Tabs + Search */}
      <motion.div variants={item} className="flex flex-col sm:flex-row gap-4 mb-6">
        <div className="flex gap-1 bg-white/5 rounded-xl p-1 border border-white/10 overflow-x-auto">
          {categories.map((cat) => (
            <button
              key={cat}
              onClick={() => setActiveCategory(cat)}
              className={clsx(
                "relative px-4 py-2 rounded-lg text-sm font-medium transition-colors whitespace-nowrap",
                activeCategory === cat ? "text-white" : "text-gray-400 hover:text-gray-200"
              )}
            >
              {activeCategory === cat && (
                <motion.div
                  layoutId="template-tab"
                  className="absolute inset-0 bg-white/10 rounded-lg"
                  transition={{ type: "spring", stiffness: 400, damping: 30 }}
                />
              )}
              <span className="relative">{cat}</span>
            </button>
          ))}
        </div>
        <div className="relative flex-1 max-w-xs">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search templates..."
            className="w-full pl-10 pr-4 py-2.5 bg-white/5 border border-white/10 rounded-xl text-sm text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50"
          />
        </div>
      </motion.div>

      {/* Main content */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        {/* Template Grid */}
        <div className="xl:col-span-2">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {filtered.map((template) => {
              const catColor = categoryColors[template.category];
              const isSelected = selectedTemplate?.id === template.id;
              return (
                <motion.div key={template.id} variants={item}>
                  <GlassCard
                    hover
                    className={clsx(
                      "cursor-pointer transition-all",
                      isSelected && "ring-2 ring-blue-500/50"
                    )}
                  >
                    <div onClick={() => setSelectedTemplate(template)}>
                      <div className="flex items-start justify-between mb-3">
                        <div className="flex items-center gap-2">
                          <FileText className="w-4 h-4 text-gray-400" />
                          <h4 className="text-white font-semibold text-sm">{template.name}</h4>
                        </div>
                        <span className={clsx("px-2 py-0.5 rounded-full text-xs font-medium", catColor.bg, catColor.text)}>
                          {template.category}
                        </span>
                      </div>
                      <p className="text-sm text-gray-400 line-clamp-3 mb-4 min-h-[3.75rem]">{template.body}</p>
                    </div>
                    <div className="flex items-center justify-between pt-3 border-t border-white/5">
                      <span className="text-xs text-gray-500">{template.createdAt}</span>
                      <div className="flex gap-1">
                        <button
                          onClick={() => openEditModal(template)}
                          className="p-1.5 rounded-lg text-gray-500 hover:text-blue-400 hover:bg-blue-500/10 transition-all"
                        >
                          <Edit3 className="w-3.5 h-3.5" />
                        </button>
                        <button
                          onClick={() => {
                            navigator.clipboard.writeText(template.body);
                            toast.success("Copied to clipboard");
                          }}
                          className="p-1.5 rounded-lg text-gray-500 hover:text-emerald-400 hover:bg-emerald-500/10 transition-all"
                        >
                          <Copy className="w-3.5 h-3.5" />
                        </button>
                        <button
                          onClick={() => deleteTemplate(template.id)}
                          className="p-1.5 rounded-lg text-gray-500 hover:text-rose-400 hover:bg-rose-500/10 transition-all"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </div>
                  </GlassCard>
                </motion.div>
              );
            })}
            {filtered.length === 0 && (
              <div className="col-span-2 flex flex-col items-center justify-center py-20 text-gray-500">
                <FileText className="w-12 h-12 mb-4 opacity-30" />
                <p className="text-lg font-medium">No templates found</p>
                <p className="text-sm mt-1">Try a different filter or create a new template.</p>
              </div>
            )}
          </div>
        </div>

        {/* Phone Preview */}
        <motion.div variants={item} className="hidden xl:block">
          <div className="sticky top-8">
            <h3 className="text-sm font-medium text-gray-400 mb-4 text-center">Preview</h3>
            <PhoneMockup messages={previewMessages} />
            {selectedTemplate && (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="mt-4 text-center"
              >
                <p className="text-xs text-gray-500">
                  {selectedTemplate.body.length} characters
                  {selectedTemplate.body.length > 160 && (
                    <span className="text-amber-400 ml-1">({Math.ceil(selectedTemplate.body.length / 160)} segments)</span>
                  )}
                </p>
              </motion.div>
            )}
          </div>
        </motion.div>
      </div>

      {/* Create / Edit Modal */}
      <AnimatePresence>
        {showModal && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setShowModal(false)}
              className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50"
            />
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 20 }}
              className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-full max-w-xl z-50"
            >
              <div className="bg-navy-900/95 backdrop-blur-xl border border-white/10 rounded-2xl shadow-2xl p-6">
                <div className="flex items-center justify-between mb-6">
                  <h3 className="text-lg font-semibold text-white">
                    {editingTemplate ? "Edit Template" : "New Template"}
                  </h3>
                  <button onClick={() => setShowModal(false)} className="text-gray-500 hover:text-white">
                    <X className="w-5 h-5" />
                  </button>
                </div>
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-1.5">Template Name</label>
                    <input
                      value={newTemplate.name}
                      onChange={(e) => setNewTemplate((p) => ({ ...p, name: e.target.value }))}
                      placeholder="e.g. Holiday Promo"
                      className={inputClass}
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-1.5">Category</label>
                    <select
                      value={newTemplate.category}
                      onChange={(e) => setNewTemplate((p) => ({ ...p, category: e.target.value as Exclude<Category, "All"> }))}
                      className={inputClass}
                    >
                      {categories.filter((c) => c !== "All").map((c) => (
                        <option key={c} value={c} className="bg-navy-900">{c}</option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-1.5">Message Body</label>
                    <textarea
                      value={newTemplate.body}
                      onChange={(e) => setNewTemplate((p) => ({ ...p, body: e.target.value }))}
                      rows={5}
                      placeholder="Type your message..."
                      className={clsx(inputClass, "resize-none")}
                    />
                    <div className="flex items-center justify-between mt-2">
                      <div className="flex flex-wrap gap-1">
                        {mergeTags.map((tag) => (
                          <button
                            key={tag}
                            onClick={() => insertMergeTag(tag)}
                            className="px-2 py-1 text-xs rounded-md bg-blue-500/10 text-blue-400 hover:bg-blue-500/20 border border-blue-500/20 transition-all"
                          >
                            {tag}
                          </button>
                        ))}
                      </div>
                    </div>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-1.5">Media Upload (optional)</label>
                    <div className="border-2 border-dashed border-white/10 rounded-xl p-6 text-center hover:border-blue-500/30 transition-colors cursor-pointer">
                      <Image className="w-8 h-8 mx-auto text-gray-500 mb-2" />
                      <p className="text-sm text-gray-400">Click or drag to upload an image</p>
                      <p className="text-xs text-gray-600 mt-1">PNG, JPG, GIF up to 5MB</p>
                    </div>
                  </div>
                </div>
                <div className="flex justify-end gap-3 mt-6">
                  <button
                    onClick={() => setShowModal(false)}
                    className="px-4 py-2.5 rounded-xl text-sm text-gray-400 hover:text-white bg-white/5 hover:bg-white/10 border border-white/10 transition-all"
                  >
                    Cancel
                  </button>
                  <motion.button
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                    onClick={handleSaveTemplate}
                    className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl font-semibold text-sm text-white bg-gradient-to-r from-blue-500 to-indigo-600 shadow-lg shadow-blue-500/25 transition-all"
                  >
                    {editingTemplate ? "Save Changes" : "Create Template"}
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
