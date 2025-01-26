# Technical Decisions Documentation

## Authentication System Evolution

### Initial Approach: Supabase

We initially planned to use Supabase as our authentication provider because:

- Built-in user management
- Ready-to-use authentication APIs
- Row Level Security (RLS) features
- Real-time capabilities
- PostgreSQL database management

### Why We Pivoted Away from Supabase

1. **Control and Flexibility**

   - Limited control over token lifecycle
   - Constrained by Supabase's authentication flow
   - Difficulty in implementing custom user number-based login
   - Challenges with custom session management

2. **Custom Requirements**
   - Need for user_number-based authentication instead of email
   - Custom refresh token rotation logic
   - Specific session tracking requirements
   - Device-based authentication tracking

### Current Implementation: Custom JWT Authentication

#### Core Components

1. **Token Generation (`platform/token`)**

   ```go
   - Access Tokens (JWT)
   - Refresh Tokens (Secure random)
   - Token hashing and verification
   ```

2. **Authentication Service (`server/service`)**

   ```go
   - Login logic
   - Token refresh
   - Session management
   - Logout capabilities
   ```

3. **Database Schema**
   ```sql
   - users table (user_number based)
   - refresh_tokens table
   - Session tracking columns
   ```

#### Key Features

1. **User Number Authentication**

   - 10-digit unique identifier
   - Password-based authentication
   - Role-based access control

2. **Token Management**

   - Short-lived access tokens (15 minutes)
   - Long-lived refresh tokens (7 days)
   - Secure token rotation
   - Token revocation capabilities

3. **Session Control**

   - Device tracking
   - Multiple session support
   - Global logout capability
   - IP and User-Agent tracking

4. **Security Measures**
   - Password hashing with bcrypt
   - Token hashing for storage
   - Cryptographically secure random token generation
   - Protection against token reuse

### Benefits of Current Approach

1. **Complete Control**

   - Custom authentication flows
   - Flexible token management
   - Full control over user data
   - Custom session handling

2. **Performance**

   - Direct database access
   - Optimized queries
   - No external API calls
   - Reduced latency

3. **Security**

   - Custom security implementations
   - Token rotation policies
   - Session invalidation
   - Audit capabilities

4. **Cost Effectiveness**
   - No third-party service costs
   - Scalable infrastructure
   - Predictable pricing
   - Resource optimization

### Future Improvements

1. **Testing**

   - Unit tests for token generation
   - Integration tests for auth flow
   - Performance testing
   - Security testing

2. **Features**

   - Rate limiting
   - Enhanced audit logging
   - Password reset flow
   - Account lockout policies

3. **Security Enhancements**

   - 2FA support
   - IP-based restrictions
   - Enhanced session monitoring
   - Automated security alerts

4. **Monitoring**
   - Token usage metrics
   - Authentication attempts logging
   - Performance monitoring
   - Security event tracking

## Conclusion

While Supabase offers excellent features for many use cases, our specific requirements necessitated a custom implementation. The current solution provides the flexibility and control needed for our unique authentication requirements while maintaining security and performance standards.

The custom JWT implementation allows us to:

- Handle user_number-based authentication
- Implement precise session control
- Manage token lifecycle
- Track device-specific sessions
- Implement custom security policies

This approach has proven more suitable for our needs while providing a foundation for future enhancements and security improvements.
