import axios from "axios";
import { API_BASE_URL, API_KEY } from "./config";

const axiosInstance = axios.create({
  baseURL: API_BASE_URL,
  headers: { "x-api-key": API_KEY },
});

axiosInstance.interceptors.request.use(config => {
  const token = localStorage.getItem("token");
  if (token) config.headers["Authorization"] = `Bearer ${token}`;
  return config;
});

export default axiosInstance;