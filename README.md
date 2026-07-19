# Stock Review Backend API

FastAPI backend for Stock Review iOS app with Agent-powered analysis.

## Architecture

- **FastAPI**: API Gateway and middleware
- **Supabase**: Authentication and PostgreSQL database
- **Agent (Agno)**: AI-powered analysis with tools
  - YFinance Tool: Real-time market data
  - Memory Tool: Historical pattern analysis
  - Note Manager: Database operations

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp env.example .env
```

Required variables:
- `SUPABASE_URL`: Your Supabase project URL
- `SUPABASE_KEY`: Supabase anon key
- `SUPABASE_SERVICE_KEY`: Supabase service role key
- `DATABASE_URL`: PostgreSQL connection string
- `DEEPSEEK_API_KEY` or `OPENAI_API_KEY`: LLM API key
- `JWT_SECRET`: JWT secret for token verification

### 3. Run Database Migrations

Execute the SQL migration file in your Supabase SQL editor:

```bash
# Copy contents of supabase/migrations/001_initial_schema.sql
# and run in Supabase Dashboard > SQL Editor
```

### 4. Run the Server

```bash
python main.py
```

Or with uvicorn:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## API Endpoints

### Health Check
- `GET /api/health` - Health check

### Authentication
- `GET /api/auth/me` - Get current user info

### Notes
- `POST /api/notes` - Create a new reflection note
- `GET /api/notes` - List notes (with filtering and search)
- `GET /api/notes/{note_id}` - Get a specific note
- `GET /api/notes/stream/{note_id}` - Stream AI analysis (SSE)
- `DELETE /api/notes/{note_id}` - Delete a note
- `GET /api/notes/history/weekly` - Get weekly history for agent context

## Deployment

### Railway

1. Create a new Railway project
2. Connect your GitHub repository
3. Set environment variables in Railway dashboard
4. Deploy

### AWS

1. Use AWS App Runner or Elastic Beanstalk
2. Set environment variables
3. Configure CORS for your iOS app domain

## Database Schema

- `user_profiles`: User profile information
- `reflection_notes`: Core reflection notes
- `session_context`: Agent conversation history

All tables have Row Level Security (RLS) enabled for user isolation.
