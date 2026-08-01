import axios from 'axios';

// Ensure you replace this with the actual backend IP address if running on a physical device.
// For Android emulator, use 10.0.2.2. For physical devices, use your Mac's IP (e.g. 192.168.1.35)
export const BASE_URL = 'http://192.168.1.35:8000';

export const api = axios.create({
  baseURL: BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const authState = {
  accessToken: null,
};

export const verifyNumber = async (phoneNumber) => {
  // In a real scenario, the OIDC flow would be triggered via a WebView or browser redirect
  // For the sake of the demo, we assume the token exchange is handled and we call the backend NV endpoint.
  // We'll mock the access_token for now until OIDC is fully wired.
  const response = await api.post('/nv/verify', {
    access_token: authState.accessToken || 'mock-token',
    phone_number: phoneNumber,
  });
  return response.data;
};

export const createQoDSession = async (duration = 60) => {
  const response = await api.post('/qod/session', {
    access_token: authState.accessToken || 'mock-token',
    duration: duration,
  });
  return response.data;
};

export const uploadVideo = async (fileUri) => {
  const formData = new FormData();
  formData.append('file', {
    uri: fileUri,
    name: 'video.mp4',
    type: 'video/mp4',
  });

  const response = await api.post('/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  return response.data;
};

export const runAI = async () => {
  const response = await api.post('/ai-run');
  return response.data;
};

export const getAIResult = async () => {
  const response = await api.get('/ai-result');
  return response.data;
};
