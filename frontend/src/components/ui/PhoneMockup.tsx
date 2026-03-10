import clsx from "clsx";

interface PhoneMockupProps {
  messages: { text: string; from: "sender" | "recipient"; time?: string }[];
  className?: string;
}

export default function PhoneMockup({ messages, className }: PhoneMockupProps) {
  return (
    <div className={clsx("w-[300px] mx-auto", className)}>
      <div className="bg-gray-900 rounded-[3rem] p-3 shadow-2xl border border-gray-700">
        {/* Notch */}
        <div className="flex justify-center mb-2">
          <div className="w-28 h-6 bg-black rounded-full" />
        </div>
        {/* Screen */}
        <div className="bg-gray-950 rounded-[2rem] h-[500px] overflow-hidden flex flex-col">
          {/* Header */}
          <div className="bg-navy-900/50 backdrop-blur px-4 py-3 border-b border-white/5">
            <p className="text-center text-sm font-medium text-white">Messages</p>
          </div>
          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-4 space-y-2">
            {messages.map((msg, i) => (
              <div key={i} className={clsx("flex", msg.from === "sender" ? "justify-end" : "justify-start")}>
                <div
                  className={clsx(
                    "max-w-[75%] px-3 py-2 rounded-2xl text-sm",
                    msg.from === "sender"
                      ? "bg-blue-500 text-white rounded-br-md"
                      : "bg-gray-700 text-gray-100 rounded-bl-md"
                  )}
                >
                  {msg.text}
                  {msg.time && <p className="text-[10px] opacity-60 mt-1">{msg.time}</p>}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
