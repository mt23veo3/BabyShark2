import { useEffect } from "react";
import { io, Socket } from "socket.io-client";

export function useSocket(event: string, handler: (data: any) => void) {
  useEffect(() => {
    const socket: Socket = io("http://localhost:8000"); // Đổi cho đúng backend
    socket.on(event, handler);
    return () => { socket.off(event, handler); socket.disconnect(); };
  }, [event, handler]);
}