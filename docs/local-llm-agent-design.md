# ByteBot Local LLM Agent Design

## Summary

ByteBot is a Discord-native AI assistant for the Byte Club community. It runs against a locally hosted LLM, responds when mentioned, uses recent Discord context, stores explicit user memories, retrieves saved documents, and supports resume review.

The first implementation should be intentionally boring: one Discord bot, one FastAPI backend, one local model provider, one agent runtime, PostgreSQL with pgvector, and a small set of well-tested tools.

## Goals

- Reply to Discord mentions with concise, context-aware answers.
- Use recent Discord messages as short-term conversational context.
- Store and retrieve explicit user memories.
- Ingest uploaded resume files and review them with retrieved document context.
- Store Discord messages for future search and channel summaries.
- Keep the model provider swappable so the app can move between local and remote models later.

## Non-Goals

- Fully autonomous multi-step workflows.
- Multi-hour background tasks.
- Public hosted deployment.
- Multiple independent agent runtimes.
- Proactive replies to every message.
- A complete moderation system.
- Automatic memory extraction from all user behavior.

## Hardware Target

ByteBot should run on a local server with:

- CPU: Ryzen 9 5900X
- RAM: 32 GB DDR4
- GPU: Nvidia RTX 3050 Ti
- Storage: effectively unlimited

The GPU should be treated as constrained. The initial model should be small and quantized.

## Model Stack

The MVP uses Ollama.

Default model:

- Qwen3 4B, quantized

Candidate models to benchmark later:

- Gemma 3 4B Instruct
- Phi-4 Mini Instruct

Embeddings:

- `nomic-embed-text`

The application must not hardcode model-specific behavior throughout the codebase. All model calls go through an LLM provider abstraction.

```python
class LLMProvider:
    async def generate(self, messages: list[dict], **kwargs) -> str:
        ...

    async def stream(self, messages: list[dict], **kwargs):
        ...

    async def embed(self, text: str) -> list[float]:
        ...
```

## Architecture

```text
Discord
  -> Discord Bot
  -> FastAPI Backend
  -> Agent Runtime
  -> Tool Layer
  -> Ollama Local LLM
```

Supporting services:

```text
PostgreSQL + pgvector
Redis or lightweight job queue
Local file storage
```

## Runtime Components

### Discord Bot

The Discord bot receives message events, filters for direct mentions, fetches recent messages, downloads supported attachments, and sends replies.

In the MVP, ByteBot only replies when directly mentioned. It may still store messages from configured channels for future retrieval.

### FastAPI Backend

FastAPI owns application APIs, health checks, document ingestion endpoints, and the boundary between Discord events and the agent runtime.

Initial endpoints:

```text
POST /discord/events
POST /agent/respond
POST /documents/upload
POST /documents/{document_id}/ingest
GET /health
GET /models
```

### Agent Runtime

The agent runtime builds context, selects tools, calls the LLM, executes a single tool step when needed, and returns the final response.

The first version should use a simple single-step tool loop. Avoid recursive planning until the basic system is reliable.

### Tool Layer

Tools expose application capabilities to the agent through structured JSON.

Initial tools:

```python
search_discord_messages(query, user_id=None, channel_id=None, limit=10)
get_user_profile(user_id)
save_memory(user_id, content, memory_type="general")
retrieve_memory(user_id, query, limit=5)
get_resume(user_id)
search_documents(user_id, query, limit=5)
```

Later tools:

```python
summarize_channel(channel_id, start_time, end_time)
github_search(query)
job_posting_lookup(query)
create_study_plan(user_id, goal)
```

Tool calls should use structured JSON:

```json
{
  "type": "tool_call",
  "tool": "retrieve_memory",
  "args": {
    "user_id": "123",
    "query": "career goals",
    "limit": 5
  }
}
```

Final answers should also use structured output internally:

```json
{
  "type": "final",
  "content": "Here's what I found..."
}
```

## Request Flow

For each incoming Discord mention:

```text
1. Receive Discord event.
2. Identify user, channel, thread, and guild.
3. Persist the incoming message.
4. Fetch recent channel or thread messages.
5. Retrieve relevant user memories.
6. Retrieve relevant documents.
7. Build the prompt.
8. Call the LLM.
9. Parse the model response.
10. Execute one tool call if needed.
11. Generate the final response.
12. Send the Discord reply.
13. Persist the interaction.
```

## Context Strategy

The model is small, so context quality matters more than raw context size. ByteBot should retrieve relevant context instead of dumping full message histories or full resumes into the prompt.

Suggested first-pass token budget:

```text
System prompt:              500 tokens
Recent Discord messages:  1,000 tokens
User memory:                500 tokens
Retrieved documents:      1,500 tokens
Response budget:          1,000 tokens
```

Context sources:

- Recent channel or thread messages.
- Explicit user memory.
- Retrieved documents.
- Byte Club static knowledge.

## Memory Policy

The MVP uses explicit memory only.

ByteBot may save a memory when:

- The user directly asks ByteBot to remember something.
- A feature clearly requires persistence, such as a saved resume or profile detail.

ByteBot should not silently infer and store personal facts from ordinary channel conversation in the MVP.

## Resume Review

### Ingestion

```text
1. User uploads a resume PDF or text file.
2. Bot downloads the attachment.
3. Backend extracts text.
4. Original file is stored locally.
5. Raw text is stored in the documents table.
6. Text is split into chunks.
7. Chunks are embedded.
8. Chunks are stored in document_chunks.
```

### Review

```text
1. User asks: "@ByteBot review my resume for backend roles".
2. Runtime retrieves the user's latest resume.
3. Runtime searches resume chunks for relevant sections.
4. Runtime adds the resume-review rubric to the prompt.
5. LLM generates structured feedback.
```

Resume review response format:

```text
Strengths
Gaps
Bullet rewrites
Missing keywords
Suggested next edits
```

When rewriting bullets, ByteBot must preserve the user's actual experience. It should not invent metrics, employers, technologies, or achievements.

## Prompting

Base system prompt:

```text
You are ByteBot, a helpful programming and career assistant for the Byte Club Discord community.

You help users with software engineering, interview prep, projects, resumes, and learning plans.

Use the provided context. Do not claim to know facts not present in the context. If context is missing, say what you need.

When tools are available, use them only when needed.

Keep Discord responses concise, practical, and friendly.
```

Resume review prompt addendum:

```text
You are reviewing a resume for a software engineering role.

Give direct, specific feedback.

Focus on:
- impact
- clarity
- technical depth
- role fit
- missing keywords
- weak bullets

When rewriting bullets, preserve the user's actual experience. Do not invent metrics or technologies.
```

## Database Design

Use PostgreSQL with pgvector enabled.

### users

```sql
CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  discord_user_id TEXT UNIQUE NOT NULL,
  username TEXT,
  created_at TIMESTAMP DEFAULT now(),
  updated_at TIMESTAMP DEFAULT now()
);
```

### guilds

```sql
CREATE TABLE guilds (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  discord_guild_id TEXT UNIQUE NOT NULL,
  name TEXT,
  created_at TIMESTAMP DEFAULT now()
);
```

### channels

```sql
CREATE TABLE channels (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  discord_channel_id TEXT UNIQUE NOT NULL,
  guild_id UUID REFERENCES guilds(id),
  name TEXT,
  is_ingestion_enabled BOOLEAN DEFAULT false,
  created_at TIMESTAMP DEFAULT now()
);
```

### messages

```sql
CREATE TABLE messages (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  discord_message_id TEXT UNIQUE NOT NULL,
  channel_id UUID REFERENCES channels(id),
  user_id UUID REFERENCES users(id),
  content TEXT,
  created_at TIMESTAMP,
  inserted_at TIMESTAMP DEFAULT now()
);
```

### memories

```sql
CREATE TABLE memories (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id),
  content TEXT NOT NULL,
  memory_type TEXT DEFAULT 'general',
  source_message_id UUID REFERENCES messages(id),
  created_at TIMESTAMP DEFAULT now(),
  updated_at TIMESTAMP DEFAULT now()
);
```

### documents

```sql
CREATE TABLE documents (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id),
  title TEXT,
  document_type TEXT,
  storage_path TEXT,
  raw_text TEXT,
  created_at TIMESTAMP DEFAULT now()
);
```

### document_chunks

```sql
CREATE TABLE document_chunks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  document_id UUID REFERENCES documents(id),
  chunk_index INTEGER,
  content TEXT NOT NULL,
  embedding vector(768),
  created_at TIMESTAMP DEFAULT now()
);
```

### bot_interactions

```sql
CREATE TABLE bot_interactions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id),
  channel_id UUID REFERENCES channels(id),
  input_message_id UUID REFERENCES messages(id),
  prompt TEXT,
  response TEXT,
  model TEXT,
  created_at TIMESTAMP DEFAULT now()
);
```

## Repo Structure

```text
bytebot/
  app/
    main.py
    config.py

    discord/
      bot.py
      events.py
      formatting.py

    agent/
      runtime.py
      prompts.py
      tools.py
      context_builder.py
      llm_provider.py

    models/
      ollama.py

    memory/
      service.py

    documents/
      ingestion.py
      chunking.py
      embeddings.py
      resume_review.py

    db/
      session.py
      models.py
      migrations/

    tests/
      test_context_builder.py
      test_memory.py
      test_resume_review.py
      test_tools.py

  docker-compose.yml
  pyproject.toml
  README.md
```

## Technology Choices

- Python
- FastAPI
- discord.py
- SQLAlchemy
- Alembic
- PostgreSQL
- pgvector
- Ollama
- pydantic-settings
- pytest

Use async where it materially helps, especially for Discord, FastAPI handlers, database calls, and model requests.

## Engineering Decisions

### Mention-only first

ByteBot replies only when directly mentioned. Channel-wide ingestion is opt-in per channel.

### One runtime first

Use one agent runtime with different prompts and tools. Do not build multiple independent agents yet.

### Local model first

Use Ollama locally for the MVP, but keep the LLM provider interface stable enough to add remote providers later.

### Retrieval over giant prompts

Retrieve relevant context from Discord messages, memories, and documents. Do not send entire channel histories or entire resumes to the model.

### Explicit memory first

Only save memories when the user asks or when a feature clearly needs it. Avoid automatic personal profiling in the MVP.

## Testing Strategy

MVP tests should cover:

- Context budget construction.
- Recent message formatting.
- Memory save and retrieval.
- Document chunking.
- Embedding search over document chunks.
- Resume review prompt assembly.
- Tool call parsing.
- LLM provider interface behavior using a fake provider.

Integration tests should use a fake Discord event payload and a fake LLM provider so the core request flow can be tested without Discord or Ollama.

## Acceptance Criteria

The MVP is complete when:

- ByteBot replies when mentioned in Discord.
- Replies include recent channel or thread messages as context.
- Discord messages are stored in PostgreSQL.
- User memories can be saved and retrieved.
- Resume files can be ingested.
- Resume reviews use retrieved resume chunks.
- The LLM provider can be swapped.
- Qwen3 4B runs through Ollama.
- Basic tests cover context building and retrieval.

## Implementation Plan

1. Scaffold the Python repo.
2. Add FastAPI app and configuration.
3. Add Discord bot event handling.
4. Add SQLAlchemy models and Alembic migrations.
5. Add the Ollama provider.
6. Add the context builder.
7. Add the simple agent runtime.
8. Add memory tools.
9. Add document ingestion and chunking.
10. Add resume review flow.
11. Add tests around context, retrieval, tools, and resume prompts.

## Open Questions

- Which Discord guild and channels should enable message ingestion first?
- Should uploaded resumes be private to each user, visible to admins, or both?
- What file types should be supported beyond PDF and plain text?
- How long should raw Discord messages be retained?
- Should ByteBot support slash commands in addition to mentions?
- Should summaries use stored messages only, or fetch live Discord history on demand?
