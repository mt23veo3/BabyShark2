import axiosInstance from "./axiosInstance";
export interface Alert { level: string; msg: string; time: string; }
export interface AlertsPaged { alerts: Alert[]; total: number; page: number; page_size: number; }
export const getAlerts = async (page = 1, pageSize = 20) => {
  const res = await axiosInstance.get("/alerts", { params: { page, page_size: pageSize } });
  return res.data as AlertsPaged;
};