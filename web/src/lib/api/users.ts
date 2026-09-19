import type { User } from '@/lib/types'
import { http, USE_MOCK } from './http'
import { DEMO_USERS } from '@/lib/mocks/seed'

interface UsersResponse {
    status: string
    data: {
        user_id: string
        name: string
        email: string
    }[]
}

export async function listUsers(): Promise<User[]> {
    if (USE_MOCK) {
        return DEMO_USERS
    }

    const response = await http<UsersResponse>('/api/users')

    return response.data.map((user) => ({
        userId: user.user_id,
        name: user.name,
    }))
}