import { FastifyInstance, FastifyReply, FastifyRequest } from 'fastify';
import { supabase } from '../lib/supabaseClient';
import { logError } from '../utils/logger';

interface LoginBody {
  email: string;
  password: string;
}

interface RefreshBody {
  refresh_token: string;
}

export async function authRoutes(fastify: FastifyInstance) {
  fastify.post(
    '/login',
    async (request: FastifyRequest<{ Body: LoginBody }>, reply: FastifyReply) => {
      try {
        const { email, password } = request.body;
        fastify.log.info(`Login attempt for ${email}`);

        // First authenticate the user
        const { data, error } = await supabase.auth.signInWithPassword({
          email,
          password,
        });

        if (error) {
          fastify.log.error('Auth error:', error);
          throw error;
        }

        fastify.log.info('User authenticated:', data.user?.id);

        // Create admin client with service role
        const adminClient = supabase.auth.admin;
        const { data: roleData, error: roleError } = await supabase
          .from('users')
          .select('role')
          .eq('id', data.user.id)
          .single();

        if (roleError) {
          fastify.log.error('Role check error:', roleError);
          throw roleError;
        }

        fastify.log.info('User role:', roleData?.role);

        if (roleData?.role === 'admin') {
          fastify.log.info('Admin user detected');
          return reply.send({
            access_token: process.env.SUPABASE_API_KEY,
            refresh_token: data.session.refresh_token,
            user: { ...data.user, role: 'admin' },
          });
        }

        // For regular users, return normal tokens
        return reply.send({
          access_token: data.session.access_token,
          refresh_token: data.session.refresh_token,
          user: data.user,
        });
      } catch (error) {
        logError('Login failed', error);
        return reply.code(401).send({ error: 'Invalid credentials' });
      }
    },
  );

  fastify.post(
    '/refresh',
    async (request: FastifyRequest<{ Body: RefreshBody }>, reply: FastifyReply) => {
      try {
        const { refresh_token } = request.body;

        const { data, error } = await supabase.auth.refreshSession({
          refresh_token,
        });

        if (error) throw error;

        return reply.send({
          access_token: data.session?.access_token,
          refresh_token: data.session?.refresh_token, // New refresh token
          user: data.user,
        });
      } catch (error) {
        logError('Token refresh failed', error);
        return reply.code(401).send({ error: 'Invalid refresh token' });
      }
    },
  );
}
