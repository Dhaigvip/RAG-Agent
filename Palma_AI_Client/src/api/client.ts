// src/api/client.ts

import { mockChatResponse } from "./mockResponse";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";
const USE_MOCK = import.meta.env.VITE_USE_CHAT_MOCK === "true";

if (!API_BASE_URL) {
    throw new Error("VITE_API_BASE_URL is not defined");
}
type Source = {
    source: string;
    chunk_id: string;
};

export type ChatResponse = {
    session_id: string;
    answer: string;
    sources?: Source[];
};

export async function sendChatMessage(query: string, sessionId: string | null): Promise<ChatResponse> {
    if (USE_MOCK) {
        // simulate network latency
        await new Promise((res) => setTimeout(res, 600));

        return {
            ...mockChatResponse,
            session_id: sessionId ?? mockChatResponse.session_id
        };
    }

    const res = await fetch(`${API_BASE_URL}/chat`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            query,
            session_id: sessionId,
            namespace: "https://www.modularmanagement.com/"
        })
    });

    if (!res.ok) {
        const text = await res.text();
        throw new Error(`Chat API error: ${text}`);
    }

    return res.json();
}
