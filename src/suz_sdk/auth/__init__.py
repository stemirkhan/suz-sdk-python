"""Auth module for the SUZ SDK.

Provides:
    TrueApiAuth   — two-step True API (GIS MT) authentication flow (§9.3.2)
    TokenManager  — thread-safe token cache with TTL tracking and pre-refresh
    AuthApi       — public ``client.auth`` interface
"""
