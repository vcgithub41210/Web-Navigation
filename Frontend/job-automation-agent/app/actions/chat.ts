export interface ChatRequest {
  message: string;
  user_id: string;
}

export interface ChatResponse {
  reply: string;
  status?: string;
  error?: string;
}

const BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

export async function sendChatMessage(
  message: string,
  userId: string
): Promise<string> {
  try {
    const response = await fetch(`${BACKEND_URL}/api/chat`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        message,
        user_id: userId,
      } as ChatRequest),
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(
        `Backend error (${response.status}): ${errorText}`
      );
    }

    const data: ChatResponse = await response.json();

    if (data.error) {
      throw new Error(data.error);
    }

    return data.reply;
  } catch (error) {
    console.error("[Frontend] Auto-apply chat request failed:", error);
    throw error;
  }
}

export async function sendCustomFormMessage(
  message: string,
  userId: string
): Promise<string> {
  try {
    const response = await fetch(`${BACKEND_URL}/api/customform`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        message,
        user_id: userId,
      } as ChatRequest),
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(
        `Backend error (${response.status}): ${errorText}`
      );
    }

    const data: ChatResponse = await response.json();

    if (data.error) {
      throw new Error(data.error);
    }

    return data.reply;
  } catch (error) {
    console.error("[Frontend] Custom form request failed:", error);
    throw error;
  }
}