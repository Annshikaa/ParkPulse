import client from "./client";
import type { Slot, Stats } from "@/types";

export const slotsApi = {
  list: () => client.get<Slot[]>("/slots"),
  get: (id: number) => client.get<Slot>(`/slots/${id}`),
  stats: () => client.get<Stats>("/stats"),
};
