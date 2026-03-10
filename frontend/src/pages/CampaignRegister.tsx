import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useNavigate } from "react-router-dom";
import { useForm, useFieldArray } from "react-hook-form";
import {
  Megaphone,
  FileText,
  ShieldCheck,
  ClipboardCheck,
  ChevronRight,
  ChevronLeft,
  Check,
  Loader2,
  Plus,
  Trash2,
} from "lucide-react";
import clsx from "clsx";
import GlassCard from "../components/ui/GlassCard";
import toast from "react-hot-toast";
import api from "../lib/api";

interface Brand {
  id: string;
  legal_name: string;
  status: string;
}

interface CampaignFormData {
  brandId: string;
  useCase: string;
  subUsecases: string[];
  description: string;
  messageFlow: string;
  sampleMessages: { value: string }[];
  helpMessage: string;
  optInMessage: string;
  optOutMessage: string;
  subscriberOptin: boolean;
  subscriberOptout: boolean;
  subscriberHelp: boolean;
  numberPool: boolean;
  directLending: boolean;
  embeddedLinks: boolean;
  embeddedPhone: boolean;
  affiliateMarketing: boolean;
  ageGated: boolean;
  autoRenewal: boolean;
  privacyPolicyLink: string;
  termsAndConditionsLink: string;
}

const steps = [
  { id: 0, label: "Brand & Use Case", icon: Megaphone },
  { id: 1, label: "Campaign Details", icon: FileText },
  { id: 2, label: "Compliance Config", icon: ShieldCheck },
  { id: 3, label: "Review", icon: ClipboardCheck },
];

const useCases = [
  { value: "2FA", label: "Two-Factor Authentication" },
  { value: "ACCOUNT_NOTIFICATION", label: "Account Notification" },
  { value: "CUSTOMER_CARE", label: "Customer Care" },
  { value: "DELIVERY_NOTIFICATION", label: "Delivery Notification" },
  { value: "FRAUD_ALERT", label: "Fraud Alert" },
  { value: "HIGHER_EDUCATION", label: "Higher Education" },
  { value: "LOW_VOLUME", label: "Low Volume Mixed" },
  { value: "MARKETING", label: "Marketing" },
  { value: "MIXED", label: "Mixed" },
  { value: "POLLING_VOTING", label: "Polling & Voting" },
  { value: "PUBLIC_SERVICE_ANNOUNCEMENT", label: "Public Service Announcement" },
  { value: "SECURITY_ALERT", label: "Security Alert" },
  { value: "STARTER", label: "Starter" },
];

const subUsecaseOptions = [
  { value: "2FA", label: "Two-Factor Authentication" },
  { value: "ACCOUNT_NOTIFICATION", label: "Account Notification" },
  { value: "CUSTOMER_CARE", label: "Customer Care" },
  { value: "DELIVERY_NOTIFICATION", label: "Delivery Notification" },
  { value: "FRAUD_ALERT", label: "Fraud Alert" },
  { value: "MARKETING", label: "Marketing" },
  { value: "SECURITY_ALERT", label: "Security Alert" },
];

const slideVariants = {
  enter: (direction: number) => ({
    x: direction > 0 ? 300 : -300,
    opacity: 0,
  }),
  center: { x: 0, opacity: 1 },
  exit: (direction: number) => ({
    x: direction > 0 ? -300 : 300,
    opacity: 0,
  }),
};

const inputClass =
  "w-full px-4 py-3 bg-white/5 border border-white/10 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500/50 transition-all";
const labelClass = "block text-sm font-medium text-gray-300 mb-1.5";
const errorClass = "text-xs text-rose-400 mt-1";

export default function CampaignRegister() {
  const navigate = useNavigate();
  const [currentStep, setCurrentStep] = useState(0);
  const [direction, setDirection] = useState(1);
  const [submitting, setSubmitting] = useState(false);
  const [brands, setBrands] = useState<Brand[]>([]);
  const [loadingBrands, setLoadingBrands] = useState(true);

  const {
    register,
    handleSubmit,
    trigger,
    getValues,
    watch,
    control,
    setValue,
    formState: { errors },
  } = useForm<CampaignFormData>({
    defaultValues: {
      brandId: "",
      useCase: "",
      subUsecases: [],
      description: "",
      messageFlow: "",
      sampleMessages: [{ value: "" }],
      helpMessage: "",
      optInMessage: "",
      optOutMessage: "",
      subscriberOptin: true,
      subscriberOptout: true,
      subscriberHelp: true,
      numberPool: false,
      directLending: false,
      embeddedLinks: false,
      embeddedPhone: false,
      affiliateMarketing: false,
      ageGated: false,
      autoRenewal: false,
      privacyPolicyLink: "",
      termsAndConditionsLink: "",
    },
  });

  const { fields, append, remove } = useFieldArray({
    control,
    name: "sampleMessages",
  });

  const selectedUseCase = watch("useCase");
  const descriptionVal = watch("description");
  const messageFlowVal = watch("messageFlow");
  const showSubUsecases = ["MIXED", "LOW_VOLUME", "STARTER"].includes(
    selectedUseCase
  );

  useEffect(() => {
    const fetchBrands = async () => {
      try {
        const res = await api.get("/compliance/brands");
        setBrands(res.data);
      } catch {
        toast.error("Failed to load brands");
      } finally {
        setLoadingBrands(false);
      }
    };
    fetchBrands();
  }, []);

  const stepValidation = async (step: number): Promise<boolean> => {
    switch (step) {
      case 0:
        return trigger(["brandId", "useCase"]);
      case 1:
        return trigger(["description", "messageFlow", "sampleMessages"]);
      case 2:
        return trigger(["helpMessage", "optOutMessage"]);
      default:
        return true;
    }
  };

  const goNext = async () => {
    const valid = await stepValidation(currentStep);
    if (!valid) return;
    setDirection(1);
    setCurrentStep((s) => Math.min(s + 1, 3));
  };

  const goBack = () => {
    setDirection(-1);
    setCurrentStep((s) => Math.max(s - 1, 0));
  };

  const onSubmit = async (data: CampaignFormData) => {
    setSubmitting(true);
    try {
      await api.post("/compliance/campaigns/apply", {
        brand_id: data.brandId,
        use_case: data.useCase,
        sub_usecases: data.subUsecases.length > 0 ? data.subUsecases : null,
        description: data.description,
        message_flow: data.messageFlow,
        sample_messages: data.sampleMessages
          .map((m) => m.value)
          .filter((v) => v.length > 0),
        help_message: data.helpMessage,
        opt_in_message: data.optInMessage || null,
        opt_out_message: data.optOutMessage,
        subscriber_optin: data.subscriberOptin,
        subscriber_optout: data.subscriberOptout,
        subscriber_help: data.subscriberHelp,
        number_pool: data.numberPool,
        direct_lending: data.directLending,
        embedded_links: data.embeddedLinks,
        embedded_phone: data.embeddedPhone,
        affiliate_marketing: data.affiliateMarketing,
        age_gated: data.ageGated,
        auto_renewal: data.autoRenewal,
        privacy_policy_link: data.privacyPolicyLink || null,
        terms_and_conditions_link: data.termsAndConditionsLink || null,
      });
      toast.success("Campaign registration submitted for admin review!");
      navigate("/compliance");
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string } } };
      toast.error(
        error?.response?.data?.detail ||
          "Failed to submit campaign registration"
      );
    } finally {
      setSubmitting(false);
    }
  };

  const values = getValues();

  const handleSubUsecaseToggle = (value: string) => {
    const current = getValues("subUsecases") || [];
    if (current.includes(value)) {
      setValue(
        "subUsecases",
        current.filter((v) => v !== value)
      );
    } else {
      setValue("subUsecases", [...current, value]);
    }
  };

  return (
    <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-white">Register Campaign</h1>
        <p className="text-gray-400 mt-1">
          Register a new 10DLC campaign. This will be submitted for admin review
          before being sent to The Campaign Registry.
        </p>
      </div>

      {/* Step Indicator */}
      <div className="flex items-center justify-center mb-10">
        {steps.map((step, i) => {
          const StepIcon = step.icon;
          const isComplete = i < currentStep;
          const isCurrent = i === currentStep;
          return (
            <div key={step.id} className="flex items-center">
              <motion.div
                animate={{
                  scale: isCurrent ? 1.1 : 1,
                  boxShadow: isCurrent
                    ? "0 0 20px rgba(59, 130, 246, 0.4)"
                    : "0 0 0px transparent",
                }}
                className={clsx(
                  "w-12 h-12 rounded-xl flex items-center justify-center border transition-all",
                  isComplete
                    ? "bg-gradient-to-br from-blue-500 to-indigo-600 border-blue-500/50"
                    : isCurrent
                    ? "bg-blue-500/20 border-blue-500/50"
                    : "bg-white/5 border-white/10"
                )}
              >
                {isComplete ? (
                  <Check className="w-5 h-5 text-white" />
                ) : (
                  <StepIcon
                    className={clsx(
                      "w-5 h-5",
                      isCurrent ? "text-blue-400" : "text-gray-500"
                    )}
                  />
                )}
              </motion.div>
              <div
                className={clsx(
                  "ml-2 mr-6",
                  i === steps.length - 1 && "mr-0"
                )}
              >
                <p
                  className={clsx(
                    "text-xs font-medium",
                    isCurrent ? "text-white" : "text-gray-500"
                  )}
                >
                  Step {i + 1}
                </p>
                <p
                  className={clsx(
                    "text-sm",
                    isCurrent ? "text-blue-400" : "text-gray-500"
                  )}
                >
                  {step.label}
                </p>
              </div>
              {i < steps.length - 1 && (
                <div
                  className={clsx(
                    "w-12 h-0.5 rounded-full mr-6",
                    isComplete ? "bg-blue-500" : "bg-white/10"
                  )}
                />
              )}
            </div>
          );
        })}
      </div>

      {/* Form */}
      <div className="max-w-2xl mx-auto">
        <GlassCard>
          <form onSubmit={handleSubmit(onSubmit)}>
            <div className="relative overflow-hidden min-h-[420px]">
              <AnimatePresence mode="wait" custom={direction}>
                {/* Step 0: Brand & Use Case */}
                {currentStep === 0 && (
                  <motion.div
                    key="step0"
                    custom={direction}
                    variants={slideVariants}
                    initial="enter"
                    animate="center"
                    exit="exit"
                    transition={{ duration: 0.3, ease: "easeInOut" }}
                    className="space-y-5"
                  >
                    <h3 className="text-lg font-semibold text-white mb-4">
                      Brand & Use Case
                    </h3>
                    <div>
                      <label className={labelClass}>Brand</label>
                      {loadingBrands ? (
                        <div className="flex items-center gap-2 text-gray-400 text-sm py-3">
                          <Loader2 className="w-4 h-4 animate-spin" />
                          Loading brands...
                        </div>
                      ) : (
                        <select
                          {...register("brandId", {
                            required: "Please select a brand",
                          })}
                          className={inputClass}
                        >
                          <option value="" className="bg-navy-900">
                            Select a brand...
                          </option>
                          {brands.map((b) => (
                            <option
                              key={b.id}
                              value={b.id}
                              className="bg-navy-900"
                            >
                              {b.legal_name}
                            </option>
                          ))}
                        </select>
                      )}
                      {errors.brandId && (
                        <p className={errorClass}>{errors.brandId.message}</p>
                      )}
                    </div>
                    <div>
                      <label className={labelClass}>Use Case</label>
                      <select
                        {...register("useCase", {
                          required: "Use case is required",
                        })}
                        className={inputClass}
                      >
                        <option value="" className="bg-navy-900">
                          Select use case...
                        </option>
                        {useCases.map((u) => (
                          <option
                            key={u.value}
                            value={u.value}
                            className="bg-navy-900"
                          >
                            {u.label}
                          </option>
                        ))}
                      </select>
                      {errors.useCase && (
                        <p className={errorClass}>{errors.useCase.message}</p>
                      )}
                    </div>

                    {showSubUsecases && (
                      <div>
                        <label className={labelClass}>
                          Sub-Usecases{" "}
                          <span className="text-gray-500">
                            (select applicable)
                          </span>
                        </label>
                        <div className="grid grid-cols-2 gap-2">
                          {subUsecaseOptions.map((opt) => {
                            const currentSubs = watch("subUsecases") || [];
                            const isSelected = currentSubs.includes(opt.value);
                            return (
                              <button
                                key={opt.value}
                                type="button"
                                onClick={() =>
                                  handleSubUsecaseToggle(opt.value)
                                }
                                className={clsx(
                                  "px-3 py-2 rounded-lg text-xs font-medium border transition-all text-left",
                                  isSelected
                                    ? "bg-blue-500/20 border-blue-500/50 text-blue-300"
                                    : "bg-white/5 border-white/10 text-gray-400 hover:bg-white/10"
                                )}
                              >
                                {opt.label}
                              </button>
                            );
                          })}
                        </div>
                      </div>
                    )}
                  </motion.div>
                )}

                {/* Step 1: Campaign Details */}
                {currentStep === 1 && (
                  <motion.div
                    key="step1"
                    custom={direction}
                    variants={slideVariants}
                    initial="enter"
                    animate="center"
                    exit="exit"
                    transition={{ duration: 0.3, ease: "easeInOut" }}
                    className="space-y-5"
                  >
                    <h3 className="text-lg font-semibold text-white mb-4">
                      Campaign Details
                    </h3>
                    <div>
                      <label className={labelClass}>
                        Description{" "}
                        <span className="text-gray-500">(min 40 chars)</span>
                      </label>
                      <textarea
                        {...register("description", {
                          required: "Description is required",
                          minLength: {
                            value: 40,
                            message: "Must be at least 40 characters",
                          },
                        })}
                        rows={3}
                        placeholder="Describe the purpose of this campaign and what messages will be sent..."
                        className={clsx(inputClass, "resize-none")}
                      />
                      <div className="flex justify-between mt-1">
                        {errors.description ? (
                          <p className={errorClass}>
                            {errors.description.message}
                          </p>
                        ) : (
                          <span />
                        )}
                        <span
                          className={clsx(
                            "text-xs",
                            (descriptionVal?.length || 0) < 40
                              ? "text-gray-500"
                              : "text-emerald-400"
                          )}
                        >
                          {descriptionVal?.length || 0}/40 min
                        </span>
                      </div>
                    </div>
                    <div>
                      <label className={labelClass}>
                        Message Flow{" "}
                        <span className="text-gray-500">(min 40 chars)</span>
                      </label>
                      <textarea
                        {...register("messageFlow", {
                          required: "Message flow is required",
                          minLength: {
                            value: 40,
                            message: "Must be at least 40 characters",
                          },
                        })}
                        rows={3}
                        placeholder="Describe how subscribers opt-in and what they should expect..."
                        className={clsx(inputClass, "resize-none")}
                      />
                      <div className="flex justify-between mt-1">
                        {errors.messageFlow ? (
                          <p className={errorClass}>
                            {errors.messageFlow.message}
                          </p>
                        ) : (
                          <span />
                        )}
                        <span
                          className={clsx(
                            "text-xs",
                            (messageFlowVal?.length || 0) < 40
                              ? "text-gray-500"
                              : "text-emerald-400"
                          )}
                        >
                          {messageFlowVal?.length || 0}/40 min
                        </span>
                      </div>
                    </div>
                    <div>
                      <label className={labelClass}>
                        Sample Messages{" "}
                        <span className="text-gray-500">
                          (1-5, each min 20 chars)
                        </span>
                      </label>
                      <div className="space-y-3">
                        {fields.map((field, index) => (
                          <div key={field.id} className="flex gap-2">
                            <input
                              {...register(
                                `sampleMessages.${index}.value` as const,
                                {
                                  required: "Sample message is required",
                                  minLength: {
                                    value: 20,
                                    message: "Must be at least 20 characters",
                                  },
                                }
                              )}
                              placeholder={`Sample message ${index + 1}...`}
                              className={clsx(inputClass, "flex-1")}
                            />
                            {fields.length > 1 && (
                              <button
                                type="button"
                                onClick={() => remove(index)}
                                className="px-3 py-2 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-400 hover:bg-rose-500/20 transition-all"
                              >
                                <Trash2 className="w-4 h-4" />
                              </button>
                            )}
                          </div>
                        ))}
                        {errors.sampleMessages && (
                          <p className={errorClass}>
                            Please ensure all sample messages have at least 20
                            characters
                          </p>
                        )}
                      </div>
                      {fields.length < 5 && (
                        <button
                          type="button"
                          onClick={() => append({ value: "" })}
                          className="mt-2 inline-flex items-center gap-1.5 text-xs text-blue-400 hover:text-blue-300 transition-colors"
                        >
                          <Plus className="w-3.5 h-3.5" />
                          Add Sample Message
                        </button>
                      )}
                    </div>
                  </motion.div>
                )}

                {/* Step 2: Compliance Config */}
                {currentStep === 2 && (
                  <motion.div
                    key="step2"
                    custom={direction}
                    variants={slideVariants}
                    initial="enter"
                    animate="center"
                    exit="exit"
                    transition={{ duration: 0.3, ease: "easeInOut" }}
                    className="space-y-5"
                  >
                    <h3 className="text-lg font-semibold text-white mb-4">
                      Compliance Configuration
                    </h3>
                    <div>
                      <label className={labelClass}>
                        Help Message{" "}
                        <span className="text-gray-500">(20-320 chars)</span>
                      </label>
                      <input
                        {...register("helpMessage", {
                          required: "Help message is required",
                          minLength: {
                            value: 20,
                            message: "Must be at least 20 characters",
                          },
                          maxLength: {
                            value: 320,
                            message: "Must be 320 characters or less",
                          },
                        })}
                        placeholder="Reply HELP for assistance or contact support@example.com"
                        className={inputClass}
                      />
                      {errors.helpMessage && (
                        <p className={errorClass}>
                          {errors.helpMessage.message}
                        </p>
                      )}
                    </div>
                    <div>
                      <label className={labelClass}>
                        Opt-In Message{" "}
                        <span className="text-gray-500">
                          (optional, max 320 chars)
                        </span>
                      </label>
                      <input
                        {...register("optInMessage", {
                          maxLength: {
                            value: 320,
                            message: "Must be 320 characters or less",
                          },
                        })}
                        placeholder="You have subscribed to [Brand] alerts. Reply STOP to opt out."
                        className={inputClass}
                      />
                      {errors.optInMessage && (
                        <p className={errorClass}>
                          {errors.optInMessage.message}
                        </p>
                      )}
                    </div>
                    <div>
                      <label className={labelClass}>
                        Opt-Out Message{" "}
                        <span className="text-gray-500">(20-320 chars)</span>
                      </label>
                      <input
                        {...register("optOutMessage", {
                          required: "Opt-out message is required",
                          minLength: {
                            value: 20,
                            message: "Must be at least 20 characters",
                          },
                          maxLength: {
                            value: 320,
                            message: "Must be 320 characters or less",
                          },
                        })}
                        placeholder="You have been unsubscribed. No more messages will be sent."
                        className={inputClass}
                      />
                      {errors.optOutMessage && (
                        <p className={errorClass}>
                          {errors.optOutMessage.message}
                        </p>
                      )}
                    </div>

                    {/* Toggle switches */}
                    <div>
                      <label className={labelClass}>Campaign Flags</label>
                      <div className="grid grid-cols-2 gap-3">
                        {(
                          [
                            {
                              key: "subscriberOptin",
                              label: "Subscriber Opt-in",
                            },
                            {
                              key: "subscriberOptout",
                              label: "Subscriber Opt-out",
                            },
                            {
                              key: "subscriberHelp",
                              label: "Subscriber Help",
                            },
                            { key: "numberPool", label: "Number Pool" },
                            { key: "directLending", label: "Direct Lending" },
                            { key: "embeddedLinks", label: "Embedded Links" },
                            { key: "embeddedPhone", label: "Embedded Phone" },
                            {
                              key: "affiliateMarketing",
                              label: "Affiliate Marketing",
                            },
                            { key: "ageGated", label: "Age Gated" },
                            { key: "autoRenewal", label: "Auto Renewal" },
                          ] as const
                        ).map((flag) => (
                          <label
                            key={flag.key}
                            className="flex items-center gap-3 p-3 rounded-xl bg-white/5 border border-white/10 cursor-pointer hover:bg-white/8 transition-all"
                          >
                            <input
                              type="checkbox"
                              {...register(flag.key)}
                              className="w-4 h-4 rounded bg-white/10 border-white/20 text-blue-500 focus:ring-blue-500/50"
                            />
                            <span className="text-sm text-gray-300">
                              {flag.label}
                            </span>
                          </label>
                        ))}
                      </div>
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className={labelClass}>
                          Privacy Policy Link{" "}
                          <span className="text-gray-500">(optional)</span>
                        </label>
                        <input
                          {...register("privacyPolicyLink")}
                          placeholder="https://example.com/privacy"
                          className={inputClass}
                        />
                      </div>
                      <div>
                        <label className={labelClass}>
                          Terms & Conditions{" "}
                          <span className="text-gray-500">(optional)</span>
                        </label>
                        <input
                          {...register("termsAndConditionsLink")}
                          placeholder="https://example.com/terms"
                          className={inputClass}
                        />
                      </div>
                    </div>
                  </motion.div>
                )}

                {/* Step 3: Review */}
                {currentStep === 3 && (
                  <motion.div
                    key="step3"
                    custom={direction}
                    variants={slideVariants}
                    initial="enter"
                    animate="center"
                    exit="exit"
                    transition={{ duration: 0.3, ease: "easeInOut" }}
                    className="space-y-5"
                  >
                    <h3 className="text-lg font-semibold text-white mb-4">
                      Review & Submit
                    </h3>
                    <p className="text-sm text-gray-400 mb-4">
                      Please review all information before submitting. Your
                      campaign registration will be reviewed by an admin.
                    </p>
                    <div className="space-y-4">
                      <div className="bg-white/5 rounded-xl p-4">
                        <h4 className="text-xs text-gray-500 uppercase tracking-wider mb-3">
                          Brand & Use Case
                        </h4>
                        <div className="space-y-2 text-sm">
                          <div>
                            <span className="text-gray-500">Brand:</span>{" "}
                            <span className="text-white ml-1">
                              {brands.find((b) => b.id === values.brandId)
                                ?.legal_name || "-"}
                            </span>
                          </div>
                          <div>
                            <span className="text-gray-500">Use Case:</span>{" "}
                            <span className="text-white ml-1">
                              {useCases.find((u) => u.value === values.useCase)
                                ?.label || "-"}
                            </span>
                          </div>
                          {values.subUsecases?.length > 0 && (
                            <div>
                              <span className="text-gray-500">
                                Sub-Usecases:
                              </span>{" "}
                              <span className="text-white ml-1">
                                {values.subUsecases.join(", ")}
                              </span>
                            </div>
                          )}
                        </div>
                      </div>

                      <div className="bg-white/5 rounded-xl p-4">
                        <h4 className="text-xs text-gray-500 uppercase tracking-wider mb-3">
                          Campaign Details
                        </h4>
                        <div className="space-y-2 text-sm">
                          <div>
                            <span className="text-gray-500">Description:</span>{" "}
                            <span className="text-gray-300 ml-1">
                              {values.description || "-"}
                            </span>
                          </div>
                          <div>
                            <span className="text-gray-500">
                              Message Flow:
                            </span>{" "}
                            <span className="text-gray-300 ml-1">
                              {values.messageFlow || "-"}
                            </span>
                          </div>
                          <div>
                            <span className="text-gray-500">
                              Sample Messages:
                            </span>
                            <ul className="mt-1 space-y-1 ml-4">
                              {values.sampleMessages
                                ?.filter((m) => m.value)
                                .map((m, i) => (
                                  <li
                                    key={i}
                                    className="text-gray-300 text-xs font-mono"
                                  >
                                    {i + 1}. {m.value}
                                  </li>
                                ))}
                            </ul>
                          </div>
                        </div>
                      </div>

                      <div className="bg-white/5 rounded-xl p-4">
                        <h4 className="text-xs text-gray-500 uppercase tracking-wider mb-3">
                          Compliance Config
                        </h4>
                        <div className="space-y-2 text-sm">
                          <div>
                            <span className="text-gray-500">
                              Help Message:
                            </span>{" "}
                            <span className="text-gray-300 ml-1">
                              {values.helpMessage || "-"}
                            </span>
                          </div>
                          {values.optInMessage && (
                            <div>
                              <span className="text-gray-500">
                                Opt-In Message:
                              </span>{" "}
                              <span className="text-gray-300 ml-1">
                                {values.optInMessage}
                              </span>
                            </div>
                          )}
                          <div>
                            <span className="text-gray-500">
                              Opt-Out Message:
                            </span>{" "}
                            <span className="text-gray-300 ml-1">
                              {values.optOutMessage || "-"}
                            </span>
                          </div>
                          <div className="flex flex-wrap gap-2 mt-2">
                            {[
                              {
                                key: "subscriberOptin" as const,
                                label: "Opt-in",
                              },
                              {
                                key: "subscriberOptout" as const,
                                label: "Opt-out",
                              },
                              {
                                key: "subscriberHelp" as const,
                                label: "Help",
                              },
                              {
                                key: "numberPool" as const,
                                label: "Number Pool",
                              },
                              {
                                key: "directLending" as const,
                                label: "Direct Lending",
                              },
                              {
                                key: "embeddedLinks" as const,
                                label: "Embedded Links",
                              },
                              {
                                key: "embeddedPhone" as const,
                                label: "Embedded Phone",
                              },
                              {
                                key: "affiliateMarketing" as const,
                                label: "Affiliate Marketing",
                              },
                              {
                                key: "ageGated" as const,
                                label: "Age Gated",
                              },
                              {
                                key: "autoRenewal" as const,
                                label: "Auto Renewal",
                              },
                            ].map((flag) => (
                              <span
                                key={flag.key}
                                className={clsx(
                                  "px-2 py-1 rounded-full text-xs font-medium",
                                  values[flag.key]
                                    ? "bg-emerald-500/20 text-emerald-400"
                                    : "bg-white/5 text-gray-500"
                                )}
                              >
                                {flag.label}:{" "}
                                {values[flag.key] ? "Yes" : "No"}
                              </span>
                            ))}
                          </div>
                        </div>
                      </div>

                      <div className="bg-amber-500/10 border border-amber-500/20 rounded-xl p-4">
                        <p className="text-sm text-amber-300">
                          This campaign registration will be submitted for admin
                          review. You will be notified once it has been approved
                          and submitted to TCR.
                        </p>
                      </div>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>

            {/* Navigation Buttons */}
            <div className="flex items-center justify-between mt-8 pt-6 border-t border-white/10">
              <button
                type="button"
                onClick={
                  currentStep === 0 ? () => navigate("/compliance") : goBack
                }
                className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl font-medium text-sm text-gray-400 hover:text-white bg-white/5 hover:bg-white/10 border border-white/10 transition-all"
              >
                <ChevronLeft className="w-4 h-4" />
                {currentStep === 0 ? "Cancel" : "Back"}
              </button>

              {currentStep < 3 ? (
                <motion.button
                  type="button"
                  onClick={goNext}
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  className="inline-flex items-center gap-2 px-6 py-2.5 rounded-xl font-semibold text-sm text-white bg-gradient-to-r from-blue-500 to-indigo-600 shadow-lg shadow-blue-500/25 transition-all"
                >
                  Continue
                  <ChevronRight className="w-4 h-4" />
                </motion.button>
              ) : (
                <motion.button
                  type="submit"
                  disabled={submitting}
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  className="inline-flex items-center gap-2 px-6 py-2.5 rounded-xl font-semibold text-sm text-white bg-gradient-to-r from-emerald-500 to-teal-600 shadow-lg shadow-emerald-500/25 transition-all disabled:opacity-60"
                >
                  {submitting ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Submitting...
                    </>
                  ) : (
                    <>
                      <Check className="w-4 h-4" />
                      Submit for Admin Review
                    </>
                  )}
                </motion.button>
              )}
            </div>
          </form>
        </GlassCard>
      </div>
    </motion.div>
  );
}
