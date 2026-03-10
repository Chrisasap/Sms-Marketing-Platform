import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { useNavigate } from "react-router-dom";
import {
  Users,
  UserCheck,
  UserX,
  AlertTriangle,
  Plus,
  Upload,
  Download,
  MoreHorizontal,
  Trash2,
  Tag,
  Ban,
  Mail,
  ChevronDown,
} from "lucide-react";
import clsx from "clsx";
import { format } from "date-fns";
import StatCard from "../components/ui/StatCard";
import GlassCard from "../components/ui/GlassCard";
import DataTable from "../components/ui/DataTable";
import api from "../lib/api";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface Contact {
  id: string;
  first_name: string;
  last_name: string;
  phone: string;
  email: string;
  status: "active" | "unsubscribed" | "bounced" | "blocked";
  lists: string[];
  last_messaged: string | null;
}

/* ------------------------------------------------------------------ */
/*  Constants                                                          */
/* ------------------------------------------------------------------ */

const statusBadge: Record<Contact["status"], { bg: string; text: string }> = {
  active: { bg: "bg-emerald-500/20", text: "text-emerald-400" },
  unsubscribed: { bg: "bg-amber-500/20", text: "text-amber-400" },
  bounced: { bg: "bg-rose-500/20", text: "text-rose-400" },
  blocked: { bg: "bg-gray-500/20", text: "text-gray-400" },
};

const container = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { staggerChildren: 0.08 } },
};

const item = {
  hidden: { opacity: 0, y: 20 },
  show: { opacity: 1, y: 0 },
};

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

export default function Contacts() {
  const navigate = useNavigate();
  const [selected, setSelected] = useState<Contact[]>([]);
  const [bulkOpen, setBulkOpen] = useState(false);
  const [statusFilter, setStatusFilter] = useState<string>("all");

  const { data: contacts = [], isLoading, error } = useQuery<Contact[]>({
    queryKey: ["contacts"],
    queryFn: async () => {
      const res = await api.get("/contacts/");
      return res.data.contacts ?? res.data;
    },
  });

  if (error) return <div className="p-8 text-center text-red-400">Failed to load data. Please try again.</div>;

  const stats = {
    total: contacts.length,
    active: contacts.filter((c) => c.status === "active").length,
    unsubscribed: contacts.filter((c) => c.status === "unsubscribed").length,
    bounced: contacts.filter((c) => c.status === "bounced").length,
  };

  const filtered =
    statusFilter === "all"
      ? contacts
      : contacts.filter((c) => c.status === statusFilter);

  const columns = [
    {
      key: "name",
      label: "Name",
      sortable: true,
      render: (row: Contact) => (
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-full bg-gradient-to-br from-blue-500/30 to-indigo-600/30 flex items-center justify-center text-sm font-bold text-blue-400">
            {row.first_name?.[0]}{row.last_name?.[0]}
          </div>
          <div>
            <p className="text-white font-medium">{row.first_name} {row.last_name}</p>
          </div>
        </div>
      ),
    },
    {
      key: "phone",
      label: "Phone",
      sortable: true,
      render: (row: Contact) => (
        <span className="font-mono text-gray-300 text-sm">{row.phone}</span>
      ),
    },
    {
      key: "email",
      label: "Email",
      sortable: true,
      render: (row: Contact) => (
        <span className="text-gray-400 text-sm">{row.email || <span className="italic text-gray-600">N/A</span>}</span>
      ),
    },
    {
      key: "status",
      label: "Status",
      sortable: true,
      render: (row: Contact) => {
        const badge = statusBadge[row.status];
        return (
          <span className={clsx("inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium", badge.bg, badge.text)}>
            {row.status.charAt(0).toUpperCase() + row.status.slice(1)}
          </span>
        );
      },
    },
    {
      key: "lists",
      label: "Lists",
      render: (row: Contact) => (
        <div className="flex flex-wrap gap-1">
          {(row.lists || []).slice(0, 2).map((list) => (
            <span key={list} className="px-2 py-0.5 bg-white/5 border border-white/10 rounded-md text-xs text-gray-400">
              {list}
            </span>
          ))}
          {(row.lists || []).length > 2 && (
            <span className="px-2 py-0.5 bg-white/5 border border-white/10 rounded-md text-xs text-gray-500">
              +{row.lists.length - 2}
            </span>
          )}
        </div>
      ),
    },
    {
      key: "last_messaged",
      label: "Last Messaged",
      sortable: true,
      render: (row: Contact) =>
        row.last_messaged ? (
          <span className="text-gray-400 text-sm">
            {format(new Date(row.last_messaged), "MMM d, yyyy")}
          </span>
        ) : (
          <span className="text-gray-600 text-sm italic">Never</span>
        ),
    },
    {
      key: "actions",
      label: "",
      render: (_row: Contact) => (
        <button className="p-1.5 rounded-lg hover:bg-white/10 transition-colors">
          <MoreHorizontal className="w-4 h-4 text-gray-500" />
        </button>
      ),
    },
  ];

  return (
    <motion.div variants={container} initial="hidden" animate="show">
      {/* Header */}
      <motion.div variants={item} className="mb-8">
        <h1 className="text-3xl font-bold text-white">Contacts</h1>
        <p className="text-gray-400 mt-1">Manage your contact database.</p>
      </motion.div>

      {/* Stats */}
      <motion.div variants={container} initial="hidden" animate="show" className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <motion.div variants={item}>
          <StatCard title="Total Contacts" value={stats.total} icon={Users} color="blue" />
        </motion.div>
        <motion.div variants={item}>
          <StatCard title="Active" value={stats.active} icon={UserCheck} color="emerald" />
        </motion.div>
        <motion.div variants={item}>
          <StatCard title="Unsubscribed" value={stats.unsubscribed} icon={UserX} color="amber" />
        </motion.div>
        <motion.div variants={item}>
          <StatCard title="Bounced" value={stats.bounced} icon={AlertTriangle} color="rose" />
        </motion.div>
      </motion.div>

      {/* Action Bar */}
      <motion.div variants={item} className="flex flex-wrap items-center gap-3 mb-6">
        <motion.button
          whileHover={{ scale: 1.03 }}
          whileTap={{ scale: 0.97 }}
          onClick={() => navigate("/contacts/import")}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium text-gray-300 bg-white/5 border border-white/10 hover:bg-white/10 transition-all"
        >
          <Upload className="w-4 h-4" />
          Import
        </motion.button>
        <motion.button
          whileHover={{ scale: 1.03 }}
          whileTap={{ scale: 0.97 }}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium text-gray-300 bg-white/5 border border-white/10 hover:bg-white/10 transition-all"
        >
          <Download className="w-4 h-4" />
          Export
        </motion.button>

        {/* Status Filter */}
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="px-4 py-2 rounded-xl text-sm font-medium text-gray-300 bg-white/5 border border-white/10 hover:bg-white/10 transition-all focus:outline-none focus:ring-2 focus:ring-blue-500/50 [color-scheme:dark]"
        >
          <option value="all" className="bg-gray-900">All Status</option>
          <option value="active" className="bg-gray-900">Active</option>
          <option value="unsubscribed" className="bg-gray-900">Unsubscribed</option>
          <option value="bounced" className="bg-gray-900">Bounced</option>
          <option value="blocked" className="bg-gray-900">Blocked</option>
        </select>

        <div className="flex-1" />

        {/* Bulk Actions */}
        {selected.length > 0 && (
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            className="relative"
          >
            <button
              onClick={() => setBulkOpen(!bulkOpen)}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium text-amber-400 bg-amber-500/10 border border-amber-500/30 hover:bg-amber-500/20 transition-all"
            >
              {selected.length} selected
              <ChevronDown className="w-4 h-4" />
            </button>
            {bulkOpen && (
              <motion.div
                initial={{ opacity: 0, y: -5 }}
                animate={{ opacity: 1, y: 0 }}
                className="absolute right-0 top-full mt-2 w-48 bg-gray-900 border border-white/10 rounded-xl shadow-2xl overflow-hidden z-20"
              >
                <button className="w-full flex items-center gap-2 px-4 py-2.5 text-sm text-gray-300 hover:bg-white/5 transition-colors">
                  <Tag className="w-4 h-4" /> Add to List
                </button>
                <button className="w-full flex items-center gap-2 px-4 py-2.5 text-sm text-gray-300 hover:bg-white/5 transition-colors">
                  <Mail className="w-4 h-4" /> Send Message
                </button>
                <button className="w-full flex items-center gap-2 px-4 py-2.5 text-sm text-amber-400 hover:bg-white/5 transition-colors">
                  <Ban className="w-4 h-4" /> Unsubscribe
                </button>
                <button className="w-full flex items-center gap-2 px-4 py-2.5 text-sm text-rose-400 hover:bg-white/5 transition-colors">
                  <Trash2 className="w-4 h-4" /> Delete
                </button>
              </motion.div>
            )}
          </motion.div>
        )}

        <motion.button
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          className="inline-flex items-center gap-2 px-5 py-2 rounded-xl text-sm font-semibold text-white bg-gradient-to-r from-blue-500 to-indigo-600 hover:from-blue-600 hover:to-indigo-700 shadow-lg shadow-blue-500/25 transition-all"
        >
          <Plus className="w-4 h-4" />
          New Contact
        </motion.button>
      </motion.div>

      {/* Table */}
      <motion.div variants={item}>
        <GlassCard>
          {isLoading ? (
            <div className="flex items-center justify-center py-20">
              <motion.div
                animate={{ rotate: 360 }}
                transition={{ repeat: Infinity, duration: 1, ease: "linear" }}
                className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full"
              />
            </div>
          ) : filtered.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-20 text-gray-500">
              <Users className="w-12 h-12 mb-4 opacity-30" />
              <p className="text-lg font-medium">No contacts found</p>
              <p className="text-sm mt-1">Import contacts or add them manually.</p>
            </div>
          ) : (
            <DataTable
              data={filtered}
              columns={columns}
              searchable
              selectable
              onSelect={(rows) => setSelected(rows)}
              pageSize={20}
            />
          )}
        </GlassCard>
      </motion.div>
    </motion.div>
  );
}
