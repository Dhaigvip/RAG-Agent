import { useState } from "react";

import "./chat.css";
import { sendChatMessage } from "../api/client";

type Message = {
    role: "user" | "assistant";
    content: string;
};

export default function Chat() {
    const [messages, setMessages] = useState<Message[]>([]);
    const [input, setInput] = useState("");
    const [loading, setLoading] = useState(false);

    const [sessionId, setSessionId] = useState<string | null>(() => {
        return localStorage.getItem("session_id");
    });

    async function sendMessage() {
        if (!input.trim() || loading) return;

        const userMessage: Message = { role: "user", content: input };
        setMessages((prev) => [...prev, userMessage]);
        setInput("");
        setLoading(true);

        try {
            const data = await sendChatMessage(userMessage.content, sessionId);

            setSessionId(data.session_id);
            localStorage.setItem("session_id", data.session_id);

            setMessages((prev) => [...prev, { role: "assistant", content: data.answer }]);
        } catch (err) {
            setMessages((prev) => [
                ...prev,
                {
                    role: "assistant",
                    content: "Something went wrong. Please try again."
                }
            ]);
        } finally {
            setLoading(false);
        }
    }

    return (
        <div className="chat-container">
            <h2 className="chat-title">RAG Chat</h2>

            <div className="chat-window">
                {messages.map((m, i) => (
                    <div key={i} className={`chat-message ${m.role}`}>
                        <div className={`chat-bubble ${m.role}`}>{m.content}</div>
                    </div>
                ))}

                {loading && <div className="chat-loading">Thinking…</div>}
            </div>

            <div className="chat-input-container">
                <input
                    className="chat-input"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && sendMessage()}
                    placeholder="Ask something…"
                />
                <button className="chat-button" onClick={sendMessage} disabled={loading}>
                    Send
                </button>
            </div>
        </div>
    );
}
