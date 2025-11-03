import axiosInstance from "./axiosInstance";
export interface Settings { max_hold_m15: number; trailing_stop: number; snapshot_confirmations: number; }
export const getSettings = async (): Promise<Settings> => {
  const res = await axiosInstance.get("/settings");
  return res.data;
};
export const updateSettings = async (settings: Settings) => {
  const res = await axiosInstance.post("/settings", settings);
  return res.data;
};