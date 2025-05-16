# Network Configuration for WebSocket Server
# Use '0.0.0.0' to listen on all interfaces for external access,
# or '127.0.0.1' for local development only.
SERVER_HOST = '0.0.0.0'
SERVER_PORT = 8765       # Choose an available port, often > 1024

# Game Configuration (retained)
LOBBY_CONCEPT_NAME = 'lobby' # Conceptual name for server logic
GAME_CHANNEL_PREFIX = 'game_' # Still useful for game-specific messaging logic

# END OF FILE config.py