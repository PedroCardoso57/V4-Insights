import type { Metadata } from "next";

import { EmConstrucao } from "@/components/mascote/em-construcao";

export const metadata: Metadata = { title: "Em construção" };

export default function EmConstrucaoPage() {
  return <EmConstrucao />;
}
