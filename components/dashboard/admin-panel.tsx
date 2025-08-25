"use client"

import { useState } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Progress } from "@/components/ui/progress"
import {
  Users,
  Activity,
  Database,
  Server,
  AlertTriangle,
  CheckCircle,
  XCircle,
  Settings,
  RefreshCw,
} from "lucide-react"

const systemStats = {
  totalUsers: 1247,
  activeUsers: 89,
  totalTrades: 15678,
  systemUptime: 99.8,
  apiCalls: 234567,
  errorRate: 0.02,
  avgResponseTime: 145,
}

const users = [
  {
    id: 1,
    username: "trader_pro",
    email: "trader@example.com",
    role: "trader",
    status: "active",
    lastLogin: "2024-01-15 14:30",
  },
  {
    id: 2,
    username: "admin_user",
    email: "admin@example.com",
    role: "admin",
    status: "active",
    lastLogin: "2024-01-15 13:45",
  },
  {
    id: 3,
    username: "viewer_01",
    email: "viewer@example.com",
    role: "viewer",
    status: "inactive",
    lastLogin: "2024-01-14 09:20",
  },
  {
    id: 4,
    username: "bot_trader",
    email: "bot@example.com",
    role: "trader",
    status: "active",
    lastLogin: "2024-01-15 14:25",
  },
]

const systemLogs = [
  {
    timestamp: "2024-01-15 14:30:25",
    level: "INFO",
    service: "Trading Engine",
    message: "Strategy 'Breakout Scalping' executed trade TXN001",
  },
  {
    timestamp: "2024-01-15 14:29:12",
    level: "WARN",
    service: "Market Data",
    message: "API rate limit approaching for Binance endpoint",
  },
  {
    timestamp: "2024-01-15 14:28:45",
    level: "ERROR",
    service: "Telegram Bot",
    message: "Failed to send notification to user @trader_pro",
  },
  {
    timestamp: "2024-01-15 14:27:33",
    level: "INFO",
    service: "Auth Service",
    message: "User 'admin_user' logged in successfully",
  },
  { timestamp: "2024-01-15 14:26:18", level: "INFO", service: "Database", message: "Backup completed successfully" },
]

const services = [
  { name: "Trading Engine", status: "healthy", uptime: 99.9, lastCheck: "2024-01-15 14:30:00" },
  { name: "Market Data Aggregator", status: "healthy", uptime: 99.7, lastCheck: "2024-01-15 14:29:45" },
  { name: "Telegram Bot", status: "warning", uptime: 98.5, lastCheck: "2024-01-15 14:29:30" },
  { name: "Authentication Service", status: "healthy", uptime: 99.8, lastCheck: "2024-01-15 14:30:15" },
  { name: "Database", status: "healthy", uptime: 99.9, lastCheck: "2024-01-15 14:30:10" },
  { name: "Risk Management", status: "healthy", uptime: 99.6, lastCheck: "2024-01-15 14:29:55" },
]

export function AdminPanel() {
  const [isRefreshing, setIsRefreshing] = useState(false)

  const refreshSystem = async () => {
    setIsRefreshing(true)
    await new Promise((resolve) => setTimeout(resolve, 2000))
    setIsRefreshing(false)
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "healthy":
        return <CheckCircle className="w-4 h-4 text-green-500" />
      case "warning":
        return <AlertTriangle className="w-4 h-4 text-yellow-500" />
      case "error":
        return <XCircle className="w-4 h-4 text-red-500" />
      default:
        return <Activity className="w-4 h-4 text-gray-500" />
    }
  }

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "healthy":
        return <Badge className="bg-green-500/10 text-green-500 border-green-500/20">Healthy</Badge>
      case "warning":
        return <Badge className="bg-yellow-500/10 text-yellow-500 border-yellow-500/20">Warning</Badge>
      case "error":
        return <Badge className="bg-red-500/10 text-red-500 border-red-500/20">Error</Badge>
      default:
        return <Badge variant="secondary">Unknown</Badge>
    }
  }

  const getLogLevelColor = (level: string) => {
    switch (level) {
      case "ERROR":
        return "text-red-500"
      case "WARN":
        return "text-yellow-500"
      case "INFO":
        return "text-blue-500"
      default:
        return "text-muted-foreground"
    }
  }

  return (
    <div className="space-y-6">
      {/* System Overview */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium flex items-center">
              <Users className="w-4 h-4 mr-2" />
              Total Users
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{systemStats.totalUsers.toLocaleString()}</div>
            <div className="text-xs text-muted-foreground">{systemStats.activeUsers} active now</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium flex items-center">
              <Activity className="w-4 h-4 mr-2" />
              System Uptime
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{systemStats.systemUptime}%</div>
            <Progress value={systemStats.systemUptime} className="mt-2" />
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium flex items-center">
              <Database className="w-4 h-4 mr-2" />
              Total Trades
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{systemStats.totalTrades.toLocaleString()}</div>
            <div className="text-xs text-muted-foreground">All time</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium flex items-center">
              <Server className="w-4 h-4 mr-2" />
              Error Rate
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-500">{systemStats.errorRate}%</div>
            <div className="text-xs text-muted-foreground">{systemStats.avgResponseTime}ms avg response</div>
          </CardContent>
        </Card>
      </div>

      {/* Admin Tabs */}
      <Tabs defaultValue="services" className="space-y-4">
        <div className="flex items-center justify-between">
          <TabsList>
            <TabsTrigger value="services">Services</TabsTrigger>
            <TabsTrigger value="users">Users</TabsTrigger>
            <TabsTrigger value="logs">System Logs</TabsTrigger>
            <TabsTrigger value="settings">Settings</TabsTrigger>
          </TabsList>
          <Button variant="outline" size="sm" onClick={refreshSystem} disabled={isRefreshing}>
            <RefreshCw className={`w-4 h-4 mr-2 ${isRefreshing ? "animate-spin" : ""}`} />
            Refresh
          </Button>
        </div>

        <TabsContent value="services" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Service Status</CardTitle>
              <CardDescription>Monitor all system services and their health</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {services.map((service, index) => (
                  <div key={index} className="flex items-center justify-between p-4 rounded-lg border">
                    <div className="flex items-center space-x-3">
                      {getStatusIcon(service.status)}
                      <div>
                        <h4 className="font-medium">{service.name}</h4>
                        <p className="text-sm text-muted-foreground">Last check: {service.lastCheck}</p>
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="font-medium">{service.uptime}% uptime</div>
                      {getStatusBadge(service.status)}
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="users" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>User Management</CardTitle>
              <CardDescription>Manage user accounts and permissions</CardDescription>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Username</TableHead>
                    <TableHead>Email</TableHead>
                    <TableHead>Role</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Last Login</TableHead>
                    <TableHead>Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {users.map((user) => (
                    <TableRow key={user.id}>
                      <TableCell className="font-medium">{user.username}</TableCell>
                      <TableCell>{user.email}</TableCell>
                      <TableCell>
                        <Badge variant={user.role === "admin" ? "default" : "secondary"}>{user.role}</Badge>
                      </TableCell>
                      <TableCell>
                        <Badge variant={user.status === "active" ? "default" : "outline"}>{user.status}</Badge>
                      </TableCell>
                      <TableCell className="text-sm text-muted-foreground">{user.lastLogin}</TableCell>
                      <TableCell>
                        <Button variant="outline" size="sm">
                          Edit
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="logs" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>System Logs</CardTitle>
              <CardDescription>Recent system activity and error logs</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {systemLogs.map((log, index) => (
                  <div key={index} className="flex items-start space-x-3 p-3 rounded-lg border font-mono text-sm">
                    <Badge
                      variant={log.level === "ERROR" ? "destructive" : log.level === "WARN" ? "secondary" : "outline"}
                    >
                      {log.level}
                    </Badge>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center space-x-2 mb-1">
                        <span className="text-muted-foreground">{log.timestamp}</span>
                        <span className="font-medium">[{log.service}]</span>
                      </div>
                      <p className="text-sm">{log.message}</p>
                    </div>
                  </div>
                ))}
              </div>
              <Button variant="outline" className="w-full mt-4 bg-transparent">
                Load More Logs
              </Button>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="settings" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>System Settings</CardTitle>
              <CardDescription>Configure system-wide parameters</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-6">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div className="space-y-4">
                    <h4 className="font-medium">Trading Settings</h4>
                    <div className="space-y-3">
                      <div className="flex justify-between items-center">
                        <span className="text-sm">Global Trading Enabled</span>
                        <Badge className="bg-green-500/10 text-green-500 border-green-500/20">Enabled</Badge>
                      </div>
                      <div className="flex justify-between items-center">
                        <span className="text-sm">Max Concurrent Trades</span>
                        <span className="text-sm font-medium">50</span>
                      </div>
                      <div className="flex justify-between items-center">
                        <span className="text-sm">Emergency Stop</span>
                        <Button variant="destructive" size="sm">
                          Stop All Trading
                        </Button>
                      </div>
                    </div>
                  </div>

                  <div className="space-y-4">
                    <h4 className="font-medium">System Maintenance</h4>
                    <div className="space-y-3">
                      <Button variant="outline" className="w-full bg-transparent">
                        <Database className="w-4 h-4 mr-2" />
                        Backup Database
                      </Button>
                      <Button variant="outline" className="w-full bg-transparent">
                        <RefreshCw className="w-4 h-4 mr-2" />
                        Restart Services
                      </Button>
                      <Button variant="outline" className="w-full bg-transparent">
                        <Settings className="w-4 h-4 mr-2" />
                        System Diagnostics
                      </Button>
                    </div>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}
