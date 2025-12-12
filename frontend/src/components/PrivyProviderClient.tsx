"use client";

import { PrivyProvider } from "@privy-io/react-auth";
import { arbitrumSepolia } from "viem/chains";

export default function PrivyProviderClient({
    children,
}: {
    children: React.ReactNode;
}) {
    return (
        <PrivyProvider
            appId={process.env.NEXT_PUBLIC_PRIVY_APP_ID || "clpisiupl0c35l00f8wce5tyu"}
            config={{
                // Appearance
                appearance: {
                    theme: "dark",
                    accentColor: "#676FFF",
                    logo: "/logo.svg",
                    showWalletLoginFirst: false,
                },
                // Login methods
                loginMethods: ["email", "google", "twitter"],
                // Embedded wallet config (updated API)
                embeddedWallets: {
                    ethereum: {
                        createOnLogin: "users-without-wallets",
                    },
                },
                // Chain config for Hyperliquid (Arbitrum-based testnet)
                defaultChain: arbitrumSepolia,
                supportedChains: [arbitrumSepolia],
            }}
        >
            {children}
        </PrivyProvider>
    );
}
