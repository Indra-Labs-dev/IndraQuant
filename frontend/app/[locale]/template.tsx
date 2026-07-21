"use client";

import { motion } from "framer-motion";

/** Next.js remounts `template.tsx` on every navigation (unlike layout.tsx),
 * which is exactly what's needed for a per-page enter animation without
 * touching every route. */
export default function Template({ children }: { children: React.ReactNode }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25, ease: "easeOut" }}
    >
      {children}
    </motion.div>
  );
}
