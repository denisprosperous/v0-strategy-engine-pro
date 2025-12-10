import { NextResponse } from "next/server"
import { getEnvVarsByCategory } from "@/lib/config/env-display"

export async function GET() {
  const envVars = getEnvVarsByCategory()

  return NextResponse.json({
    success: true,
    timestamp: new Date().toISOString(),
    region: process.env.VERCEL_REGION || "iad1",
    environment: process.env.NODE_ENV || "development",
    variables: envVars,
    summary: {
      system: {
        total: envVars.system.length,
        configured: envVars.system.filter((v) => !v.value.includes("Not set")).length,
      },
      trading: {
        total: envVars.trading.length,
        configured: envVars.trading.filter((v) => !v.value.includes("Not set")).length,
      },
      ai: {
        total: envVars.ai.length,
        configured: envVars.ai.filter((v) => !v.value.includes("Not set")).length,
      },
      exchange: {
        total: envVars.exchange.length,
        configured: envVars.exchange.filter((v) => !v.value.includes("Not set")).length,
      },
      telegram: {
        total: envVars.telegram.length,
        configured: envVars.telegram.filter((v) => !v.value.includes("Not set")).length,
      },
      database: {
        total: envVars.database.length,
        configured: envVars.database.filter((v) => !v.value.includes("Not set")).length,
      },
    },
  })
}
