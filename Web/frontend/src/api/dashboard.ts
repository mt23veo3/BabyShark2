import axiosInstance from "./axiosInstance";
export const getDashboardOverview = async () => {
  const res = await axiosInstance.get("/dashboard");
  return res.data;
};