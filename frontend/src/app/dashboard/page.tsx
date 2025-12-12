"use client";

import { useState } from "react";

export default function Dashboard() {
    const [agentStatus, setAgentStatus] = useState<"stopped" | "running" | "loading">("stopped");
    const [riskProfile, setRiskProfile] = useState("medium");
    const [selectedAssets, setSelectedAssets] = useState<string[]>(["BTC"]);
    const [portfolioValue] = useState(1000);

    // Mock wallet address for demo
    const walletAddress = "0x1234...demo";

    // Toggle asset selection
    function toggleAsset(asset: string) {
        if (selectedAssets.includes(asset)) {
            if (selectedAssets.length > 1) {
                setSelectedAssets(selectedAssets.filter(a => a !== asset));
            }
        } else {
            setSelectedAssets([...selectedAssets, asset]);
        }
    }

    // Handle agent start (mock)
    function handleStartAgent() {
        setAgentStatus("loading");
        setTimeout(() => setAgentStatus("running"), 1500);
    }

    // Handle agent stop (mock)
    function handleStopAgent() {
        setAgentStatus("loading");
        setTimeout(() => setAgentStatus("stopped"), 1000);
    }

    return (
        <div className="min-h-screen bg-gray-950">
            {/* Header */}
            <header className="border-b border-gray-800 bg-gray-900/50 backdrop-blur-sm sticky top-0 z-50">
                <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
                    <a href="/" className="text-2xl font-bold bg-gradient-to-r from-indigo-400 to-purple-400 bg-clip-text text-transparent">
                        HypeAI
                    </a>
                    <div className="flex items-center gap-4">
                        <div className="text-sm">
                            <span className="text-gray-400">Wallet: </span>
                            <span className="text-white font-mono">{walletAddress}</span>
                        </div>
                        <span className="bg-yellow-500/20 text-yellow-400 text-xs px-2 py-1 rounded-full">
                            Demo Mode
                        </span>
                        <a
                            href="/"
                            className="text-gray-400 hover:text-white text-sm transition-colors"
                        >
                            Back
                        </a>
                    </div>
                </div>
            </header>

            <main className="max-w-7xl mx-auto px-4 py-8">
                {/* Demo Notice */}
                <div className="bg-indigo-900/30 border border-indigo-700 rounded-xl p-4 mb-6">
                    <p className="text-indigo-300">
                        🎮 <strong>Demo Mode:</strong> This is a preview of the trading dashboard.
                        Configure Privy to enable real wallet login and trading.
                    </p>
                </div>

                {/* Funding Status */}
                <div className="bg-green-900/30 border border-green-700 rounded-xl p-4 mb-6">
                    <p className="text-green-300">✓ Demo wallet funded with $1,000 testnet USDC</p>
                </div>

                {/* Stats Grid */}
                <div className="grid md:grid-cols-4 gap-4 mb-8">
                    <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
                        <p className="text-gray-400 text-sm mb-1">Portfolio Value</p>
                        <p className="text-3xl font-bold text-white">${portfolioValue.toLocaleString()}</p>
                    </div>
                    <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
                        <p className="text-gray-400 text-sm mb-1">Today&apos;s P&amp;L</p>
                        <p className="text-3xl font-bold text-green-400">+$0.00</p>
                    </div>
                    <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
                        <p className="text-gray-400 text-sm mb-1">Open Positions</p>
                        <p className="text-3xl font-bold text-white">0</p>
                    </div>
                    <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
                        <p className="text-gray-400 text-sm mb-1">Agent Status</p>
                        <p className={`text-3xl font-bold ${agentStatus === "running" ? "text-green-400" : "text-gray-400"}`}>
                            {agentStatus === "running" ? "🟢 Active" : agentStatus === "loading" ? "⏳ ..." : "⚪ Inactive"}
                        </p>
                    </div>
                </div>

                {/* Agent Control */}
                <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 mb-8">
                    <h2 className="text-xl font-semibold mb-4 text-white">AI Trading Agent</h2>

                    <div className="grid md:grid-cols-2 gap-6">
                        {/* Configuration */}
                        <div className="space-y-4">
                            <div>
                                <label className="text-sm text-gray-400 block mb-2">Risk Profile</label>
                                <select
                                    className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-white"
                                    value={riskProfile}
                                    onChange={(e) => setRiskProfile(e.target.value)}
                                    disabled={agentStatus === "running"}
                                >
                                    <option value="low">Low Risk (Conservative)</option>
                                    <option value="medium">Medium Risk (Balanced)</option>
                                    <option value="high">High Risk (Aggressive)</option>
                                </select>
                            </div>
                            <div>
                                <label className="text-sm text-gray-400 block mb-2">Trading Assets</label>
                                <div className="flex gap-2 flex-wrap">
                                    {["BTC", "ETH", "SOL", "AVAX", "ARB"].map(asset => (
                                        <button
                                            key={asset}
                                            onClick={() => toggleAsset(asset)}
                                            disabled={agentStatus === "running"}
                                            className={`px-3 py-1 rounded-full text-sm transition-colors ${selectedAssets.includes(asset)
                                                    ? "bg-indigo-600 text-white"
                                                    : "bg-gray-700 text-white hover:bg-gray-600"
                                                } ${agentStatus === "running" ? "opacity-50 cursor-not-allowed" : ""}`}
                                        >
                                            {asset}
                                        </button>
                                    ))}
                                </div>
                            </div>
                        </div>

                        {/* Controls */}
                        <div className="flex flex-col justify-center items-center gap-4">
                            {agentStatus === "stopped" ? (
                                <button
                                    onClick={handleStartAgent}
                                    className="w-full bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-500 hover:to-emerald-500 text-white font-semibold py-4 px-8 rounded-xl text-lg transition-all"
                                >
                                    🚀 Start AI Agent
                                </button>
                            ) : agentStatus === "loading" ? (
                                <button
                                    disabled
                                    className="w-full bg-gray-700 text-white font-semibold py-4 px-8 rounded-xl text-lg opacity-50"
                                >
                                    ⏳ Loading...
                                </button>
                            ) : (
                                <button
                                    onClick={handleStopAgent}
                                    className="w-full bg-gradient-to-r from-red-600 to-rose-600 hover:from-red-500 hover:to-rose-500 text-white font-semibold py-4 px-8 rounded-xl text-lg transition-all"
                                >
                                    ⏹️ Stop Agent
                                </button>
                            )}
                            <p className="text-gray-500 text-sm text-center">
                                {agentStatus === "running"
                                    ? "Agent is actively trading based on your risk profile"
                                    : "Click to start AI-powered trading on Hyperliquid testnet"}
                            </p>
                        </div>
                    </div>
                </div>

                {/* Recent Activity */}
                <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
                    <h2 className="text-xl font-semibold mb-4 text-white">Recent Trades</h2>
                    <div className="text-center py-12 text-gray-500">
                        <p className="text-4xl mb-2">📊</p>
                        <p>No trades yet. Start the AI agent to begin trading.</p>
                    </div>
                </div>
            </main>
        </div>
    );
}
