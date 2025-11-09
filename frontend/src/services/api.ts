import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'https://lmguard-backend.onrender.com';

export interface Message {
  role: string;
  content: string;
}

export interface ChatRequest {
  messages: Message[];
  student_id?: string;
}

export interface ChatResponse {
  action: string;
  output: string;
  policy_reason: string;
  agent_confidence?: number;
}

export const sendChatMessage = async (
  messages: Message[],
  studentId?: string
): Promise<ChatResponse> => {
  const response = await axios.post<ChatResponse>(
    `${API_BASE_URL}/chat`,
    {
      messages,
      student_id: studentId
    }
  );
  
  return response.data;
};

export const checkHealth = async (): Promise<{ status: string }> => {
  const response = await axios.get(`${API_BASE_URL}/`);
  return response.data;
};