import { useState, useCallback } from "react";
import { useDropzone } from "react-dropzone";
import { motion, AnimatePresence } from "framer-motion";
import { useNavigate } from "react-router-dom";
import { useMutation } from "@tanstack/react-query";
import {
  ChevronLeft,
  ChevronRight,
  Upload,
  FileSpreadsheet,
  ArrowRight,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  X,
} from "lucide-react";
import clsx from "clsx";
import toast from "react-hot-toast";
import GlassCard from "../components/ui/GlassCard";
import api from "../lib/api";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface ParsedCSV {
  headers: string[];
  rows: string[][];
}

interface ColumnMapping {
  [csvHeader: string]: string;
}

interface ImportResult {
  total: number;
  imported: number;
  failed: number;
  errors: { row: number; reason: string }[];
}

/* ------------------------------------------------------------------ */
/*  Constants                                                          */
/* ------------------------------------------------------------------ */

const fieldOptions = [
  { value: "", label: "-- Skip --" },
  { value: "first_name", label: "First Name" },
  { value: "last_name", label: "Last Name" },
  { value: "phone", label: "Phone Number" },
  { value: "email", label: "Email" },
  { value: "company", label: "Company" },
  { value: "city", label: "City" },
  { value: "state", label: "State" },
  { value: "zip", label: "Zip Code" },
  { value: "custom_1", label: "Custom Field 1" },
  { value: "custom_2", label: "Custom Field 2" },
  { value: "custom_3", label: "Custom Field 3" },
];

const steps = [
  { label: "Upload", icon: Upload },
  { label: "Map Columns", icon: ArrowRight },
  { label: "Preview", icon: FileSpreadsheet },
  { label: "Import", icon: CheckCircle2 },
];

/* ------------------------------------------------------------------ */
/*  CSV Parser                                                         */
/* ------------------------------------------------------------------ */

function parseCSVLine(line: string): string[] {
  const result: string[] = [];
  let current = "";
  let inQuotes = false;
  for (const char of line) {
    if (char === '"') {
      inQuotes = !inQuotes;
    } else if (char === "," && !inQuotes) {
      result.push(current.trim());
      current = "";
    } else {
      current += char;
    }
  }
  result.push(current.trim());
  return result;
}

function parseCSV(text: string): ParsedCSV {
  const lines = text.trim().split(/\r?\n/);
  const headers = parseCSVLine(lines[0]);
  const rows = lines.slice(1).map((line) => parseCSVLine(line));
  return { headers, rows };
}

function autoMap(headers: string[]): ColumnMapping {
  const mapping: ColumnMapping = {};
  const patterns: Record<string, RegExp> = {
    first_name: /first.?name|fname|given.?name/i,
    last_name: /last.?name|lname|surname|family.?name/i,
    phone: /phone|mobile|cell|tel/i,
    email: /email|e-mail/i,
    company: /company|org|business/i,
    city: /city|town/i,
    state: /state|province|region/i,
    zip: /zip|postal|postcode/i,
  };
  headers.forEach((header) => {
    for (const [field, regex] of Object.entries(patterns)) {
      if (regex.test(header)) {
        mapping[header] = field;
        return;
      }
    }
    mapping[header] = "";
  });
  return mapping;
}

/* ------------------------------------------------------------------ */
/*  Main Component                                                     */
/* ------------------------------------------------------------------ */

export default function ContactImport() {
  const navigate = useNavigate();
  const [step, setStep] = useState(0);
  const [file, setFile] = useState<File | null>(null);
  const [csv, setCsv] = useState<ParsedCSV | null>(null);
  const [mapping, setMapping] = useState<ColumnMapping>({});
  const [importResult, setImportResult] = useState<ImportResult | null>(null);
  const [direction, setDirection] = useState(0);

  /* -- File drop handler -- */
  const onDrop = useCallback((acceptedFiles: File[]) => {
    const f = acceptedFiles[0];
    if (!f) return;
    setFile(f);
    const reader = new FileReader();
    reader.onload = (e) => {
      const text = e.target?.result as string;
      const parsed = parseCSV(text);
      setCsv(parsed);
      setMapping(autoMap(parsed.headers));
    };
    reader.readAsText(f);
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { "text/csv": [".csv"], "application/vnd.ms-excel": [".csv"] },
    maxFiles: 1,
  });

  /* -- Import mutation -- */
  const importMutation = useMutation({
    mutationFn: async () => {
      const formData = new FormData();
      formData.append("file", file!);
      formData.append("mapping", JSON.stringify(mapping));
      const res = await api.post("/contacts/import", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      return res.data as ImportResult;
    },
    onSuccess: (data) => {
      setImportResult(data);
      toast.success(`Imported ${data.imported} contacts successfully`);
    },
    onError: () => {
      toast.error("Import failed. Please try again.");
    },
  });

  /* -- Navigation -- */
  const goNext = () => {
    setDirection(1);
    if (step === 3) return;
    if (step === 2) {
      importMutation.mutate();
    }
    setStep((s) => s + 1);
  };
  const goBack = () => {
    setDirection(-1);
    setStep((s) => Math.max(0, s - 1));
  };

  const canNext = () => {
    switch (step) {
      case 0: return file !== null && csv !== null;
      case 1: return Object.values(mapping).some((v) => v === "phone");
      case 2: return true;
      default: return false;
    }
  };

  const slideVariants = {
    enter: (d: number) => ({ x: d > 0 ? 300 : -300, opacity: 0 }),
    center: { x: 0, opacity: 1 },
    exit: (d: number) => ({ x: d < 0 ? 300 : -300, opacity: 0 }),
  };

  /* ---------------------------------------------------------------- */

  return (
    <div>
      {/* Header */}
      <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} className="mb-8">
        <button
          onClick={() => navigate("/contacts")}
          className="flex items-center gap-1 text-sm text-gray-400 hover:text-white transition-colors mb-3"
        >
          <ChevronLeft className="w-4 h-4" /> Back to Contacts
        </button>
        <h1 className="text-3xl font-bold text-white">Import Contacts</h1>
        <p className="text-gray-400 mt-1">Upload a CSV file and map columns to contact fields.</p>
      </motion.div>

      {/* Progress */}
      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="mb-10">
        <div className="flex items-center justify-between max-w-2xl mx-auto">
          {steps.map((s, i) => {
            const Icon = s.icon;
            const isActive = i === step;
            const isDone = i < step;
            return (
              <div key={s.label} className="flex items-center">
                <div className="flex flex-col items-center">
                  <motion.div
                    animate={{ scale: isActive ? 1.15 : 1 }}
                    className={clsx(
                      "w-10 h-10 rounded-full flex items-center justify-center border-2 transition-colors",
                      isDone
                        ? "border-blue-500 bg-blue-500"
                        : isActive
                        ? "border-blue-500 bg-blue-500/30"
                        : "border-white/20 bg-white/5"
                    )}
                  >
                    {isDone ? (
                      <CheckCircle2 className="w-5 h-5 text-white" />
                    ) : (
                      <Icon className={clsx("w-5 h-5", isActive ? "text-blue-400" : "text-gray-500")} />
                    )}
                  </motion.div>
                  <span className={clsx("text-xs mt-2 font-medium", isActive ? "text-white" : isDone ? "text-blue-400" : "text-gray-500")}>
                    {s.label}
                  </span>
                </div>
                {i < steps.length - 1 && (
                  <div className="w-16 sm:w-24 lg:w-32 h-0.5 mx-2 mt-[-1rem]">
                    <div className="h-full bg-white/10 rounded-full overflow-hidden">
                      <motion.div
                        animate={{ width: isDone ? "100%" : "0%" }}
                        className="h-full bg-blue-500 rounded-full"
                        transition={{ duration: 0.5 }}
                      />
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </motion.div>

      {/* Step Content */}
      <GlassCard className="mb-8 min-h-[400px] overflow-hidden">
        <AnimatePresence mode="wait" custom={direction}>
          <motion.div
            key={step}
            custom={direction}
            variants={slideVariants}
            initial="enter"
            animate="center"
            exit="exit"
            transition={{ type: "tween", duration: 0.3 }}
          >
            {/* Step 0: Upload */}
            {step === 0 && (
              <div className="max-w-xl mx-auto py-8">
                <div
                  {...getRootProps()}
                  className={clsx(
                    "border-2 border-dashed rounded-2xl p-12 flex flex-col items-center gap-4 cursor-pointer transition-all text-center",
                    isDragActive
                      ? "border-blue-500 bg-blue-500/10"
                      : file
                      ? "border-emerald-500/50 bg-emerald-500/5"
                      : "border-white/15 hover:border-blue-500/30 hover:bg-blue-500/5"
                  )}
                >
                  <input {...getInputProps()} />
                  {file ? (
                    <>
                      <motion.div
                        initial={{ scale: 0 }}
                        animate={{ scale: 1 }}
                        transition={{ type: "spring", stiffness: 300, damping: 20 }}
                        className="w-16 h-16 rounded-2xl bg-emerald-500/20 flex items-center justify-center"
                      >
                        <FileSpreadsheet className="w-8 h-8 text-emerald-400" />
                      </motion.div>
                      <div>
                        <p className="text-white font-semibold">{file.name}</p>
                        <p className="text-sm text-gray-400 mt-1">
                          {(file.size / 1024).toFixed(1)} KB &middot; {csv?.rows.length.toLocaleString()} rows &middot; {csv?.headers.length} columns
                        </p>
                      </div>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          setFile(null);
                          setCsv(null);
                          setMapping({});
                        }}
                        className="flex items-center gap-1 text-xs text-rose-400 hover:text-rose-300 transition-colors"
                      >
                        <X className="w-3 h-3" /> Remove file
                      </button>
                    </>
                  ) : (
                    <>
                      <motion.div
                        animate={{ y: [0, -8, 0] }}
                        transition={{ repeat: Infinity, duration: 2, ease: "easeInOut" }}
                        className="w-16 h-16 rounded-2xl bg-blue-500/20 flex items-center justify-center"
                      >
                        <Upload className="w-8 h-8 text-blue-400" />
                      </motion.div>
                      <div>
                        <p className="text-white font-semibold">
                          {isDragActive ? "Drop your file here" : "Drag & drop a CSV file"}
                        </p>
                        <p className="text-sm text-gray-500 mt-1">
                          or <span className="text-blue-400">click to browse</span> your files
                        </p>
                      </div>
                      <p className="text-xs text-gray-600">Supports .csv files up to 50MB</p>
                    </>
                  )}
                </div>
              </div>
            )}

            {/* Step 1: Column Mapping */}
            {step === 1 && csv && (
              <div className="max-w-2xl mx-auto py-4">
                <div className="text-center mb-6">
                  <h3 className="text-lg font-semibold text-white">Map Your Columns</h3>
                  <p className="text-sm text-gray-400 mt-1">Match each CSV column to a contact field. Phone number is required.</p>
                </div>
                <div className="space-y-3">
                  {csv.headers.map((header) => (
                    <motion.div
                      key={header}
                      initial={{ opacity: 0, x: -20 }}
                      animate={{ opacity: 1, x: 0 }}
                      className="flex items-center gap-4 p-3 bg-white/5 rounded-xl border border-white/10"
                    >
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <FileSpreadsheet className="w-4 h-4 text-gray-500 shrink-0" />
                          <span className="text-sm text-white font-medium truncate">{header}</span>
                        </div>
                        <p className="text-xs text-gray-600 mt-0.5 truncate ml-6">
                          Sample: {csv.rows[0]?.[csv.headers.indexOf(header)] || "empty"}
                        </p>
                      </div>
                      <ArrowRight className="w-4 h-4 text-gray-600 shrink-0" />
                      <select
                        value={mapping[header] || ""}
                        onChange={(e) => setMapping((m) => ({ ...m, [header]: e.target.value }))}
                        className={clsx(
                          "w-48 px-3 py-2 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/50 border [color-scheme:dark]",
                          mapping[header]
                            ? "bg-blue-500/10 border-blue-500/30 text-blue-400"
                            : "bg-white/5 border-white/10 text-gray-500"
                        )}
                      >
                        {fieldOptions.map((opt) => (
                          <option key={opt.value} value={opt.value} className="bg-gray-900">
                            {opt.label}
                          </option>
                        ))}
                      </select>
                    </motion.div>
                  ))}
                </div>
                {!Object.values(mapping).includes("phone") && (
                  <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className="flex items-center gap-2 mt-4 p-3 bg-amber-500/10 border border-amber-500/30 rounded-xl"
                  >
                    <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0" />
                    <p className="text-sm text-amber-400">You must map at least one column to "Phone Number" to continue.</p>
                  </motion.div>
                )}
              </div>
            )}

            {/* Step 2: Preview */}
            {step === 2 && csv && (
              <div className="py-4">
                <div className="text-center mb-6">
                  <h3 className="text-lg font-semibold text-white">Preview Import Data</h3>
                  <p className="text-sm text-gray-400 mt-1">Showing first 5 rows with your mapped fields.</p>
                </div>
                <div className="overflow-x-auto rounded-xl border border-white/10">
                  <table className="w-full">
                    <thead>
                      <tr className="bg-white/5">
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-10">#</th>
                        {Object.entries(mapping)
                          .filter(([_, field]) => field)
                          .map(([csvHeader, field]) => (
                            <th key={csvHeader} className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                              <div className="flex flex-col gap-0.5">
                                <span className="text-blue-400">{fieldOptions.find((f) => f.value === field)?.label}</span>
                                <span className="text-gray-600 normal-case font-normal">{csvHeader}</span>
                              </div>
                            </th>
                          ))}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-white/5">
                      {csv.rows.slice(0, 5).map((row, ri) => (
                        <motion.tr
                          key={ri}
                          initial={{ opacity: 0, y: 10 }}
                          animate={{ opacity: 1, y: 0 }}
                          transition={{ delay: ri * 0.05 }}
                          className="hover:bg-white/5"
                        >
                          <td className="px-4 py-3 text-xs text-gray-600 font-mono">{ri + 1}</td>
                          {Object.entries(mapping)
                            .filter(([_, field]) => field)
                            .map(([csvHeader]) => {
                              const colIdx = csv.headers.indexOf(csvHeader);
                              return (
                                <td key={csvHeader} className="px-4 py-3 text-sm text-gray-300">
                                  {row[colIdx] || <span className="text-gray-600 italic">empty</span>}
                                </td>
                              );
                            })}
                        </motion.tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <p className="text-xs text-gray-500 mt-3 text-center">
                  Total rows to import: <span className="text-white font-medium">{csv.rows.length.toLocaleString()}</span>
                </p>
              </div>
            )}

            {/* Step 3: Import Results */}
            {step === 3 && (
              <div className="max-w-md mx-auto py-8 text-center">
                {importMutation.isPending && !importResult ? (
                  <div className="space-y-6">
                    <motion.div
                      animate={{ rotate: 360 }}
                      transition={{ repeat: Infinity, duration: 1.5, ease: "linear" }}
                      className="w-16 h-16 mx-auto border-4 border-blue-500 border-t-transparent rounded-full"
                    />
                    <div>
                      <p className="text-lg font-semibold text-white">Importing contacts...</p>
                      <p className="text-sm text-gray-400 mt-1">This may take a moment.</p>
                    </div>
                    {/* Animated progress bar */}
                    <div className="w-full h-2 bg-white/10 rounded-full overflow-hidden">
                      <motion.div
                        initial={{ width: "0%" }}
                        animate={{ width: "90%" }}
                        transition={{ duration: 10, ease: "easeOut" }}
                        className="h-full bg-gradient-to-r from-blue-500 to-indigo-600 rounded-full"
                      />
                    </div>
                  </div>
                ) : importMutation.isError ? (
                  <div className="space-y-4">
                    <motion.div
                      initial={{ scale: 0 }}
                      animate={{ scale: 1 }}
                      transition={{ type: "spring" }}
                      className="w-16 h-16 mx-auto rounded-2xl bg-rose-500/20 flex items-center justify-center"
                    >
                      <XCircle className="w-8 h-8 text-rose-400" />
                    </motion.div>
                    <p className="text-lg font-semibold text-white">Import Failed</p>
                    <p className="text-sm text-gray-400">Something went wrong. Please try again.</p>
                    <button
                      onClick={() => { setStep(0); setFile(null); setCsv(null); }}
                      className="px-5 py-2 rounded-xl text-sm font-medium text-white bg-white/10 hover:bg-white/15 transition-colors"
                    >
                      Start Over
                    </button>
                  </div>
                ) : importResult ? (
                  <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className="space-y-6"
                  >
                    <motion.div
                      initial={{ scale: 0 }}
                      animate={{ scale: 1 }}
                      transition={{ type: "spring", stiffness: 300, damping: 20 }}
                      className="w-16 h-16 mx-auto rounded-2xl bg-emerald-500/20 flex items-center justify-center"
                    >
                      <CheckCircle2 className="w-8 h-8 text-emerald-400" />
                    </motion.div>
                    <div>
                      <p className="text-lg font-semibold text-white">Import Complete</p>
                      <p className="text-sm text-gray-400 mt-1">Your contacts have been processed.</p>
                    </div>

                    {/* Results Summary */}
                    <div className="grid grid-cols-3 gap-4">
                      <div className="p-4 bg-white/5 rounded-xl border border-white/10">
                        <p className="text-2xl font-bold font-mono text-white">{importResult.total.toLocaleString()}</p>
                        <p className="text-xs text-gray-400 mt-1">Total Rows</p>
                      </div>
                      <div className="p-4 bg-emerald-500/10 rounded-xl border border-emerald-500/30">
                        <p className="text-2xl font-bold font-mono text-emerald-400">{importResult.imported.toLocaleString()}</p>
                        <p className="text-xs text-emerald-400/70 mt-1">Imported</p>
                      </div>
                      <div className="p-4 bg-rose-500/10 rounded-xl border border-rose-500/30">
                        <p className="text-2xl font-bold font-mono text-rose-400">{importResult.failed.toLocaleString()}</p>
                        <p className="text-xs text-rose-400/70 mt-1">Failed</p>
                      </div>
                    </div>

                    {/* Error details */}
                    {importResult.errors.length > 0 && (
                      <div className="text-left mt-4">
                        <p className="text-xs font-medium text-gray-400 mb-2">Errors:</p>
                        <div className="max-h-32 overflow-y-auto space-y-1">
                          {importResult.errors.slice(0, 10).map((err, i) => (
                            <p key={i} className="text-xs text-rose-400/80">
                              Row {err.row}: {err.reason}
                            </p>
                          ))}
                          {importResult.errors.length > 10 && (
                            <p className="text-xs text-gray-500">...and {importResult.errors.length - 10} more</p>
                          )}
                        </div>
                      </div>
                    )}

                    {/* Actions */}
                    <div className="flex gap-3 justify-center pt-2">
                      <button
                        onClick={() => navigate("/contacts")}
                        className="px-5 py-2.5 rounded-xl text-sm font-semibold text-white bg-gradient-to-r from-blue-500 to-indigo-600 hover:from-blue-600 hover:to-indigo-700 shadow-lg shadow-blue-500/25 transition-all"
                      >
                        View Contacts
                      </button>
                      <button
                        onClick={() => { setStep(0); setFile(null); setCsv(null); setImportResult(null); }}
                        className="px-5 py-2.5 rounded-xl text-sm font-medium text-gray-300 bg-white/5 border border-white/10 hover:bg-white/10 transition-all"
                      >
                        Import More
                      </button>
                    </div>
                  </motion.div>
                ) : null}
              </div>
            )}
          </motion.div>
        </AnimatePresence>
      </GlassCard>

      {/* Navigation */}
      {step < 3 && (
        <div className="flex items-center justify-between">
          <motion.button
            whileHover={{ scale: 1.03 }}
            whileTap={{ scale: 0.97 }}
            onClick={goBack}
            disabled={step === 0}
            className={clsx(
              "flex items-center gap-2 px-5 py-2.5 rounded-xl font-semibold text-sm transition-all",
              step === 0
                ? "opacity-0 pointer-events-none"
                : "text-gray-300 bg-white/5 border border-white/10 hover:bg-white/10"
            )}
          >
            <ChevronLeft className="w-4 h-4" /> Back
          </motion.button>
          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={goNext}
            disabled={!canNext()}
            className={clsx(
              "flex items-center gap-2 px-6 py-2.5 rounded-xl font-semibold text-sm text-white shadow-lg transition-all",
              canNext()
                ? "bg-gradient-to-r from-blue-500 to-indigo-600 hover:from-blue-600 hover:to-indigo-700 shadow-blue-500/25"
                : "bg-gray-700 cursor-not-allowed opacity-50"
            )}
          >
            {step === 2 && importMutation.isPending ? "Importing..." : step === 2 ? "Start Import" : "Next"}
            {!(step === 2 && importMutation.isPending) && <ChevronRight className="w-4 h-4" />}
          </motion.button>
        </div>
      )}
    </div>
  );
}
