import { useState, useRef, useEffect } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { motion } from "framer-motion";
import toast from "react-hot-toast";
import {
  Search,
  Send,
  Phone,
  User,
  Image as ImageIcon,
  Paperclip,
  MessageSquare,
} from "lucide-react";
import clsx from "clsx";
import { formatDistanceToNow, format } from "date-fns";
import api from "../lib/api";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface Conversation {
  id: string;
  contact_name: string;
  contact_phone: string;
  last_message: string;
  last_message_at: string;
  unread_count: number;
  status: "open" | "closed";
  assigned_to: string | null;
}

interface Message {
  id: string;
  conversation_id: string;
  direction: "inbound" | "outbound";
  body: string;
  media_url: string | null;
  created_at: string;
  status: "delivered" | "sent" | "failed";
}

type ConversationFilter = "all" | "open" | "closed";

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

export default function Inbox() {
  const [activeConvo, setActiveConvo] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [filterStatus, setFilterStatus] = useState<ConversationFilter>("all");
  const [messageInput, setMessageInput] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);

  /* -- Conversations query -- */
  const { data: conversations = [], error } = useQuery<Conversation[]>({
    queryKey: ["conversations"],
    queryFn: async () => {
      const res = await api.get("/inbox/");
      return res.data.conversations ?? res.data;
    },
  });

  if (error) return <div className="p-8 text-center text-red-400">Failed to load data. Please try again.</div>;

  /* -- Messages query for selected conversation -- */
  const { data: messages = [] } = useQuery<Message[]>({
    queryKey: ["messages", activeConvo],
    queryFn: async () => {
      if (!activeConvo) return [];
      const res = await api.get(`/inbox/${activeConvo}/messages`);
      return res.data.messages ?? res.data;
    },
    enabled: !!activeConvo,
  });

  const activeConversation = conversations.find((c) => c.id === activeConvo);

  /* -- Scroll to bottom when messages change -- */
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  /* -- Filter conversations -- */
  const filteredConversations = conversations.filter((c) => {
    const matchesSearch =
      !search ||
      c.contact_name.toLowerCase().includes(search.toLowerCase()) ||
      c.contact_phone.includes(search);
    const matchesFilter = filterStatus === "all" || c.status === filterStatus;
    return matchesSearch && matchesFilter;
  });

  const queryClient = useQueryClient();

  /* -- Send message handler -- */
  const handleSend = async () => {
    if (!messageInput.trim() || !activeConvo) return;
    const text = messageInput;
    setMessageInput("");
    try {
      await api.post(`/inbox/${activeConvo}/reply`, { body: text });
      queryClient.invalidateQueries({ queryKey: ["messages", activeConvo] });
      queryClient.invalidateQueries({ queryKey: ["conversations"] });
      toast.success("Message sent");
    } catch {
      setMessageInput(text);
      toast.error("Failed to send message");
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
      {/* Header */}
      <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} className="mb-6">
        <h1 className="text-3xl font-bold text-white">Inbox</h1>
        <p className="text-gray-400 mt-1">Two-way messaging with your contacts.</p>
      </motion.div>

      {/* Split Panel */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="flex rounded-2xl border border-white/10 overflow-hidden bg-white/5 backdrop-blur-xl shadow-xl shadow-black/20"
        style={{ height: "calc(100vh - 200px)", minHeight: 500 }}
      >
        {/* Left Panel — Conversation List */}
        <div className="w-80 lg:w-96 border-r border-white/10 flex flex-col shrink-0">
          {/* Search */}
          <div className="p-4 border-b border-white/5">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
              <input
                type="text"
                placeholder="Search conversations..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="w-full pl-10 pr-4 py-2.5 bg-white/5 border border-white/10 rounded-xl text-sm text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50"
              />
            </div>

            {/* Filter Tabs */}
            <div className="flex gap-1 mt-3 bg-white/5 rounded-lg p-0.5">
              {(["all", "open", "closed"] as const).map((f) => (
                <button
                  key={f}
                  onClick={() => setFilterStatus(f)}
                  className={clsx(
                    "flex-1 py-1.5 text-xs font-medium rounded-md transition-colors",
                    filterStatus === f
                      ? "bg-white/10 text-white"
                      : "text-gray-500 hover:text-gray-300"
                  )}
                >
                  {f.charAt(0).toUpperCase() + f.slice(1)}
                </button>
              ))}
            </div>
          </div>

          {/* Conversation Cards */}
          <div className="flex-1 overflow-y-auto">
            {filteredConversations.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full text-gray-600">
                <MessageSquare className="w-8 h-8 mb-2 opacity-40" />
                <p className="text-sm">No conversations</p>
              </div>
            ) : (
              filteredConversations.map((convo) => {
                const isActive = convo.id === activeConvo;
                return (
                  <motion.button
                    key={convo.id}
                    onClick={() => setActiveConvo(convo.id)}
                    whileHover={{ backgroundColor: "rgba(255,255,255,0.03)" }}
                    className={clsx(
                      "w-full text-left px-4 py-3.5 border-l-2 transition-all",
                      isActive
                        ? "bg-blue-500/5 border-l-blue-500"
                        : "border-l-transparent hover:bg-white/[0.02]"
                    )}
                  >
                    <div className="flex items-start gap-3">
                      {/* Avatar */}
                      <div className={clsx(
                        "w-10 h-10 rounded-full flex items-center justify-center shrink-0 text-sm font-bold",
                        isActive
                          ? "bg-blue-500/20 text-blue-400"
                          : "bg-white/10 text-gray-400"
                      )}>
                        {convo.contact_name
                          .split(" ")
                          .map((n) => n[0])
                          .slice(0, 2)
                          .join("")}
                      </div>

                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between">
                          <p className={clsx("text-sm font-semibold truncate", isActive ? "text-white" : "text-gray-200")}>
                            {convo.contact_name}
                          </p>
                          <span className="text-[11px] text-gray-500 shrink-0 ml-2">
                            {formatDistanceToNow(new Date(convo.last_message_at), { addSuffix: false })}
                          </span>
                        </div>
                        <div className="flex items-center justify-between mt-0.5">
                          <p className="text-xs text-gray-500 truncate pr-2">{convo.last_message}</p>
                          {convo.unread_count > 0 && (
                            <motion.span
                              initial={{ scale: 0 }}
                              animate={{ scale: 1 }}
                              className="w-5 h-5 rounded-full bg-blue-500 text-white text-[10px] font-bold flex items-center justify-center shrink-0"
                            >
                              {convo.unread_count}
                            </motion.span>
                          )}
                        </div>
                      </div>
                    </div>
                  </motion.button>
                );
              })
            )}
          </div>
        </div>

        {/* Right Panel — Message Thread */}
        <div className="flex-1 flex flex-col min-w-0">
          {activeConversation ? (
            <>
              {/* Contact Header */}
              <div className="px-6 py-4 border-b border-white/5 flex items-center justify-between bg-white/[0.02]">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-full bg-gradient-to-br from-blue-500/30 to-indigo-600/30 flex items-center justify-center text-sm font-bold text-blue-400">
                    {activeConversation.contact_name
                      .split(" ")
                      .map((n) => n[0])
                      .slice(0, 2)
                      .join("")}
                  </div>
                  <div>
                    <p className="text-white font-semibold text-sm">{activeConversation.contact_name}</p>
                    <div className="flex items-center gap-2 text-xs text-gray-500">
                      <Phone className="w-3 h-3" />
                      <span className="font-mono">{activeConversation.contact_phone}</span>
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  {activeConversation.assigned_to && (
                    <div className="flex items-center gap-1.5 px-2.5 py-1 bg-white/5 border border-white/10 rounded-lg">
                      <User className="w-3 h-3 text-gray-500" />
                      <span className="text-xs text-gray-400">{activeConversation.assigned_to}</span>
                    </div>
                  )}
                  <span className={clsx(
                    "px-2.5 py-1 rounded-full text-xs font-medium",
                    activeConversation.status === "open"
                      ? "bg-emerald-500/20 text-emerald-400"
                      : "bg-gray-500/20 text-gray-400"
                  )}>
                    {activeConversation.status === "open" ? "Open" : "Closed"}
                  </span>
                </div>
              </div>

              {/* Messages */}
              <div className="flex-1 overflow-y-auto px-6 py-4 space-y-3">
                {messages.map((msg, i) => {
                  const isOutbound = msg.direction === "outbound";
                  const showTimestamp =
                    i === 0 ||
                    new Date(msg.created_at).getTime() -
                      new Date(messages[i - 1].created_at).getTime() >
                      300000; // 5min gap
                  return (
                    <div key={msg.id}>
                      {showTimestamp && (
                        <div className="flex justify-center my-4">
                          <span className="px-3 py-1 bg-white/5 rounded-full text-[10px] text-gray-600 font-medium">
                            {format(new Date(msg.created_at), "MMM d, h:mm a")}
                          </span>
                        </div>
                      )}
                      <motion.div
                        initial={{ opacity: 0, y: 10, scale: 0.95 }}
                        animate={{ opacity: 1, y: 0, scale: 1 }}
                        transition={{ delay: i * 0.02 }}
                        className={clsx("flex", isOutbound ? "justify-end" : "justify-start")}
                      >
                        <div
                          className={clsx(
                            "max-w-[70%] px-4 py-2.5 text-sm leading-relaxed",
                            isOutbound
                              ? "bg-blue-500 text-white rounded-2xl rounded-br-md"
                              : "bg-white/10 text-gray-100 rounded-2xl rounded-bl-md"
                          )}
                        >
                          {/* MMS Image */}
                          {msg.media_url && (
                            <div className="mb-2">
                              <img
                                src={msg.media_url}
                                alt="MMS"
                                className="max-w-[240px] rounded-lg border border-white/10"
                              />
                            </div>
                          )}
                          <p>{msg.body}</p>
                          <div className={clsx("flex items-center gap-1 mt-1", isOutbound ? "justify-end" : "justify-start")}>
                            <span className="text-[10px] opacity-50">
                              {format(new Date(msg.created_at), "h:mm a")}
                            </span>
                            {isOutbound && msg.status === "delivered" && (
                              <span className="text-[10px] opacity-50">Delivered</span>
                            )}
                            {isOutbound && msg.status === "failed" && (
                              <span className="text-[10px] text-rose-300">Failed</span>
                            )}
                          </div>
                        </div>
                      </motion.div>
                    </div>
                  );
                })}

                {/* Typing indicator placeholder */}
                {false && (
                  <div className="flex justify-start">
                    <div className="bg-white/10 rounded-2xl rounded-bl-md px-4 py-3">
                      <div className="flex gap-1">
                        <motion.div
                          animate={{ y: [0, -4, 0] }}
                          transition={{ repeat: Infinity, duration: 0.8, delay: 0 }}
                          className="w-2 h-2 rounded-full bg-gray-400"
                        />
                        <motion.div
                          animate={{ y: [0, -4, 0] }}
                          transition={{ repeat: Infinity, duration: 0.8, delay: 0.15 }}
                          className="w-2 h-2 rounded-full bg-gray-400"
                        />
                        <motion.div
                          animate={{ y: [0, -4, 0] }}
                          transition={{ repeat: Infinity, duration: 0.8, delay: 0.3 }}
                          className="w-2 h-2 rounded-full bg-gray-400"
                        />
                      </div>
                    </div>
                  </div>
                )}

                <div ref={messagesEndRef} />
              </div>

              {/* Message Input */}
              <div className="px-6 py-4 border-t border-white/5 bg-white/[0.02]">
                <div className="flex items-end gap-3">
                  <div className="flex-1 relative">
                    <textarea
                      value={messageInput}
                      onChange={(e) => setMessageInput(e.target.value)}
                      onKeyDown={handleKeyDown}
                      placeholder="Type a message..."
                      rows={1}
                      className="w-full px-4 py-3 pr-20 bg-white/5 border border-white/10 rounded-xl text-sm text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50 resize-none"
                      style={{ minHeight: 44, maxHeight: 120 }}
                    />
                    <div className="absolute right-2 bottom-2 flex items-center gap-1">
                      <button className="p-1.5 rounded-lg hover:bg-white/10 transition-colors">
                        <Paperclip className="w-4 h-4 text-gray-500" />
                      </button>
                      <button className="p-1.5 rounded-lg hover:bg-white/10 transition-colors">
                        <ImageIcon className="w-4 h-4 text-gray-500" />
                      </button>
                    </div>
                  </div>
                  <motion.button
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                    onClick={handleSend}
                    disabled={!messageInput.trim()}
                    className={clsx(
                      "w-11 h-11 rounded-xl flex items-center justify-center transition-all shrink-0",
                      messageInput.trim()
                        ? "bg-gradient-to-r from-blue-500 to-indigo-600 shadow-lg shadow-blue-500/25 text-white"
                        : "bg-white/5 text-gray-600"
                    )}
                  >
                    <Send className="w-4 h-4" />
                  </motion.button>
                </div>
              </div>
            </>
          ) : (
            /* Empty State */
            <div className="flex-1 flex flex-col items-center justify-center text-gray-600">
              <motion.div
                initial={{ scale: 0.8, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                transition={{ type: "spring", damping: 20 }}
                className="w-20 h-20 rounded-2xl bg-white/5 flex items-center justify-center mb-4"
              >
                <MessageSquare className="w-10 h-10 opacity-30" />
              </motion.div>
              <p className="text-lg font-medium text-gray-500">Select a conversation</p>
              <p className="text-sm text-gray-600 mt-1">Choose from the sidebar to view messages.</p>
            </div>
          )}
        </div>
      </motion.div>
    </motion.div>
  );
}
