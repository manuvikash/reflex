# Migration from Claude to Gemini

## Summary

SafeRunner has been migrated from Anthropic Claude to Google Gemini for AI-powered patch generation.

## Changes Made

### 1. Code Changes

- **`control/patcher.py`**: Replaced Anthropic client with Google Gemini
  - Changed from `anthropic` to `google-generativeai` package
  - Updated API calls to use Gemini's `generate_content()` method
  - Model default: `gemini-1.5-pro`

- **`control/github_api.py`**: Updated parameter names
  - `claude_reasoning` → `ai_reasoning`

- **`control/worker.py`**: Updated comments and log messages
  - References to Claude changed to Gemini

### 2. Dependencies

- **`requirements.txt`**: 
  - Removed: `anthropic==0.34.2`
  - Added: `google-generativeai>=0.8.0`

### 3. Environment Variables

Update your `.env` file with:

```bash
# Remove these:
# ANTHROPIC_API_KEY=...
# ANTHROPIC_MODEL=...

# Add these:
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-1.5-pro
```

## Getting a Gemini API Key

1. Go to [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Click "Get API Key"
3. Create a new API key or use an existing one
4. Copy the key to your `.env` file

## Testing

After updating your `.env` file, restart the server:

```bash
make server
```

The system will now use Gemini for patch generation instead of Claude.

## API Differences

### Claude (Before)
```python
response = self.client.messages.create(
    model=self.model,
    max_tokens=4096,
    system=system_prompt,
    messages=[{"role": "user", "content": user_prompt}],
)
content = response.content[0].text
```

### Gemini (After)
```python
full_prompt = f"{system_prompt}\n\n{user_prompt}"
response = self.model.generate_content(
    full_prompt,
    generation_config=genai.types.GenerationConfig(
        max_output_tokens=4096,
        temperature=0.2,
    ),
)
content = response.text
```

## Notes

- Gemini API has a generous free tier
- `gemini-1.5-pro` is recommended for code generation tasks
- Temperature set to 0.2 for more deterministic outputs
- All other functionality remains unchanged
