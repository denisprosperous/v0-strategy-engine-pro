"use client"

import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { useAuth } from "@/lib/hooks/use-auth"
import { LayoutDashboard, TrendingUp, BarChart3, Shield, Users, LogOut, Bot } from "lucide-react"

interface DashboardSidebarProps {
  activeTab: string
  onTabChange: (tab: string) => void
}

export function DashboardSidebar({ activeTab, onTabChange }: DashboardSidebarProps) {
  const { user, logout } = useAuth()

  const menuItems = [
    { id: "overview", label: "Overview", icon: LayoutDashboard },
    { id: "trades", label: "Trade History", icon: TrendingUp },
    { id: "strategies", label: "Strategies", icon: Bot },
    { id: "market", label: "Market Data", icon: BarChart3 },
    { id: "risk", label: "Risk Management", icon: Shield },
  ]

  if (user?.role === "admin") {
    menuItems.push({ id: "admin", label: "Admin Panel", icon: Users })
  }

  return (
    <div className="w-64 bg-sidebar border-r border-sidebar-border flex flex-col">
      {/* Header */}
      <div className="p-6 border-b border-sidebar-border">
        <div className="flex items-center space-x-2">
          <div className="w-8 h-8 bg-sidebar-primary rounded-lg flex items-center justify-center">
            <Bot className="w-4 h-4 text-sidebar-primary-foreground" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-sidebar-foreground">AI Trader</h2>
            <p className="text-xs text-sidebar-foreground/60">v2.0.1</p>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-4 space-y-2">
        {menuItems.map((item) => {
          const Icon = item.icon
          return (
            <Button
              key={item.id}
              variant={activeTab === item.id ? "secondary" : "ghost"}
              className={cn(
                "w-full justify-start text-sidebar-foreground hover:bg-sidebar-accent",
                activeTab === item.id && "bg-sidebar-accent text-sidebar-accent-foreground",
              )}
              onClick={() => onTabChange(item.id)}
            >
              <Icon className="w-4 h-4 mr-3" />
              {item.label}
            </Button>
          )
        })}
      </nav>

      {/* User Info & Logout */}
      <div className="p-4 border-t border-sidebar-border">
        <div className="flex items-center space-x-3 mb-3">
          <div className="w-8 h-8 bg-sidebar-primary rounded-full flex items-center justify-center">
            <span className="text-xs font-medium text-sidebar-primary-foreground">
              {user?.username?.charAt(0).toUpperCase()}
            </span>
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-sidebar-foreground truncate">{user?.username}</p>
            <p className="text-xs text-sidebar-foreground/60 capitalize">{user?.role}</p>
          </div>
        </div>
        <Button
          variant="ghost"
          size="sm"
          className="w-full justify-start text-sidebar-foreground hover:bg-sidebar-accent"
          onClick={logout}
        >
          <LogOut className="w-4 h-4 mr-3" />
          Logout
        </Button>
      </div>
    </div>
  )
}
