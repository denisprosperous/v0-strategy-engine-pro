import type { NextRequest } from "next/server"
import { AccountManager } from "@/lib/trading/account/account-manager"

export async function GET(request: NextRequest) {
  try {
    // Get user ID from session/auth (simulated)
    const userId = "user_123" // In real app, get from authentication

    const accountManager = new AccountManager(userId)
    await accountManager.initializeAccounts()

    const accounts = accountManager.getUserAccounts()
    const accountsWithBalances = accounts.map((account) => ({
      ...account,
      balance: accountManager.getAccountBalance(account.id),
    }))

    return Response.json({
      success: true,
      accounts: accountsWithBalances,
    })
  } catch (error) {
    console.error("[v0] Error fetching accounts:", error)
    return Response.json(
      {
        error: "Failed to fetch accounts",
        details: error instanceof Error ? error.message : "Unknown error",
      },
      { status: 500 },
    )
  }
}

export async function POST(request: NextRequest) {
  try {
    const userId = "user_123" // In real app, get from authentication
    const { action, ...data } = await request.json()

    const accountManager = new AccountManager(userId)
    await accountManager.initializeAccounts()

    switch (action) {
      case "create_live_account":
        const { accountName, broker, apiCredentials } = data
        const newAccount = await accountManager.createLiveAccount(accountName, broker, apiCredentials)
        return Response.json({
          success: true,
          account: newAccount,
          message: "Live account created successfully",
        })

      case "reset_demo_account":
        const { accountId } = data
        await accountManager.resetDemoAccount(accountId)
        return Response.json({
          success: true,
          message: "Demo account reset successfully",
        })

      case "sync_live_balance":
        const { accountId: syncAccountId } = data
        await accountManager.syncLiveAccountBalance(syncAccountId)
        return Response.json({
          success: true,
          message: "Live account balance synced successfully",
        })

      default:
        return Response.json(
          {
            error: "Invalid action",
          },
          { status: 400 },
        )
    }
  } catch (error) {
    console.error("[v0] Error in accounts API:", error)
    return Response.json(
      {
        error: "Account operation failed",
        details: error instanceof Error ? error.message : "Unknown error",
      },
      { status: 500 },
    )
  }
}
