import axiosInstance from "./axiosInstance";
export interface PnLData { labels: string[]; values: number[]; }
export const getPnLReport = async (): Promise<PnLData> => {
  const res = await axiosInstance.get("/pnl");
  return res.data;
};