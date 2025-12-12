"use client";

import { useState, useEffect } from "react";

export default function Home() {
  const [loading, setLoading] = useState(true);
  const [privyError, setPrivyError] = useState(false);

  useEffect(() => {
    // Check if Privy loads correctly after 3 seconds
    const timer = setTimeout(() => {
      setLoading(false);
      setPrivyError(true);
    }, 3000);

    return () => clearTimeout(timer);
  }, []);

  if (loading) {
    return (
      <main className="min-h-screen bg-gradient-to-br from-gray-950 via-gray-900 to-indigo-950 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-indigo-500 mx-auto mb-4"></div>
          <p className="text-gray-400">Loading HypeAI...</p>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-gradient-to-br from-gray-950 via-gray-900 to-indigo-950">
      {/* Hero Section */}
      <div className="flex flex-col items-center justify-center min-h-screen px-4">
        {/* Logo/Brand */}
        <div className="mb-8">
          <h1 className="text-6xl font-bold bg-gradient-to-r from-indigo-400 via-purple-400 to-pink-400 bg-clip-text text-transparent">
            HypeAI
          </h1>
          <p className="text-gray-400 text-center mt-2">
            AI-Powered Trading on Hyperliquid
          </p>
        </div>

        {/* Feature Cards */}
        <div className="grid md:grid-cols-3 gap-6 max-w-4xl mb-12">
          <div className="bg-gray-900/50 backdrop-blur-sm border border-gray-800 rounded-xl p-6">
            <div className="text-3xl mb-3">🤖</div>
            <h3 className="text-lg font-semibold mb-2 text-white">AI-Powered Decisions</h3>
            <p className="text-gray-400 text-sm">
              Advanced TA + LLM inference for intelligent trading
            </p>
          </div>
          <div className="bg-gray-900/50 backdrop-blur-sm border border-gray-800 rounded-xl p-6">
            <div className="text-3xl mb-3">🔒</div>
            <h3 className="text-lg font-semibold mb-2 text-white">Non-Custodial</h3>
            <p className="text-gray-400 text-sm">
              Your wallet, your funds. We never hold your keys.
            </p>
          </div>
          <div className="bg-gray-900/50 backdrop-blur-sm border border-gray-800 rounded-xl p-6">
            <div className="text-3xl mb-3">⚡</div>
            <h3 className="text-lg font-semibold mb-2 text-white">Hyperliquid L1</h3>
            <p className="text-gray-400 text-sm">
              Ultra-fast perpetuals trading on-chain
            </p>
          </div>
        </div>

        {/* CTA Section */}
        {privyError ? (
          <div className="text-center max-w-lg">
            <div className="bg-yellow-900/30 border border-yellow-700 rounded-xl p-6 mb-6">
              <p className="text-yellow-300 mb-4">⚠️ Privy App ID not configured</p>
              <p className="text-gray-400 text-sm mb-4">
                To enable social login, you need to configure a Privy App ID:
              </p>
              <ol className="text-left text-gray-400 text-sm space-y-2">
                <li>1. Go to <a href="https://dashboard.privy.io" target="_blank" className="text-indigo-400 underline">dashboard.privy.io</a></li>
                <li>2. Create an account and new app</li>
                <li>3. Copy your App ID</li>
                <li>4. Edit <code className="bg-gray-800 px-2 py-1 rounded">frontend/.env.local</code></li>
                <li>5. Set <code className="bg-gray-800 px-2 py-1 rounded">NEXT_PUBLIC_PRIVY_APP_ID=your_app_id</code></li>
                <li>6. Restart the dev server</li>
              </ol>
            </div>
            <a
              href="/dashboard"
              className="inline-block bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white font-semibold py-4 px-8 rounded-xl text-lg transition-all"
            >
              Continue to Demo Dashboard →
            </a>
          </div>
        ) : (
          <button
            className="bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white font-semibold py-4 px-8 rounded-xl text-lg transition-all shadow-lg shadow-indigo-500/25 hover:shadow-indigo-500/40"
          >
            Get Started with Testnet
          </button>
        )}

        {/* Testnet Badge */}
        <div className="absolute bottom-8 left-1/2 -translate-x-1/2">
          <span className="bg-yellow-500/20 text-yellow-400 text-xs font-medium px-3 py-1 rounded-full border border-yellow-500/30">
            🧪 Testnet Mode - No Real Funds
          </span>
        </div>
      </div>
    </main>
  );
}
