import { motion } from "framer-motion";
import clsx from "clsx";

interface GlassCardProps {
  children: React.ReactNode;
  className?: string;
  hover?: boolean;
}

export default function GlassCard({ children, className, hover = false }: GlassCardProps) {
  return (
    <motion.div
      whileHover={hover ? { scale: 1.02, y: -2 } : undefined}
      className={clsx(
        "bg-white/5 backdrop-blur-xl border border-white/10 rounded-2xl p-6",
        "shadow-xl shadow-black/20",
        className
      )}
    >
      {children}
    </motion.div>
  );
}
