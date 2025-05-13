# Docker Development Environment

This project can use Docker for development and deployment. The setup includes three services:

1. **encyc-tng**: The main application container
2. **db**: PostgreSQL 16 database
3. **redis**: Redis 6 cache server

## Building and Running

```bash
# Build and start all services
docker-compose up --build

# Stop all services
docker-compose down
```

The application will be available at `http://localhost:8082`

## Development with Docker

The Dockerfile sets up a development environment with:

- Debian stable-slim base image
- Common build dependencies
- Git configuration for the encyc-core repository
- Application installation via Makefile targets

### Build Arguments

Key build arguments that can be customized:

- `UID`: User ID (default: 1000)
- `GID`: Group ID (default: 1000)
- `USERNAME`: Username (default: encyc)

To rebuild with custom user/group IDs:

```bash
docker-compose build --build-arg UID=$(id -u) --build-arg GID=$(id -g)
```

### Service Configuration

#### PostgreSQL Database

- Version: 16 (Alpine-based)
- Default credentials:
  - User: encyctng
  - Password: encyctng
- Data is persisted in a Docker volume

#### Redis Cache

- Version: 6 (Alpine-based)
- Used for caching and session management
- Exposed on port 6379

### Troubleshooting

If you encounter permission issues:

1. Check that your user/group IDs match the container's
2. Rebuild with custom UID/GID as shown above
3. Ensure the encyc-core repository is properly cloned and accessible

For database connection issues:

1. Verify the database container is running: `docker-compose ps`
2. Check database logs: `docker-compose logs db`
3. Ensure the application configuration matches the database credentials
