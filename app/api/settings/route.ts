import { NextResponse } from "next/server"
import {
  getSettings,
  updateSettings,
  resetToDefaults,
  SETTING_RECOMMENDATIONS,
  assessRisk,
  validateSettings,
} from "@/lib/trading/settings-manager"

export async function GET() {
  try {
    const settings = await getSettings()
    const riskAssessment = assessRisk(settings)

    return NextResponse.json({
      success: true,
      settings,
      recommendations: SETTING_RECOMMENDATIONS,
      riskAssessment,
    })
  } catch (error) {
    console.error("Failed to get settings:", error)
    return NextResponse.json({ success: false, error: "Failed to load settings" }, { status: 500 })
  }
}

export async function PUT(request: Request) {
  try {
    const body = await request.json()
    const { updates } = body

    if (!updates || typeof updates !== "object") {
      return NextResponse.json({ success: false, error: "Invalid updates object" }, { status: 400 })
    }

    // Validate before updating
    const validationErrors = validateSettings(updates)
    if (validationErrors.length > 0) {
      return NextResponse.json({ success: false, errors: validationErrors }, { status: 400 })
    }

    const newSettings = await updateSettings(updates)
    const riskAssessment = assessRisk(newSettings)

    return NextResponse.json({
      success: true,
      settings: newSettings,
      riskAssessment,
      message: "Settings updated successfully",
    })
  } catch (error) {
    console.error("Failed to update settings:", error)
    return NextResponse.json(
      { success: false, error: error instanceof Error ? error.message : "Failed to update settings" },
      { status: 500 },
    )
  }
}

export async function DELETE() {
  try {
    const defaults = await resetToDefaults()
    const riskAssessment = assessRisk(defaults)

    return NextResponse.json({
      success: true,
      settings: defaults,
      riskAssessment,
      message: "Settings reset to recommended defaults",
    })
  } catch (error) {
    console.error("Failed to reset settings:", error)
    return NextResponse.json({ success: false, error: "Failed to reset settings" }, { status: 500 })
  }
}
