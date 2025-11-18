# SmartTodo

AI-powered task management system with natural language processing. SmartTodo combines traditional CRUD operations with sophisticated AI-driven task manipulation through natural language commands.

## Features

- **Natural Language Processing**: Interact with your tasks using plain English commands
- **Smart State Machine**: Safely stage and commit multiple operations in a single transaction
- **Advanced Authorization**: Scope-based access control with recursive group resolution
- **Task Dependencies**: Define prerequisites and automatically validate completion order
- **Recurring Tasks**: Automatically create new instances when completing recurring tasks
- **Group Management**: Organize users and nested groups with circular reference prevention
- **OpenTelemetry Integration**: Full observability with traces, metrics, and logs
- **OpenRouter LLM Support**: Swap LLM providers easily through OpenRouter

## Technology Stack

- **Framework**: FastAPI
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Migrations**: Alembic
- **Authentication**: JWT Bearer tokens + API tokens
- **Password Hashing**: bcrypt
- **Validation**: Pydantic v2
- **LLM Provider**: OpenRouter (supports multiple models)
- **Observability**: OpenTelemetry with OpenInference conventions
- **Package Manager**: uv

## Quick Start

### Prerequisites

- Python 3.13+
- PostgreSQL 12+
- uv package manager

### Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/smart-todo.git
cd smart-todo
```

2. Install dependencies using uv:
```bash
uv sync
```

3. Copy the environment template:
```bash
cp .env.example .env
```

4. Configure your environment variables in `.env`:
   - Set `DATABASE_URL` to your PostgreSQL connection string
   - Set `LLM_API_KEY` to your OpenRouter API key
   - Set `SECRET_KEY` to a secure random value (at least 32 characters)

### Database Setup

1. Create the database:
```bash
createdb smart_todo
```

2. Run migrations:
```bash
uv run alembic upgrade head
```

### Running the Application

Start the development server:
```bash
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Or use the Python module directly:
```bash
uv run python -m app.main
```

The API will be available at `http://localhost:8000`

## API Documentation

Once the application is running, visit:
- **Interactive API docs**: http://localhost:8000/docs
- **Alternative docs**: http://localhost:8000/redoc

## Usage Examples

### 1. Register a User

```bash
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "alice",
    "password": "securepassword123"
  }'
```

### 2. Get API Token

```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "alice",
    "password": "securepassword123"
  }'
```

Response:
```json
{
  "access_token": "your-token-here",
  "token_type": "bearer"
}
```

### 3. Create a Task

```bash
curl -X POST http://localhost:8000/api/tasks \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Buy groceries",
    "description": "Weekly shopping",
    "urgency": "high",
    "due_date": "2025-01-20"
  }'
```

### 4. Use Natural Language Processing

```bash
curl -X POST http://localhost:8000/api/tasks/process \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Create a task to buy milk with high urgency due tomorrow, then create another task to cook dinner that depends on the milk task"
  }'
```

### 5. List Tasks

```bash
curl http://localhost:8000/api/tasks \
  -H "Authorization: Bearer YOUR_TOKEN"
```

Filter by status:
```bash
curl http://localhost:8000/api/tasks?status=todo \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 6. Complete a Task

```bash
curl -X POST http://localhost:8000/api/tasks/1/complete \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 7. Create a Group

```bash
curl -X POST http://localhost:8000/api/groups \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Engineering Team",
    "description": "Software engineering team"
  }'
```

### 8. Add Member to Group

```bash
curl -X POST http://localhost:8000/api/groups/1/members \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 2
  }'
```

## Configuration

All configuration is done through environment variables. See `.env.example` for all available options.

### Key Configuration Options

#### Database
- `DATABASE_URL`: PostgreSQL connection URL
- `DB_POOL_SIZE`: Connection pool size (default: 10)
- `DB_MAX_OVERFLOW`: Max overflow connections (default: 20)

#### LLM Provider
- `LLM_PROVIDER`: Provider type (default: openrouter)
- `LLM_BASE_URL`: API base URL
- `LLM_API_KEY`: API key for authentication
- `LLM_MODEL`: Model to use (e.g., anthropic/claude-3.5-sonnet)
- `LLM_TEMPERATURE`: Temperature for generation (default: 0.7)

#### Security
- `SECRET_KEY`: Secret key for signing tokens (minimum 32 characters)
- `PASSWORD_MIN_LENGTH`: Minimum password length (default: 12)
- `SESSION_TOKEN_EXPIRE_DAYS`: Session token expiration (default: 14)

#### OpenTelemetry
- `OTEL_ENABLED`: Enable/disable telemetry (default: true)
- `OTEL_SERVICE_NAME`: Service name for traces
- `OTEL_EXPORTER_OTLP_ENDPOINT`: OTLP endpoint URL
- `OTEL_EXPORTER_OTLP_HEADERS`: Headers for authentication

## Natural Language Commands

The NLP endpoint supports complex multi-step operations:

- **Create tasks**: "Create a task to buy milk"
- **Set urgency**: "Create a high-priority task to fix the bug"
- **Set due dates**: "Create a task to submit report due next Friday"
- **Add dependencies**: "Create task A, then create task B that depends on task A"
- **Update tasks**: "Update task 5 to mark it as in progress"
- **Complete tasks**: "Complete task 3"
- **Recurring tasks**: "Create a daily task to check emails"

## Architecture

### State Machine

SmartTodo uses a sophisticated state machine to safely handle LLM-driven operations:

1. **awaiting_command**: Ready to receive commands
2. **editing_task**: Currently editing a specific task
3. **completed**: Session finished, all operations committed

All operations are staged in memory and committed atomically in a single database transaction.

### Authorization

Scope-based authorization ensures users can only access tasks they:
- Own (created the task)
- Are assigned to
- Are in a group that's assigned to the task (recursively resolved)

### Task Dependencies

Tasks can have prerequisites that must be completed first. The system automatically validates the dependency chain before allowing task completion.

### Recurring Tasks

When a recurring task is completed, a new instance is automatically created with:
- The same title, description, and settings
- Updated due date based on recurrence pattern (daily, weekly, monthly, yearly)
- Same prerequisites and assignees

## Development

### Running Tests

```bash
uv run pytest
```

### Running Migrations

Create a new migration:
```bash
uv run alembic revision --autogenerate -m "description"
```

Apply migrations:
```bash
uv run alembic upgrade head
```

Rollback one migration:
```bash
uv run alembic downgrade -1
```

### Code Quality

The codebase follows these standards:
- Type hints throughout
- Pydantic for validation
- SQLAlchemy 2.0 style
- Async/await for I/O operations
- OpenTelemetry for observability

## OpenTelemetry Integration

SmartTodo is fully instrumented with OpenTelemetry, following OpenInference conventions for AI observability:

- **Traces**: Full request tracing with parent-child relationships
- **Metrics**: Task operations, LLM requests, database queries
- **Logs**: Structured JSON logging with trace correlation
- **OpenInference**: LLM spans include model, prompts, tools, and session tracking

Connect to Phoenix or any OTLP-compatible backend for visualization.

## Troubleshooting

### Database Connection Issues

Ensure PostgreSQL is running and accessible:
```bash
psql $DATABASE_URL
```

### LLM API Errors

Check your OpenRouter API key and model availability:
- Verify `LLM_API_KEY` is set correctly
- Ensure the specified `LLM_MODEL` is available on OpenRouter
- Check OpenRouter dashboard for usage and errors

### Migration Issues

If migrations fail, check:
- Database connection
- Existing schema state
- Migration history: `uv run alembic history`

## License

MIT

## Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## Support

For issues and questions:
- GitHub Issues: https://github.com/yourusername/smart-todo/issues
- Documentation: See `/docs` endpoint when running

## Acknowledgments

This Python implementation is based on the original Elixir SmartTodo specification, recreated with modern Python best practices and tools.