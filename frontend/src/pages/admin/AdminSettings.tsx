import { motion } from "framer-motion";
import { Settings, Shield, Bell, Key, Database, Globe } from "lucide-react";
import GlassCard from "../../components/ui/GlassCard";

const container = { hidden: { opacity: 0 }, show: { opacity: 1, transition: { staggerChildren: 0.06 } } };
const item = { hidden: { opacity: 0, y: 20 }, show: { opacity: 1, y: 0 } };

const settingsSections = [
  {
    icon: Globe,
    title: "General Settings",
    description: "Platform name, default timezone, and base configuration.",
    color: "blue",
  },
  {
    icon: Key,
    title: "API Keys",
    description: "Configure Bandwidth, Stripe, and AI provider API keys.",
    color: "amber",
  },
  {
    icon: Shield,
    title: "Security",
    description: "JWT secrets, password policies, and session settings.",
    color: "emerald",
  },
  {
    icon: Bell,
    title: "Notifications",
    description: "Email notifications, webhook URLs, and alert thresholds.",
    color: "purple",
  },
  {
    icon: Database,
    title: "Database",
    description: "Database maintenance, backups, and migration status.",
    color: "rose",
  },
];

const colorMap: Record<string, { bg: string; text: string }> = {
  blue: { bg: "bg-blue-500/20", text: "text-blue-400" },
  amber: { bg: "bg-amber-500/20", text: "text-amber-400" },
  emerald: { bg: "bg-emerald-500/20", text: "text-emerald-400" },
  purple: { bg: "bg-purple-500/20", text: "text-purple-400" },
  rose: { bg: "bg-rose-500/20", text: "text-rose-400" },
};

export default function AdminSettings() {
  return (
    <motion.div variants={container} initial="hidden" animate="show">
      <motion.div variants={item} className="mb-8">
        <h1 className="text-3xl font-bold text-white">Settings</h1>
        <p className="text-gray-400 mt-1">Platform configuration and administration</p>
      </motion.div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {settingsSections.map((section) => {
          const colors = colorMap[section.color] || colorMap.blue;
          return (
            <motion.div key={section.title} variants={item}>
              <GlassCard hover className="cursor-pointer">
                <div className="flex items-start gap-4">
                  <div className={`w-12 h-12 rounded-xl ${colors.bg} flex items-center justify-center flex-shrink-0`}>
                    <section.icon className={`w-6 h-6 ${colors.text}`} />
                  </div>
                  <div>
                    <h3 className="text-white font-semibold mb-1">{section.title}</h3>
                    <p className="text-sm text-gray-400">{section.description}</p>
                  </div>
                </div>
              </GlassCard>
            </motion.div>
          );
        })}
      </div>

      <motion.div variants={item} className="mt-8">
        <GlassCard>
          <div className="text-center py-8">
            <Settings className="w-12 h-12 text-gray-600 mx-auto mb-3" />
            <p className="text-gray-500 text-sm">Settings management is coming soon. Individual sections will be built out with full configuration forms.</p>
          </div>
        </GlassCard>
      </motion.div>
    </motion.div>
  );
}
