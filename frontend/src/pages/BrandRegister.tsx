import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useNavigate } from "react-router-dom";
import { useForm } from "react-hook-form";
import {
  Building2,
  MapPin,
  Globe,
  ClipboardCheck,
  ChevronRight,
  ChevronLeft,
  Check,
  Loader2,
} from "lucide-react";
import clsx from "clsx";
import GlassCard from "../components/ui/GlassCard";
import toast from "react-hot-toast";
import api from "../lib/api";

interface BrandFormData {
  entityType: string;
  legalName: string;
  dbaName: string;
  ein: string;
  street: string;
  city: string;
  state: string;
  zip: string;
  country: string;
  phone: string;
  email: string;
  brandRelationship: string;
  website: string;
  vertical: string;
  description: string;
  stockSymbol: string;
  stockExchange: string;
  businessContactEmail: string;
}

const steps = [
  { id: 0, label: "Entity Info", icon: Building2 },
  { id: 1, label: "Address", icon: MapPin },
  { id: 2, label: "Business Details", icon: Globe },
  { id: 3, label: "Review", icon: ClipboardCheck },
];

const entityTypes = [
  { value: "PRIVATE_PROFIT", label: "Private Profit" },
  { value: "PUBLIC_PROFIT", label: "Public Profit" },
  { value: "NON_PROFIT", label: "Non-Profit" },
  { value: "GOVERNMENT", label: "Government" },
  { value: "SOLE_PROPRIETOR", label: "Sole Proprietor" },
];

const verticals = [
  { value: "PROFESSIONAL", label: "Professional Services" },
  { value: "REAL_ESTATE", label: "Real Estate" },
  { value: "HEALTHCARE", label: "Healthcare" },
  { value: "HUMAN_RESOURCES", label: "Human Resources" },
  { value: "ENERGY", label: "Energy" },
  { value: "ENTERTAINMENT", label: "Entertainment" },
  { value: "RETAIL", label: "Retail" },
  { value: "TRANSPORTATION", label: "Transportation" },
  { value: "AGRICULTURE", label: "Agriculture" },
  { value: "INSURANCE", label: "Insurance" },
  { value: "POSTAL", label: "Postal" },
  { value: "EDUCATION", label: "Education" },
  { value: "HOSPITALITY", label: "Hospitality" },
  { value: "FINANCIAL", label: "Financial" },
  { value: "POLITICAL", label: "Political" },
  { value: "GAMBLING", label: "Gambling" },
  { value: "LEGAL", label: "Legal" },
  { value: "CONSTRUCTION", label: "Construction" },
  { value: "NGO", label: "NGO" },
  { value: "MANUFACTURING", label: "Manufacturing" },
  { value: "GOVERNMENT", label: "Government" },
  { value: "TECHNOLOGY", label: "Technology" },
  { value: "COMMUNICATION", label: "Communication" },
];

const brandRelationships = [
  { value: "BASIC_ACCOUNT", label: "Basic Account" },
  { value: "SMALL_ACCOUNT", label: "Small Account" },
  { value: "MEDIUM_ACCOUNT", label: "Medium Account" },
  { value: "LARGE_ACCOUNT", label: "Large Account" },
  { value: "KEY_ACCOUNT", label: "Key Account" },
];

const slideVariants = {
  enter: (direction: number) => ({
    x: direction > 0 ? 300 : -300,
    opacity: 0,
  }),
  center: {
    x: 0,
    opacity: 1,
  },
  exit: (direction: number) => ({
    x: direction > 0 ? -300 : 300,
    opacity: 0,
  }),
};

const inputClass =
  "w-full px-4 py-3 bg-white/5 border border-white/10 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500/50 transition-all";
const labelClass = "block text-sm font-medium text-gray-300 mb-1.5";
const errorClass = "text-xs text-rose-400 mt-1";

export default function BrandRegister() {
  const navigate = useNavigate();
  const [currentStep, setCurrentStep] = useState(0);
  const [direction, setDirection] = useState(1);
  const [submitting, setSubmitting] = useState(false);

  const {
    register,
    handleSubmit,
    trigger,
    getValues,
    watch,
    formState: { errors },
  } = useForm<BrandFormData>({
    defaultValues: {
      entityType: "",
      legalName: "",
      dbaName: "",
      ein: "",
      street: "",
      city: "",
      state: "",
      zip: "",
      country: "US",
      phone: "",
      email: "",
      brandRelationship: "",
      website: "",
      vertical: "",
      description: "",
      stockSymbol: "",
      stockExchange: "",
      businessContactEmail: "",
    },
  });

  const entityType = watch("entityType");

  const stepFields: (keyof BrandFormData)[][] = [
    ["entityType", "legalName", "ein"],
    ["street", "city", "state", "zip", "country"],
    ["phone", "email", "vertical", "description"],
    [],
  ];

  const goNext = async () => {
    const fields = stepFields[currentStep];
    const valid = await trigger(fields);
    if (!valid) return;
    setDirection(1);
    setCurrentStep((s) => Math.min(s + 1, 3));
  };

  const goBack = () => {
    setDirection(-1);
    setCurrentStep((s) => Math.max(s - 1, 0));
  };

  const onSubmit = async (data: BrandFormData) => {
    setSubmitting(true);
    try {
      await api.post("/compliance/brands/apply", {
        entity_type: data.entityType,
        legal_name: data.legalName,
        dba_name: data.dbaName || data.legalName,
        ein: data.ein,
        phone: data.phone,
        email: data.email,
        street: data.street,
        city: data.city,
        state: data.state,
        zip_code: data.zip,
        country: data.country,
        website: data.website || null,
        vertical: data.vertical,
        brand_relationship: data.brandRelationship || null,
        is_main: true,
        stock_symbol: data.stockSymbol || null,
        stock_exchange: data.stockExchange || null,
        business_contact_email: data.businessContactEmail || null,
      });
      toast.success("Brand registration submitted for admin review!");
      navigate("/compliance");
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string } } };
      toast.error(
        error?.response?.data?.detail || "Failed to submit brand registration"
      );
    } finally {
      setSubmitting(false);
    }
  };

  const values = getValues();

  return (
    <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-white">Register Brand</h1>
        <p className="text-gray-400 mt-1">
          Complete your 10DLC brand registration. This will be submitted for
          admin review before being sent to The Campaign Registry.
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
                {/* Step 0: Entity Info */}
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
                      Entity Information
                    </h3>
                    <div>
                      <label className={labelClass}>Entity Type</label>
                      <select
                        {...register("entityType", {
                          required: "Entity type is required",
                        })}
                        className={inputClass}
                      >
                        <option value="" className="bg-navy-900">
                          Select entity type...
                        </option>
                        {entityTypes.map((t) => (
                          <option
                            key={t.value}
                            value={t.value}
                            className="bg-navy-900"
                          >
                            {t.label}
                          </option>
                        ))}
                      </select>
                      {errors.entityType && (
                        <p className={errorClass}>{errors.entityType.message}</p>
                      )}
                    </div>
                    <div>
                      <label className={labelClass}>Legal Business Name</label>
                      <input
                        {...register("legalName", {
                          required: "Legal name is required",
                          minLength: {
                            value: 2,
                            message: "Must be at least 2 characters",
                          },
                        })}
                        placeholder="e.g. BlastWave Technologies Inc."
                        className={inputClass}
                      />
                      {errors.legalName && (
                        <p className={errorClass}>{errors.legalName.message}</p>
                      )}
                    </div>
                    <div>
                      <label className={labelClass}>
                        DBA Name{" "}
                        <span className="text-gray-500">(optional)</span>
                      </label>
                      <input
                        {...register("dbaName")}
                        placeholder="Doing Business As name, if different from legal name"
                        className={inputClass}
                      />
                    </div>
                    <div>
                      <label className={labelClass}>
                        EIN (Employer Identification Number)
                      </label>
                      <input
                        {...register("ein", {
                          required: "EIN is required",
                          pattern: {
                            value: /^\d{2}-?\d{7}$/,
                            message: "Format: XX-XXXXXXX",
                          },
                        })}
                        placeholder="XX-XXXXXXX"
                        className={inputClass}
                      />
                      {errors.ein && (
                        <p className={errorClass}>{errors.ein.message}</p>
                      )}
                    </div>
                  </motion.div>
                )}

                {/* Step 1: Address */}
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
                      Business Address
                    </h3>
                    <div>
                      <label className={labelClass}>Street Address</label>
                      <input
                        {...register("street", {
                          required: "Street address is required",
                        })}
                        placeholder="123 Main Street, Suite 100"
                        className={inputClass}
                      />
                      {errors.street && (
                        <p className={errorClass}>{errors.street.message}</p>
                      )}
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className={labelClass}>City</label>
                        <input
                          {...register("city", {
                            required: "City is required",
                          })}
                          placeholder="San Francisco"
                          className={inputClass}
                        />
                        {errors.city && (
                          <p className={errorClass}>{errors.city.message}</p>
                        )}
                      </div>
                      <div>
                        <label className={labelClass}>State</label>
                        <input
                          {...register("state", {
                            required: "State is required",
                          })}
                          placeholder="CA"
                          className={inputClass}
                        />
                        {errors.state && (
                          <p className={errorClass}>{errors.state.message}</p>
                        )}
                      </div>
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className={labelClass}>ZIP Code</label>
                        <input
                          {...register("zip", {
                            required: "ZIP is required",
                            pattern: {
                              value: /^\d{5}(-\d{4})?$/,
                              message: "Invalid ZIP",
                            },
                          })}
                          placeholder="94105"
                          className={inputClass}
                        />
                        {errors.zip && (
                          <p className={errorClass}>{errors.zip.message}</p>
                        )}
                      </div>
                      <div>
                        <label className={labelClass}>Country</label>
                        <select {...register("country")} className={inputClass}>
                          <option value="US" className="bg-navy-900">
                            United States
                          </option>
                          <option value="CA" className="bg-navy-900">
                            Canada
                          </option>
                        </select>
                      </div>
                    </div>
                  </motion.div>
                )}

                {/* Step 2: Business Details */}
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
                      Business Details
                    </h3>
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className={labelClass}>Contact Phone (E.164)</label>
                        <input
                          {...register("phone", {
                            required: "Phone is required",
                            pattern: {
                              value: /^\+[1-9]\d{1,14}$/,
                              message: "Must be E.164 format (e.g. +15551234567)",
                            },
                          })}
                          placeholder="+15551234567"
                          className={inputClass}
                        />
                        {errors.phone && (
                          <p className={errorClass}>{errors.phone.message}</p>
                        )}
                      </div>
                      <div>
                        <label className={labelClass}>Contact Email</label>
                        <input
                          {...register("email", {
                            required: "Email is required",
                            pattern: {
                              value: /^[^\s@]+@[^\s@]+\.[^\s@]+$/,
                              message: "Invalid email address",
                            },
                          })}
                          placeholder="compliance@example.com"
                          className={inputClass}
                        />
                        {errors.email && (
                          <p className={errorClass}>{errors.email.message}</p>
                        )}
                      </div>
                    </div>
                    <div>
                      <label className={labelClass}>Brand Relationship</label>
                      <select
                        {...register("brandRelationship")}
                        className={inputClass}
                      >
                        <option value="" className="bg-navy-900">
                          Select relationship...
                        </option>
                        {brandRelationships.map((r) => (
                          <option
                            key={r.value}
                            value={r.value}
                            className="bg-navy-900"
                          >
                            {r.label}
                          </option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <label className={labelClass}>
                        Website{" "}
                        <span className="text-gray-500">(optional)</span>
                      </label>
                      <input
                        {...register("website")}
                        placeholder="https://example.com"
                        className={inputClass}
                      />
                    </div>
                    <div>
                      <label className={labelClass}>Business Vertical</label>
                      <select
                        {...register("vertical", {
                          required: "Vertical is required",
                        })}
                        className={inputClass}
                      >
                        <option value="" className="bg-navy-900">
                          Select vertical...
                        </option>
                        {verticals.map((v) => (
                          <option
                            key={v.value}
                            value={v.value}
                            className="bg-navy-900"
                          >
                            {v.label}
                          </option>
                        ))}
                      </select>
                      {errors.vertical && (
                        <p className={errorClass}>{errors.vertical.message}</p>
                      )}
                    </div>
                    <div>
                      <label className={labelClass}>Business Description</label>
                      <textarea
                        {...register("description", {
                          required: "Description is required",
                          minLength: {
                            value: 20,
                            message: "At least 20 characters",
                          },
                        })}
                        rows={3}
                        placeholder="Describe what your company does and how you use SMS messaging..."
                        className={clsx(inputClass, "resize-none")}
                      />
                      {errors.description && (
                        <p className={errorClass}>
                          {errors.description.message}
                        </p>
                      )}
                    </div>

                    {/* Conditional fields for PUBLIC_PROFIT */}
                    {entityType === "PUBLIC_PROFIT" && (
                      <>
                        <div className="grid grid-cols-2 gap-4">
                          <div>
                            <label className={labelClass}>Stock Symbol</label>
                            <input
                              {...register("stockSymbol")}
                              placeholder="e.g. AAPL"
                              className={inputClass}
                            />
                          </div>
                          <div>
                            <label className={labelClass}>Stock Exchange</label>
                            <input
                              {...register("stockExchange")}
                              placeholder="e.g. NASDAQ"
                              className={inputClass}
                            />
                          </div>
                        </div>
                        <div>
                          <label className={labelClass}>
                            Business Contact Email
                          </label>
                          <input
                            {...register("businessContactEmail")}
                            placeholder="ir@example.com"
                            className={inputClass}
                          />
                        </div>
                      </>
                    )}
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
                      brand registration will be reviewed by an admin before
                      being submitted to The Campaign Registry.
                    </p>
                    <div className="space-y-4">
                      <div className="bg-white/5 rounded-xl p-4">
                        <h4 className="text-xs text-gray-500 uppercase tracking-wider mb-3">
                          Entity Information
                        </h4>
                        <div className="grid grid-cols-2 gap-3 text-sm">
                          <div>
                            <span className="text-gray-500">Type:</span>{" "}
                            <span className="text-white ml-1">
                              {entityTypes.find(
                                (t) => t.value === values.entityType
                              )?.label || "-"}
                            </span>
                          </div>
                          <div>
                            <span className="text-gray-500">EIN:</span>{" "}
                            <span className="text-white ml-1 font-mono">
                              {values.ein || "-"}
                            </span>
                          </div>
                          <div className="col-span-2">
                            <span className="text-gray-500">Legal Name:</span>{" "}
                            <span className="text-white ml-1">
                              {values.legalName || "-"}
                            </span>
                          </div>
                          {values.dbaName && (
                            <div className="col-span-2">
                              <span className="text-gray-500">DBA Name:</span>{" "}
                              <span className="text-white ml-1">
                                {values.dbaName}
                              </span>
                            </div>
                          )}
                        </div>
                      </div>
                      <div className="bg-white/5 rounded-xl p-4">
                        <h4 className="text-xs text-gray-500 uppercase tracking-wider mb-3">
                          Address
                        </h4>
                        <p className="text-sm text-white">
                          {values.street || "-"}
                          <br />
                          {values.city || "-"}, {values.state || "-"}{" "}
                          {values.zip || "-"}
                          <br />
                          {values.country || "-"}
                        </p>
                      </div>
                      <div className="bg-white/5 rounded-xl p-4">
                        <h4 className="text-xs text-gray-500 uppercase tracking-wider mb-3">
                          Business Details
                        </h4>
                        <div className="space-y-2 text-sm">
                          <div>
                            <span className="text-gray-500">Phone:</span>{" "}
                            <span className="text-white ml-1 font-mono">
                              {values.phone || "-"}
                            </span>
                          </div>
                          <div>
                            <span className="text-gray-500">Email:</span>{" "}
                            <span className="text-white ml-1">
                              {values.email || "-"}
                            </span>
                          </div>
                          <div>
                            <span className="text-gray-500">
                              Brand Relationship:
                            </span>{" "}
                            <span className="text-white ml-1">
                              {brandRelationships.find(
                                (r) => r.value === values.brandRelationship
                              )?.label || "-"}
                            </span>
                          </div>
                          {values.website && (
                            <div>
                              <span className="text-gray-500">Website:</span>{" "}
                              <span className="text-blue-400 ml-1">
                                {values.website}
                              </span>
                            </div>
                          )}
                          <div>
                            <span className="text-gray-500">Vertical:</span>{" "}
                            <span className="text-white ml-1">
                              {verticals.find(
                                (v) => v.value === values.vertical
                              )?.label || "-"}
                            </span>
                          </div>
                          <div>
                            <span className="text-gray-500">Description:</span>{" "}
                            <span className="text-gray-300 ml-1">
                              {values.description || "-"}
                            </span>
                          </div>
                          {values.stockSymbol && (
                            <div>
                              <span className="text-gray-500">
                                Stock Symbol:
                              </span>{" "}
                              <span className="text-white ml-1">
                                {values.stockSymbol}
                              </span>
                            </div>
                          )}
                          {values.stockExchange && (
                            <div>
                              <span className="text-gray-500">
                                Stock Exchange:
                              </span>{" "}
                              <span className="text-white ml-1">
                                {values.stockExchange}
                              </span>
                            </div>
                          )}
                          {values.businessContactEmail && (
                            <div>
                              <span className="text-gray-500">
                                Business Contact Email:
                              </span>{" "}
                              <span className="text-white ml-1">
                                {values.businessContactEmail}
                              </span>
                            </div>
                          )}
                        </div>
                      </div>

                      <div className="bg-amber-500/10 border border-amber-500/20 rounded-xl p-4">
                        <p className="text-sm text-amber-300">
                          This registration will be submitted for admin review.
                          You will be notified once it has been approved and
                          submitted to TCR.
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
