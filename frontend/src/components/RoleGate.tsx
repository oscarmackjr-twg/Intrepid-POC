import { ReactNode } from 'react'
import { Navigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'

interface RoleGateProps {
  allowed: string[]
  children: ReactNode
}

/** Renders children only if the current user's role is in the allowed list.
 *  Redirects to /dashboard otherwise. */
export default function RoleGate({ allowed, children }: RoleGateProps) {
  const { user } = useAuth()

  if (!user || !allowed.includes(user.role)) {
    return <Navigate to="/dashboard" replace />
  }

  return <>{children}</>
}
