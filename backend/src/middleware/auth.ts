import { FastifyRequest, FastifyReply } from 'fastify';
import { supabase } from '../lib/supabaseClient';

export async function requireAuth(request: FastifyRequest, reply: FastifyReply) {
  const authHeader = request.headers.authorization;
  if (!authHeader) {
    return reply.code(401).send({ error: 'No authorization header' });
  }

  try {
    const token = authHeader.replace('Bearer ', '');

    // Check if token is service role key
    if (token === process.env.SUPABASE_SERVICE_ROLE_KEY) {
      // Admin access
      request.user = { id: 'admin', role: 'service_role' } as any;
      return;
    }

    // Regular token auth
    const {
      data: { user },
      error,
    } = await supabase.auth.getUser(token);

    if (error || !user) {
      return reply.code(401).send({ error: 'Unauthorized' });
    }

    request.user = user;
  } catch (error) {
    return reply.code(401).send({ error: 'Invalid token' });
  }
}

export async function requireAdmin(request: FastifyRequest, reply: FastifyReply) {
  const authHeader = request.headers.authorization;
  if (!authHeader) {
    return reply.code(401).send({ error: 'No authorization header' });
  }

  try {
    const token = authHeader.replace('Bearer ', '');

    // If using API key, allow access
    if (token === process.env.SUPABASE_API_KEY) {
      request.user = { id: 'admin', role: 'service_role' } as any;
      return;
    }

    // Regular token auth
    const {
      data: { user },
      error,
    } = await supabase.auth.getUser(token);
    if (error || !user) {
      return reply.code(401).send({ error: 'Unauthorized' });
    }

    // Check if user is admin
    const { data: userData, error: roleError } = await supabase
      .from('users')
      .select('role')
      .eq('id', user.id)
      .single();

    if (roleError || userData?.role !== 'admin') {
      return reply.code(403).send({ error: 'Admin access required' });
    }

    request.user = user;
  } catch (error) {
    return reply.code(401).send({ error: 'Invalid token' });
  }
}
