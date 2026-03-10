import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  CreditCard,
  Zap,
  TrendingUp,
  Check,
  Star,
  Crown,
  ArrowRight,
  Download,
  Plus,
  DollarSign,
  X,
} from "lucide-react";
import clsx from "clsx";
import GlassCard from "../components/ui/GlassCard";
import AnimatedCounter from "../components/ui/AnimatedCounter";
import toast from "react-hot-toast";

const container = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { staggerChildren: 0.1 } },
};

const item = {
  hidden: { opacity: 0, y: 20 },
  show: { opacity: 1, y: 0 },
};

interface Plan {
  name: string;
  price: number;
  period: string;
  icon: typeof Star;
  color: string;
  borderGradient: string;
  smsIncluded: number;
  mmsIncluded: number;
  features: string[];
  popular?: boolean;
}

const plans: Plan[] = [
  {
    name: "Starter",
    price: 49,
    period: "/mo",
    icon: Star,
    color: "text-gray-400",
    borderGradient: "from-gray-500 to-gray-600",
    smsIncluded: 5000,
    mmsIncluded: 500,
    features: [
      "5,000 SMS / month",
      "500 MMS / month",
      "2 Phone numbers",
      "1 AI Agent",
      "Basic analytics",
      "Email support",
    ],
  },
  {
    name: "Growth",
    price: 149,
    period: "/mo",
    icon: Zap,
    color: "text-blue-400",
    borderGradient: "from-blue-500 to-indigo-600",
    smsIncluded: 25000,
    mmsIncluded: 2500,
    features: [
      "25,000 SMS / month",
      "2,500 MMS / month",
      "10 Phone numbers",
      "5 AI Agents",
      "Advanced analytics",
      "Priority support",
      "API access",
      "Automations",
    ],
    popular: true,
  },
  {
    name: "Enterprise",
    price: 499,
    period: "/mo",
    icon: Crown,
    color: "text-amber-400",
    borderGradient: "from-amber-500 to-orange-600",
    smsIncluded: 100000,
    mmsIncluded: 10000,
    features: [
      "100,000 SMS / month",
      "10,000 MMS / month",
      "Unlimited numbers",
      "Unlimited AI Agents",
      "Custom analytics",
      "24/7 dedicated support",
      "Full API access",
      "Advanced automations",
      "SSO & SAML",
      "Custom integrations",
    ],
  },
];

interface Invoice {
  id: string;
  date: string;
  amount: string;
  status: "paid" | "pending" | "failed";
  description: string;
}

const invoices: Invoice[] = [
  { id: "INV-2026-003", date: "Mar 1, 2026", amount: "$149.00", status: "paid", description: "Growth Plan - March 2026" },
  { id: "INV-2026-002", date: "Feb 1, 2026", amount: "$149.00", status: "paid", description: "Growth Plan - February 2026" },
  { id: "INV-2026-001", date: "Jan 1, 2026", amount: "$149.00", status: "paid", description: "Growth Plan - January 2026" },
  { id: "INV-2025-012", date: "Dec 1, 2025", amount: "$49.00", status: "paid", description: "Starter Plan - December 2025" },
  { id: "INV-2025-011", date: "Nov 1, 2025", amount: "$49.00", status: "paid", description: "Starter Plan - November 2025" },
];

const invoiceStatusBadge: Record<string, { bg: string; text: string }> = {
  paid: { bg: "bg-emerald-500/20", text: "text-emerald-400" },
  pending: { bg: "bg-amber-500/20", text: "text-amber-400" },
  failed: { bg: "bg-rose-500/20", text: "text-rose-400" },
};

const creditAmounts = [10, 25, 50, 100, 250, 500];

export default function Billing() {
  const [showBuyCredits, setShowBuyCredits] = useState(false);
  const [selectedCredit, setSelectedCredit] = useState(50);
  const currentPlan = "Growth";
  const creditBalance = 142.50;
  const smsUsed = 18432;
  const smsIncluded = 25000;
  const mmsUsed = 1847;
  const mmsIncluded = 2500;

  const handleBuyCredits = () => {
    toast.success(`$${selectedCredit}.00 in credits added to your account!`);
    setShowBuyCredits(false);
  };

  return (
    <motion.div variants={container} initial="hidden" animate="show">
      {/* Header */}
      <motion.div variants={item} className="mb-8">
        <h1 className="text-3xl font-bold text-white">Billing</h1>
        <p className="text-gray-400 mt-1">Manage your subscription, credits, and invoices.</p>
      </motion.div>

      {/* Current Plan + Credits */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        {/* Current Plan */}
        <motion.div variants={item}>
          <div className="relative rounded-2xl p-[1px] bg-gradient-to-r from-blue-500 to-indigo-600">
            <div className="bg-navy-950 rounded-2xl p-6">
              <div className="flex items-start justify-between mb-4">
                <div>
                  <p className="text-xs text-blue-400 uppercase tracking-wider font-medium mb-1">Current Plan</p>
                  <h3 className="text-2xl font-bold text-white">{currentPlan}</h3>
                </div>
                <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center">
                  <Zap className="w-6 h-6 text-white" />
                </div>
              </div>
              <div className="flex items-baseline gap-1 mb-4">
                <span className="text-4xl font-bold font-mono text-white">$149</span>
                <span className="text-gray-400">/month</span>
              </div>
              <div className="flex items-center gap-2 text-sm text-gray-400 mb-6">
                <TrendingUp className="w-4 h-4 text-emerald-400" />
                <span>Renews on April 1, 2026</span>
              </div>
              <motion.button
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                className="w-full py-3 rounded-xl font-semibold text-sm text-white bg-gradient-to-r from-blue-500 to-indigo-600 hover:from-blue-600 hover:to-indigo-700 shadow-lg shadow-blue-500/25 transition-all"
              >
                Upgrade Plan
              </motion.button>
            </div>
          </div>
        </motion.div>

        {/* Credit Balance */}
        <motion.div variants={item}>
          <GlassCard className="h-full flex flex-col justify-between">
            <div>
              <div className="flex items-start justify-between mb-4">
                <div>
                  <p className="text-xs text-emerald-400 uppercase tracking-wider font-medium mb-1">Credit Balance</p>
                  <div className="flex items-baseline gap-1">
                    <span className="text-lg text-gray-400">$</span>
                    <AnimatedCounter value={creditBalance} className="text-4xl font-bold font-mono text-white" duration={1.5} />
                  </div>
                </div>
                <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-emerald-500 to-teal-600 flex items-center justify-center">
                  <DollarSign className="w-6 h-6 text-white" />
                </div>
              </div>
              <p className="text-sm text-gray-400 mb-6">
                Credits are used for overage messages beyond your plan limits.
              </p>
            </div>
            <motion.button
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={() => setShowBuyCredits(true)}
              className="w-full py-3 rounded-xl font-semibold text-sm text-white bg-gradient-to-r from-emerald-500 to-teal-600 hover:from-emerald-600 hover:to-teal-700 shadow-lg shadow-emerald-500/25 transition-all inline-flex items-center justify-center gap-2"
            >
              <Plus className="w-4 h-4" />
              Buy Credits
            </motion.button>
          </GlassCard>
        </motion.div>
      </div>

      {/* Usage Meters */}
      <motion.div variants={item} className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
        {/* SMS Usage */}
        <GlassCard>
          <div className="flex items-center justify-between mb-4">
            <h4 className="text-sm font-medium text-gray-300">SMS Usage</h4>
            <span className="text-xs text-gray-500">{smsUsed.toLocaleString()} / {smsIncluded.toLocaleString()}</span>
          </div>
          <div className="w-full h-4 bg-white/5 rounded-full overflow-hidden mb-2">
            <motion.div
              initial={{ width: 0 }}
              animate={{ width: `${(smsUsed / smsIncluded) * 100}%` }}
              transition={{ duration: 1.5, ease: "easeOut" }}
              className={clsx(
                "h-full rounded-full",
                smsUsed / smsIncluded > 0.9 ? "bg-gradient-to-r from-rose-500 to-pink-500" :
                smsUsed / smsIncluded > 0.7 ? "bg-gradient-to-r from-amber-500 to-orange-500" :
                "bg-gradient-to-r from-blue-500 to-indigo-500"
              )}
            />
          </div>
          <div className="flex items-center justify-between text-xs">
            <span className={clsx(
              "font-medium",
              smsUsed / smsIncluded > 0.9 ? "text-rose-400" :
              smsUsed / smsIncluded > 0.7 ? "text-amber-400" :
              "text-blue-400"
            )}>
              {((smsUsed / smsIncluded) * 100).toFixed(1)}% used
            </span>
            <span className="text-gray-500">{(smsIncluded - smsUsed).toLocaleString()} remaining</span>
          </div>
        </GlassCard>

        {/* MMS Usage */}
        <GlassCard>
          <div className="flex items-center justify-between mb-4">
            <h4 className="text-sm font-medium text-gray-300">MMS Usage</h4>
            <span className="text-xs text-gray-500">{mmsUsed.toLocaleString()} / {mmsIncluded.toLocaleString()}</span>
          </div>
          <div className="w-full h-4 bg-white/5 rounded-full overflow-hidden mb-2">
            <motion.div
              initial={{ width: 0 }}
              animate={{ width: `${(mmsUsed / mmsIncluded) * 100}%` }}
              transition={{ duration: 1.5, ease: "easeOut" }}
              className={clsx(
                "h-full rounded-full",
                mmsUsed / mmsIncluded > 0.9 ? "bg-gradient-to-r from-rose-500 to-pink-500" :
                mmsUsed / mmsIncluded > 0.7 ? "bg-gradient-to-r from-amber-500 to-orange-500" :
                "bg-gradient-to-r from-purple-500 to-violet-500"
              )}
            />
          </div>
          <div className="flex items-center justify-between text-xs">
            <span className={clsx(
              "font-medium",
              mmsUsed / mmsIncluded > 0.9 ? "text-rose-400" :
              mmsUsed / mmsIncluded > 0.7 ? "text-amber-400" :
              "text-purple-400"
            )}>
              {((mmsUsed / mmsIncluded) * 100).toFixed(1)}% used
            </span>
            <span className="text-gray-500">{(mmsIncluded - mmsUsed).toLocaleString()} remaining</span>
          </div>
        </GlassCard>
      </motion.div>

      {/* Plan Comparison */}
      <motion.div variants={item} className="mb-8">
        <h3 className="text-lg font-semibold text-white mb-6">Compare Plans</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {plans.map((plan) => {
            const PlanIcon = plan.icon;
            const isCurrent = plan.name === currentPlan;
            return (
              <motion.div
                key={plan.name}
                whileHover={{ y: -4 }}
                className="relative"
              >
                {plan.popular && (
                  <div className="absolute -top-3 left-1/2 -translate-x-1/2 z-10">
                    <span className="px-3 py-1 rounded-full text-xs font-bold bg-gradient-to-r from-blue-500 to-indigo-600 text-white shadow-lg shadow-blue-500/30">
                      Most Popular
                    </span>
                  </div>
                )}
                <div
                  className={clsx(
                    "relative rounded-2xl p-[1px]",
                    plan.popular
                      ? "bg-gradient-to-r from-blue-500 to-indigo-600"
                      : "bg-white/10"
                  )}
                >
                  <div className="bg-navy-950 rounded-2xl p-6 h-full">
                    <div className="flex items-center gap-3 mb-4">
                      <div className={clsx("w-10 h-10 rounded-xl bg-gradient-to-br flex items-center justify-center", plan.borderGradient)}>
                        <PlanIcon className="w-5 h-5 text-white" />
                      </div>
                      <div>
                        <h4 className="text-white font-semibold">{plan.name}</h4>
                        {isCurrent && (
                          <span className="text-xs text-blue-400 font-medium">Current plan</span>
                        )}
                      </div>
                    </div>
                    <div className="flex items-baseline gap-1 mb-6">
                      <span className="text-3xl font-bold font-mono text-white">${plan.price}</span>
                      <span className="text-gray-400 text-sm">{plan.period}</span>
                    </div>
                    <ul className="space-y-3 mb-6">
                      {plan.features.map((feature, i) => (
                        <li key={i} className="flex items-center gap-2 text-sm text-gray-300">
                          <Check className="w-4 h-4 text-emerald-400 flex-shrink-0" />
                          {feature}
                        </li>
                      ))}
                    </ul>
                    <motion.button
                      whileHover={{ scale: 1.02 }}
                      whileTap={{ scale: 0.98 }}
                      className={clsx(
                        "w-full py-2.5 rounded-xl font-semibold text-sm transition-all inline-flex items-center justify-center gap-2",
                        isCurrent
                          ? "text-gray-400 bg-white/5 border border-white/10 cursor-default"
                          : plan.popular
                          ? "text-white bg-gradient-to-r from-blue-500 to-indigo-600 shadow-lg shadow-blue-500/25"
                          : "text-white bg-white/10 hover:bg-white/15 border border-white/10"
                      )}
                      disabled={isCurrent}
                    >
                      {isCurrent ? "Current Plan" : (
                        <>
                          Choose Plan
                          <ArrowRight className="w-4 h-4" />
                        </>
                      )}
                    </motion.button>
                  </div>
                </div>
              </motion.div>
            );
          })}
        </div>
      </motion.div>

      {/* Invoice History */}
      <motion.div variants={item}>
        <GlassCard>
          <h3 className="text-lg font-semibold text-white mb-4">Invoice History</h3>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-white/5">
                  <th className="text-left text-xs text-gray-400 uppercase tracking-wider pb-3 px-2">Invoice</th>
                  <th className="text-left text-xs text-gray-400 uppercase tracking-wider pb-3 px-2">Date</th>
                  <th className="text-left text-xs text-gray-400 uppercase tracking-wider pb-3 px-2">Description</th>
                  <th className="text-left text-xs text-gray-400 uppercase tracking-wider pb-3 px-2">Amount</th>
                  <th className="text-left text-xs text-gray-400 uppercase tracking-wider pb-3 px-2">Status</th>
                  <th className="text-left text-xs text-gray-400 uppercase tracking-wider pb-3 px-2"></th>
                </tr>
              </thead>
              <tbody>
                {invoices.map((invoice, i) => {
                  const badge = invoiceStatusBadge[invoice.status];
                  return (
                    <motion.tr
                      key={invoice.id}
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: 0.3 + i * 0.05 }}
                      className="border-b border-white/5 last:border-0 hover:bg-white/5 transition-colors"
                    >
                      <td className="py-3 px-2">
                        <span className="text-sm font-mono text-white">{invoice.id}</span>
                      </td>
                      <td className="py-3 px-2 text-sm text-gray-400">{invoice.date}</td>
                      <td className="py-3 px-2 text-sm text-gray-300">{invoice.description}</td>
                      <td className="py-3 px-2 text-sm font-mono font-medium text-white">{invoice.amount}</td>
                      <td className="py-3 px-2">
                        <span className={clsx("px-2.5 py-1 rounded-full text-xs font-medium", badge.bg, badge.text)}>
                          {invoice.status.charAt(0).toUpperCase() + invoice.status.slice(1)}
                        </span>
                      </td>
                      <td className="py-3 px-2">
                        <button className="p-1.5 rounded-lg text-gray-500 hover:text-blue-400 hover:bg-blue-500/10 transition-all">
                          <Download className="w-4 h-4" />
                        </button>
                      </td>
                    </motion.tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </GlassCard>
      </motion.div>

      {/* Buy Credits Modal */}
      <AnimatePresence>
        {showBuyCredits && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setShowBuyCredits(false)}
              className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50"
            />
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 20 }}
              className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-full max-w-md z-50"
            >
              <div className="bg-navy-900/95 backdrop-blur-xl border border-white/10 rounded-2xl shadow-2xl p-6">
                <div className="flex items-center justify-between mb-6">
                  <h3 className="text-lg font-semibold text-white">Buy Credits</h3>
                  <button onClick={() => setShowBuyCredits(false)} className="text-gray-500 hover:text-white">
                    <X className="w-5 h-5" />
                  </button>
                </div>
                <p className="text-sm text-gray-400 mb-4">
                  Select an amount to add to your credit balance. Credits never expire.
                </p>
                <div className="grid grid-cols-3 gap-3 mb-6">
                  {creditAmounts.map((amount) => (
                    <motion.button
                      key={amount}
                      whileHover={{ scale: 1.05 }}
                      whileTap={{ scale: 0.95 }}
                      onClick={() => setSelectedCredit(amount)}
                      className={clsx(
                        "py-3 rounded-xl font-semibold text-sm transition-all border",
                        selectedCredit === amount
                          ? "text-white bg-blue-500/20 border-blue-500/50 shadow-lg shadow-blue-500/10"
                          : "text-gray-400 bg-white/5 border-white/10 hover:bg-white/10"
                      )}
                    >
                      ${amount}
                    </motion.button>
                  ))}
                </div>
                <div className="bg-white/5 rounded-xl p-4 mb-6">
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-gray-400">Credit amount</span>
                    <span className="text-white font-mono font-bold">${selectedCredit}.00</span>
                  </div>
                  <div className="flex items-center justify-between text-sm mt-2">
                    <span className="text-gray-400">Estimated messages</span>
                    <span className="text-gray-300 font-mono">~{(selectedCredit * 100).toLocaleString()} SMS</span>
                  </div>
                </div>
                <div className="flex justify-end gap-3">
                  <button
                    onClick={() => setShowBuyCredits(false)}
                    className="px-4 py-2.5 rounded-xl text-sm text-gray-400 hover:text-white bg-white/5 hover:bg-white/10 border border-white/10 transition-all"
                  >
                    Cancel
                  </button>
                  <motion.button
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                    onClick={handleBuyCredits}
                    className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl font-semibold text-sm text-white bg-gradient-to-r from-emerald-500 to-teal-600 shadow-lg shadow-emerald-500/25 transition-all"
                  >
                    <CreditCard className="w-4 h-4" />
                    Purchase ${selectedCredit}.00
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
