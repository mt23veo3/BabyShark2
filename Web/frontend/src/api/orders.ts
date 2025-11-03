import axiosInstance from "./axiosInstance";

export interface Order {
  id: number;
  symbol: string;
  side: string;
  pnl: number;
  status: string;
}

export interface OrdersPaged {
  orders: Order[];
  total: number;
  page: number;
  page_size: number;
}

export const getOrders = async (page = 1, pageSize = 20, symbol?: string) => {
  const res = await axiosInstance.get("/orders", {
    params: { page, page_size: pageSize, symbol }
  });
  return res.data as OrdersPaged;
};