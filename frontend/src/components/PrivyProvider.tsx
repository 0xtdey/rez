"use client";

import dynamic from "next/dynamic";

// Import Privy dynamically to avoid SSR issues with WalletConnect/pino
const PrivyProviderWrapper = dynamic(
    () => import("./PrivyProviderClient"),
    { ssr: false }
);

export default function PrivyWrapper({
    children,
}: {
    children: React.ReactNode;
}) {
    return <PrivyProviderWrapper>{children}</PrivyProviderWrapper>;
}
