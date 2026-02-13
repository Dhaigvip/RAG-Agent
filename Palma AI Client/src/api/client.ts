// src/api/client.ts

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;

if (!API_BASE_URL) {
    throw new Error("VITE_API_BASE_URL is not defined");
}

export type ChatResponse = {
    session_id: string;
    answer: string;
};

export async function sendChatMessage(query: string, sessionId: string | null): Promise<ChatResponse> {
    const res = await fetch(`${API_BASE_URL}/chat`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            query,
            session_id: sessionId,
            "namespace": "https://www.modularmanagement.com/"
        })
    });

    if (!res.ok) {
        const text = await res.text();
        throw new Error(`Chat API error: ${text}`);
    }

    return res.json();
}
