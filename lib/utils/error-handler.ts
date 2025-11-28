import { NextResponse } from "next/server"
import { logger } from "./logger"

export class AppError extends Error {
  public statusCode: number
  public code: string
  public isOperational: boolean

  constructor(message: string, statusCode = 500, code = "INTERNAL_ERROR", isOperational = true) {
    super(message)
    this.statusCode = statusCode
    this.code = code
    this.isOperational = isOperational

    Error.captureStackTrace(this, this.constructor)
  }
}

export class ValidationError extends AppError {
  constructor(message: string, details?: Record<string, unknown>) {
    super(message, 400, "VALIDATION_ERROR")
    if (details) {
      ;(this as unknown as Record<string, unknown>).details = details
    }
  }
}

export class AuthenticationError extends AppError {
  constructor(message = "Authentication required") {
    super(message, 401, "AUTHENTICATION_ERROR")
  }
}

export class AuthorizationError extends AppError {
  constructor(message = "Access denied") {
    super(message, 403, "AUTHORIZATION_ERROR")
  }
}

export class NotFoundError extends AppError {
  constructor(resource: string) {
    super(`${resource} not found`, 404, "NOT_FOUND")
  }
}

export class RateLimitError extends AppError {
  constructor(retryAfter?: number) {
    super("Too many requests", 429, "RATE_LIMIT_EXCEEDED")
    if (retryAfter) {
      ;(this as unknown as Record<string, unknown>).retryAfter = retryAfter
    }
  }
}

export class ExchangeError extends AppError {
  constructor(exchange: string, message: string) {
    super(`${exchange}: ${message}`, 502, "EXCHANGE_ERROR")
  }
}

export class DatabaseError extends AppError {
  constructor(operation: string, message: string) {
    super(`Database ${operation} failed: ${message}`, 503, "DATABASE_ERROR")
  }
}

// Error response handler
export function handleError(error: unknown): NextResponse {
  // Log the error
  if (error instanceof AppError) {
    logger.error(error.message, {
      code: error.code,
      statusCode: error.statusCode,
      stack: error.stack,
    })

    return NextResponse.json(
      {
        success: false,
        error: {
          message: error.message,
          code: error.code,
          ...((error as unknown as Record<string, unknown>).details && {
            details: (error as unknown as Record<string, unknown>).details,
          }),
        },
      },
      { status: error.statusCode },
    )
  }

  // Unknown error
  const message = error instanceof Error ? error.message : "An unexpected error occurred"
  const stack = error instanceof Error ? error.stack : undefined

  logger.error("Unhandled error", { message, stack })

  return NextResponse.json(
    {
      success: false,
      error: {
        message: process.env.NODE_ENV === "production" ? "An unexpected error occurred" : message,
        code: "INTERNAL_ERROR",
      },
    },
    { status: 500 },
  )
}

// Async route wrapper for consistent error handling
export function withErrorHandling<T>(
  handler: (req: Request) => Promise<T>,
): (req: Request) => Promise<NextResponse | T> {
  return async (req: Request) => {
    try {
      return await handler(req)
    } catch (error) {
      return handleError(error)
    }
  }
}
