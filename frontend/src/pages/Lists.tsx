import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { List, Plus, Users } from "lucide-react";
import GlassCard from "../components/ui/GlassCard";
import DataTable from "../components/ui/DataTable";
import api from "../lib/api";

interface ContactList {
  id: string;
  name: string;
  description: string;
  contact_count: number;
  created_at: string;
}

const container = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { staggerChildren: 0.08 } },
};

const item = {
  hidden: { opacity: 0, y: 20 },
  show: { opacity: 1, y: 0 },
};

export default function Lists() {
  const { data: lists = [], isLoading, error } = useQuery<ContactList[]>({
    queryKey: ["contact-lists"],
    queryFn: async () => {
      const res = await api.get("/lists");
      return res.data;
    },
  });

  if (error) return <div className="p-8 text-center text-red-400">Failed to load data. Please try again.</div>;

  const columns = [
    {
      key: "name",
      label: "List Name",
      sortable: true,
      render: (row: ContactList) => (
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-blue-500/30 to-indigo-600/30 flex items-center justify-center">
            <List className="w-4 h-4 text-blue-400" />
          </div>
          <div>
            <p className="text-white font-medium">{row.name}</p>
            {row.description && <p className="text-xs text-gray-500">{row.description}</p>}
          </div>
        </div>
      ),
    },
    {
      key: "contact_count",
      label: "Contacts",
      sortable: true,
      render: (row: ContactList) => (
        <span className="font-mono text-gray-300">{row.contact_count.toLocaleString()}</span>
      ),
    },
    {
      key: "created_at",
      label: "Created",
      sortable: true,
      render: (row: ContactList) => (
        <span className="text-gray-400 text-sm">
          {new Date(row.created_at).toLocaleDateString()}
        </span>
      ),
    },
  ];

  return (
    <motion.div variants={container} initial="hidden" animate="show">
      <motion.div
        variants={item}
        className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-8"
      >
        <div>
          <h1 className="text-3xl font-bold text-white">Contact Lists</h1>
          <p className="text-gray-400 mt-1">Organize your contacts into lists.</p>
        </div>
        <motion.button
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl font-semibold text-sm text-white bg-gradient-to-r from-blue-500 to-indigo-600 hover:from-blue-600 hover:to-indigo-700 shadow-lg shadow-blue-500/25 transition-all"
        >
          <Plus className="w-4 h-4" />
          New List
        </motion.button>
      </motion.div>

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
          ) : lists.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-20 text-gray-500">
              <Users className="w-12 h-12 mb-4 opacity-30" />
              <p className="text-lg font-medium">No lists yet</p>
              <p className="text-sm mt-1">Create your first list to organize contacts.</p>
            </div>
          ) : (
            <DataTable data={lists} columns={columns} searchable pageSize={15} />
          )}
        </GlassCard>
      </motion.div>
    </motion.div>
  );
}
