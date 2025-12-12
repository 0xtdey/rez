# HypeAI Frontend - Privy + Next.js

## Quick Start

### 1. Install Dependencies
```bash
cd frontend
npm install
```

### 2. Configure Environment
```bash
cp .env.example .env.local
```

Edit `.env.local`:
```
NEXT_PUBLIC_PRIVY_APP_ID=your_privy_app_id
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### 3. Get Privy App ID
1. Go to [dashboard.privy.io](https://dashboard.privy.io)
2. Create a new app
3. Copy the App ID to your `.env.local`

### 4. Run Development Server
```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000)

## Features

- 🔐 Social login (Google, Email, Twitter) via Privy
- 💼 Embedded wallets (no seed phrase needed)
- 📊 Trading dashboard with agent controls
- 🎨 Dark theme with modern UI

## Pages

| Path | Description |
|------|-------------|
| `/` | Landing page with login |
| `/dashboard` | Trading dashboard (auth required) |

## Tech Stack

- Next.js 14
- Privy React Auth
- Tailwind CSS
- TypeScript
