# CIAO-Code-In-Architecture-Out

CIAO is a command‑line tool that flattens a code repository with Repomix and then uses the OpenAI API to generate Markdown documentation asynchronously.

## Prerequisites

- Python 3.11 or later installed and available.
- [uv](https://docs.astral.sh/uv/) installed (package manager).
- The `repomix` CLI installed and available on your PATH.
- Either:
  - An OpenAI API key set in the environment variable `OPENAI_API_KEY`, **or**
  - A self-hosted model via [Ollama](https://ollama.com) or [llama.cpp](https://github.com/ggerganov/llama.cpp) exposing an OpenAI-compatible API.

## Installation

1. Clone the repository
2. Open terminal inside the repository folder
3. Install dependencies with uv:

   ```bash
   cd CIAO-system
   uv sync
   ```

4. Copy the example environment file and adjust it:

   ```bash
   cp .env.example .env
   ```

5. Edit `.env` to choose OpenAI or a self-hosted model.

## Configuration

The tool supports three modes of operation. Edit `.env` to switch between them:

### 1. OpenAI (default)

```bash
OPENAI_API_KEY=sk-your-openai-key-here
# LLM_MODEL=gpt-5-2025-08-07  # optional
```

### 2. Ollama (local / self-hosted)

Ensure Ollama is running with the model you want to use, e.g.:

```bash
ollama pull llama3.1:70b
ollama serve
```

Then set in `.env`:

```bash
LLM_BASE_URL=http://localhost:11434/v1
LLM_MODEL=llama3.1:70b
# LLM_API_KEY is optional for Ollama (defaults to "no-key")
```

### 3. llama.cpp (local / self-hosted)

Start llama.cpp with the OpenAI-compatible server, e.g.:

```bash
# Using llama.cpp server example
./server -m models/your-model.gguf --port 8080
```

Then set in `.env`:

```bash
LLM_BASE_URL=http://localhost:8080/v1
LLM_MODEL=your-model-name
# LLM_API_KEY is optional (defaults to "no-key")
```

## Usage

1. Ensure `.env` is configured as shown above.
2. Set `repomix.config.json` file to include exclude programming languages.
3. Run CIAO on a repository:

   ```bash
   cd CIAO-system
   uv run main.py <github repo link or local repo>
   ```

   Or activate the virtual environment first:

   ```bash
   source .venv/bin/activate
   python main.py <github repo link or local repo>
   ```

When the run completes successfully, CIAO will:

- Use Repomix (and `repomix.config.json`) to flatten the repository into `full_code.txt`.
- Load documentation templates and guidelines from `prompt.json`.
- Generate documentation sections in parallel and write the final Markdown document to `documentation.txt` in the CIAO project directory.


## Data Folder 
As supplemental material the data folder contains:

- Repo folder, containing all the generated markdown documentations with the images.
- A copy of the survey.
- Results of the survey.










