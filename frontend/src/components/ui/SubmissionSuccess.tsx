import { motion } from "framer-motion";
import { CheckCircle2, ArrowLeft, Bot } from "lucide-react";
import { useNavigate } from "react-router-dom";
import GlassCard from "./GlassCard";

interface SubmissionSuccessProps {
  title?: string;
  message?: string;
  backLabel?: string;
  backPath?: string;
}

export default function SubmissionSuccess({
  title = "Application Submitted!",
  message = "Our AI compliance system will analyze your submission to maximize approval chances. An admin will review it within 24 hours.",
  backLabel = "Back to Compliance",
  backPath = "/compliance",
}: SubmissionSuccessProps) {
  const navigate = useNavigate();

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.5, ease: "easeOut" }}
      className="max-w-lg mx-auto mt-12"
    >
      <GlassCard>
        <div className="text-center py-6">
          {/* Animated checkmark */}
          <motion.div
            initial={{ scale: 0, rotate: -180 }}
            animate={{ scale: 1, rotate: 0 }}
            transition={{ delay: 0.2, type: "spring", stiffness: 200, damping: 15 }}
            className="w-20 h-20 rounded-full bg-gradient-to-br from-emerald-500 to-teal-600 flex items-center justify-center mx-auto mb-6 shadow-lg shadow-emerald-500/30"
          >
            <CheckCircle2 className="w-10 h-10 text-white" />
          </motion.div>

          {/* Title */}
          <motion.h2
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4 }}
            className="text-2xl font-bold text-white mb-3"
          >
            {title}
          </motion.h2>

          {/* Message */}
          <motion.p
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.5 }}
            className="text-gray-400 text-sm leading-relaxed mb-6 max-w-sm mx-auto"
          >
            {message}
          </motion.p>

          {/* AI indicator */}
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.6 }}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-purple-500/10 border border-purple-500/20 mb-8"
          >
            <Bot className="w-4 h-4 text-purple-400" />
            <span className="text-xs text-purple-300 font-medium">
              AI-powered compliance review is automatic
            </span>
          </motion.div>

          {/* Progress steps */}
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.7 }}
            className="flex items-center justify-center gap-3 mb-8"
          >
            {[
              { label: "Submitted", active: true },
              { label: "AI Review", active: false },
              { label: "Admin Review", active: false },
              { label: "Approved", active: false },
            ].map((step, i) => (
              <div key={step.label} className="flex items-center gap-3">
                <div className="text-center">
                  <div
                    className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold ${
                      step.active
                        ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/50"
                        : "bg-white/5 text-gray-500 border border-white/10"
                    }`}
                  >
                    {step.active ? (
                      <CheckCircle2 className="w-4 h-4" />
                    ) : (
                      i + 1
                    )}
                  </div>
                  <p className={`text-[10px] mt-1 ${step.active ? "text-emerald-400" : "text-gray-600"}`}>
                    {step.label}
                  </p>
                </div>
                {i < 3 && (
                  <div className={`w-6 h-0.5 rounded-full mb-4 ${step.active ? "bg-emerald-500/50" : "bg-white/10"}`} />
                )}
              </div>
            ))}
          </motion.div>

          {/* Back button */}
          <motion.button
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.8 }}
            onClick={() => navigate(backPath)}
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            className="inline-flex items-center gap-2 px-6 py-2.5 rounded-xl font-semibold text-sm text-white bg-gradient-to-r from-blue-500 to-indigo-600 shadow-lg shadow-blue-500/25 transition-all"
          >
            <ArrowLeft className="w-4 h-4" />
            {backLabel}
          </motion.button>
        </div>
      </GlassCard>
    </motion.div>
  );
}
