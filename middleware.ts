// Next.js middleware for route protection
import { type NextRequest, NextResponse } from "next/server"
import { verifyToken, extractTokenFromHeader } from "@/lib/auth/jwt"

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl

  // Protected routes that require authentication
  const protectedRoutes = ["/dashboard", "/admin", "/trading", "/profile"]
  const adminRoutes = ["/admin"]

  // Check if the current path is protected
  const isProtectedRoute = protectedRoutes.some((route) => pathname.startsWith(route))
  const isAdminRoute = adminRoutes.some((route) => pathname.startsWith(route))

  if (isProtectedRoute) {
    // Get token from cookie or authorization header
    const token =
      request.cookies.get("auth-token")?.value || extractTokenFromHeader(request.headers.get("authorization"))

    if (!token) {
      // Redirect to login if no token
      const loginUrl = new URL("/auth/login", request.url)
      loginUrl.searchParams.set("redirect", pathname)
      return NextResponse.redirect(loginUrl)
    }

    try {
      const user = verifyToken(token)
      if (!user) {
        // Redirect to login if invalid token
        const loginUrl = new URL("/auth/login", request.url)
        loginUrl.searchParams.set("redirect", pathname)
        return NextResponse.redirect(loginUrl)
      }

      // Check admin access
      if (isAdminRoute && user.role !== "admin") {
        return NextResponse.redirect(new URL("/dashboard", request.url))
      }

      // Add user info to request headers for server components
      const requestHeaders = new Headers(request.headers)
      requestHeaders.set("x-user-id", user.userId)
      requestHeaders.set("x-user-role", user.role)

      return NextResponse.next({
        request: {
          headers: requestHeaders,
        },
      })
    } catch (error) {
      console.error("[v0] JWT verification error:", error)
      const loginUrl = new URL("/auth/login", request.url)
      loginUrl.searchParams.set("redirect", pathname)
      return NextResponse.redirect(loginUrl)
    }
  }

  return NextResponse.next()
}

export const config = {
  matcher: ["/((?!api|_next/static|_next/image|favicon.ico|.*\\..*$).*)"],
}
