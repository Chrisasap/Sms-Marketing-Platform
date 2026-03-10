import GlassCard from "./GlassCard";
import AnimatedCounter from "./AnimatedCounter";
import type { LucideIcon } from "lucide-react";
import clsx from "clsx";

interface StatCardProps {
  title: string;
  value: number;
  icon: LucideIcon;
  trend?: number;
  prefix?: string;
  suffix?: string;
  color?: "blue" | "emerald" | "amber" | "rose";
}

const colorMap = {
  blue: "from-blue-500 to-indigo-600",
  emerald: "from-emerald-500 to-teal-600",
  amber: "from-amber-500 to-orange-600",
  rose: "from-rose-500 to-pink-600",
};

export default function StatCard({ title, value, icon: Icon, trend, prefix, suffix, color = "blue" }: StatCardProps) {
  return (
    <GlassCard hover>
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm text-gray-400 mb-1">{title}</p>
          <AnimatedCounter
            value={value}
            prefix={prefix}
            suffix={suffix}
            className="text-3xl font-bold font-mono text-white"
          />
          {trend !== undefined && (
            <p className={clsx("text-xs mt-2 font-medium", trend >= 0 ? "text-emerald-400" : "text-rose-400")}>
              {trend >= 0 ? "+" : ""}{trend}% from last period
            </p>
          )}
        </div>
        <div className={clsx("w-12 h-12 rounded-xl bg-gradient-to-br flex items-center justify-center", colorMap[color])}>
          <Icon className="w-6 h-6 text-white" />
        </div>
      </div>
    </GlassCard>
  );
}
