import axiosInstance from "./axiosInstance";
export interface Signal { time: string; symbol: string; signal: string; }
export interface SignalsPaged { signals: Signal[]; total: number; page: number; page_size: number; }
export const getSignals = async (page = 1, pageSize = 20, symbol?: string) => {
  const res = await axiosInstance.get("/signals", {
    params: { page, page_size: pageSize, symbol }
  });
  return res.data as SignalsPaged;
};