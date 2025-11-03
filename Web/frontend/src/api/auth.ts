import axiosInstance from "./axiosInstance";
export const login = async (username: string, password: string) => {
  const res = await axiosInstance.post("/user/login", { username, password });
  return res.data;
};