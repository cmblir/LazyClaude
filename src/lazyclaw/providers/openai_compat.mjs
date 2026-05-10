// Generic OpenAI-compatible Chat Completions streaming provider.
//
// Targets any endpoint that speaks the OpenAI v1 wire format:
//   - NVIDIA NIM            (https://integrate.api.nvidia.com/v1)
//   - OpenRouter            (https://openrouter.ai/api/v1)
//   - Together AI           (https://api.together.xyz/v1)
//   - Groq                  (https://api.groq.com/openai/v1)
//   - DeepInfra / Fireworks / Anyscale / Mistral La Plateforme / etc.
//   - vLLM, LM Studio, llama.cpp, text-generation-inference local servers
//
// Built so the picker can register a new endpoint at setup time without
// shipping a per-vendor provider file. The factory returns a Provider
// object the registry can drop into PROVIDERS as-is.
//
// Wire format reference (matches openai.mjs almost line-for-line; the
// only knobs are the base URL, optional extra headers, and the api-key
// closure):
//   POST <baseUrl>/chat/completions
//   Authorization: Bearer <key>
//   {"model": "...", "stream": true, "messages": [...]}

const DEFAULT_MAX_TOKENS = 4096;

class InvalidApiKeyError extends Error {
  constructor(message = 'invalid api key') {
    super(message);
    this.name = 'InvalidApiKeyError';
    this.code = 'INVALID_KEY';
  }
}

class AbortError extends Error {
  constructor(message = 'aborted') {
    super(message);
    this.name = 'AbortError';
    this.code = 'ABORT';
  }
}

class RateLimitError extends Error {
  constructor(retryAfterMs, body = '') {
    super(`openai-compat 429: rate limited (retry-after ${retryAfterMs}ms)`);
    this.name = 'RateLimitError';
    this.code = 'RATE_LIMIT';
    this.status = 429;
    this.retryAfterMs = retryAfterMs;
    this.body = body;
  }
}

class ApiError extends Error {
  constructor(status, body) {
    super(`openai-compat ${status}: ${String(body).slice(0, 200)}`);
    this.name = 'OpenAiCompatApiError';
    this.status = status;
    this.body = body;
  }
}

function parseRetryAfterMs(headers) {
  let raw = null;
  if (headers && typeof headers.get === 'function') raw = headers.get('retry-after') || headers.get('Retry-After');
  else if (headers) raw = headers['retry-after'] || headers['Retry-After'];
  if (!raw) return 1000;
  const asInt = parseInt(String(raw), 10);
  if (!Number.isNaN(asInt)) return Math.max(0, asInt * 1000);
  const date = Date.parse(String(raw));
  if (!Number.isNaN(date)) return Math.max(0, date - Date.now());
  return 1000;
}

async function* iterateBody(body) {
  if (body && typeof body.getReader === 'function') {
    const reader = body.getReader();
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      if (value) yield value;
    }
    return;
  }
  if (body && typeof body[Symbol.asyncIterator] === 'function') {
    for await (const chunk of body) yield chunk;
    return;
  }
  if (typeof body === 'string') { yield new TextEncoder().encode(body); return; }
  if (body instanceof Uint8Array) { yield body; return; }
  throw new Error('openai-compat: response body is not iterable');
}

function* parseSseFrames(buffer) {
  let cursor = 0;
  while (true) {
    const sep = buffer.indexOf('\n\n', cursor);
    if (sep < 0) break;
    const frame = buffer.slice(cursor, sep);
    cursor = sep + 2;
    const dataLines = [];
    for (const line of frame.split('\n')) {
      if (line.startsWith('data:')) dataLines.push(line.slice(5).trim());
    }
    if (dataLines.length > 0) yield { data: dataLines.join('\n'), nextCursor: cursor };
    else yield { data: '', nextCursor: cursor };
  }
}

// Normalise a base URL: strip trailing slashes so we can append `/chat/completions`
// or `/models` without worrying about doubled slashes. Accepts the user's input
// verbatim — we don't try to fix scheme or path quirks beyond the slash.
export function normaliseBaseUrl(raw) {
  if (!raw) return '';
  let s = String(raw).trim();
  while (s.endsWith('/')) s = s.slice(0, -1);
  return s;
}

/**
 * Build a Provider object backed by an OpenAI-compatible HTTP endpoint.
 * The returned object matches the shape registry.mjs expects:
 *   { name, sendMessage(messages, opts) -> AsyncIterable<string> }
 *
 * @param {Object} cfg
 * @param {string} cfg.name           Display name used in PROVIDERS / picker.
 * @param {string} cfg.baseUrl        e.g. https://integrate.api.nvidia.com/v1
 * @param {string} [cfg.apiKey]       Closure default. Caller can still override via opts.apiKey.
 * @param {string} [cfg.defaultModel] Closure default model id.
 * @param {Object<string,string>} [cfg.headers] Extra headers (e.g. {"x-foo": "bar"}).
 */
export function makeOpenAICompatProvider(cfg) {
  const name = cfg.name;
  const baseUrl = normaliseBaseUrl(cfg.baseUrl);
  const closureKey = cfg.apiKey || '';
  const closureModel = cfg.defaultModel || '';
  const extraHeaders = cfg.headers || {};
  if (!name) throw new Error('makeOpenAICompatProvider: name is required');
  if (!baseUrl) throw new Error('makeOpenAICompatProvider: baseUrl is required');

  return {
    name,
    async *sendMessage(messages, opts = {}) {
      const apiKey = opts.apiKey || closureKey;
      const fetchFn = opts.fetch || globalThis.fetch;
      if (!fetchFn) throw new Error(`${name}: no fetch implementation available`);

      const model = opts.model || closureModel;
      if (!model) throw new Error(`${name}: missing model — set cfg.model or pass opts.model`);

      const apiMessages = [];
      const sys = opts.system || messages.find(m => m.role === 'system')?.content;
      if (sys) apiMessages.push({ role: 'system', content: String(sys) });
      for (const m of messages) {
        if (m.role === 'user' || m.role === 'assistant') {
          apiMessages.push({ role: m.role, content: String(m.content ?? '') });
        }
      }

      const body = {
        model,
        max_tokens: opts.maxTokens || DEFAULT_MAX_TOKENS,
        stream: true,
        messages: apiMessages,
      };
      if (Array.isArray(opts.tools) && opts.tools.length > 0) {
        body.tools = opts.tools;
        if (opts.toolChoice) body.tool_choice = opts.toolChoice;
      }
      if (typeof opts.onUsage === 'function') {
        body.stream_options = { include_usage: true };
      }

      const headers = {
        'content-type': 'application/json',
        ...extraHeaders,
      };
      if (apiKey) headers['authorization'] = `Bearer ${apiKey}`;

      if (opts.signal?.aborted) throw new AbortError('aborted before request');
      const url = `${baseUrl}/chat/completions`;
      const res = await fetchFn(url, {
        method: 'POST',
        headers,
        body: JSON.stringify(body),
        signal: opts.signal,
      });

      if (!res.ok) {
        const text = typeof res.text === 'function' ? await res.text() : '';
        if (res.status === 401 || res.status === 403) throw new InvalidApiKeyError(text || 'unauthorized');
        if (res.status === 429) throw new RateLimitError(parseRetryAfterMs(res.headers), text || '');
        throw new ApiError(res.status, text || '');
      }

      const decoder = new TextDecoder('utf-8', { fatal: false });
      let buffer = '';
      let usage = null;
      const toolCallsByIndex = new Map();
      const flushToolCall = (idx) => {
        const tc = toolCallsByIndex.get(idx);
        if (!tc || !tc.function?.name) return;
        toolCallsByIndex.delete(idx);
        if (typeof opts.onToolUse !== 'function') return;
        let input = {};
        try { input = tc.function.arguments ? JSON.parse(tc.function.arguments) : {}; }
        catch { /* malformed → empty + raw */ }
        try {
          opts.onToolUse({
            id: tc.id || null,
            name: tc.function.name,
            input,
            raw: tc.function.arguments || '',
          });
        } catch { /* never let a callback abort the stream */ }
      };
      for await (const chunk of iterateBody(res.body)) {
        if (opts.signal?.aborted) throw new AbortError('aborted mid-stream');
        buffer += typeof chunk === 'string' ? chunk : decoder.decode(chunk, { stream: true });
        let consumed = 0;
        for (const frame of parseSseFrames(buffer)) {
          consumed = frame.nextCursor;
          if (!frame.data) continue;
          if (frame.data === '[DONE]') {
            for (const idx of Array.from(toolCallsByIndex.keys())) flushToolCall(idx);
            if (usage && typeof opts.onUsage === 'function') {
              try { opts.onUsage(usage); } catch { /* swallow */ }
            }
            return;
          }
          try {
            const obj = JSON.parse(frame.data);
            if (obj?.usage && typeof obj.usage === 'object') {
              usage = {
                inputTokens: obj.usage.prompt_tokens ?? null,
                outputTokens: obj.usage.completion_tokens ?? null,
                totalTokens: obj.usage.total_tokens ?? null,
              };
            }
            const choice = obj?.choices?.[0];
            const delta = choice?.delta || {};
            if (delta.content) yield delta.content;
            if (Array.isArray(delta.tool_calls)) {
              for (const td of delta.tool_calls) {
                const idx = td.index ?? 0;
                const cur = toolCallsByIndex.get(idx) || { id: null, function: { name: '', arguments: '' } };
                if (td.id) cur.id = td.id;
                if (td.function?.name) cur.function.name = td.function.name;
                if (typeof td.function?.arguments === 'string') cur.function.arguments += td.function.arguments;
                toolCallsByIndex.set(idx, cur);
              }
            }
            if (choice?.finish_reason === 'tool_calls') {
              for (const idx of Array.from(toolCallsByIndex.keys())) flushToolCall(idx);
            }
          } catch {
            // Ignore malformed frames; keep scanning the rest of the buffer.
          }
        }
        if (consumed > 0) buffer = buffer.slice(consumed);
      }
      const tail = decoder.decode();
      if (tail) buffer += tail;
    },
  };
}

/**
 * Fetch the model catalogue from an OpenAI-compatible endpoint.
 * Returns an array of model id strings, sorted alphabetically. Throws
 * on transport errors so callers can surface the failure to the user.
 *
 * Endpoints we tested:
 *   - https://api.openai.com/v1/models                  → { data: [{id, ...}] }
 *   - https://integrate.api.nvidia.com/v1/models        → { data: [{id, ...}] }
 *   - https://openrouter.ai/api/v1/models               → { data: [{id, ...}] }
 *   - https://api.together.xyz/v1/models                → [{id, ...}] (bare list)
 *   - http://127.0.0.1:11434/v1/models    (Ollama)      → { data: [{id, ...}] }
 *   - http://localhost:1234/v1/models     (LM Studio)   → { data: [{id, ...}] }
 */
export async function fetchOpenAICompatModels({ baseUrl, apiKey, headers, fetch: fetchOverride, signal } = {}) {
  const fetchFn = fetchOverride || globalThis.fetch;
  if (!fetchFn) throw new Error('fetchOpenAICompatModels: no fetch implementation available');
  const url = `${normaliseBaseUrl(baseUrl)}/models`;
  const h = { 'accept': 'application/json', ...(headers || {}) };
  if (apiKey) h['authorization'] = `Bearer ${apiKey}`;
  const res = await fetchFn(url, { method: 'GET', headers: h, signal });
  if (!res.ok) {
    const body = typeof res.text === 'function' ? await res.text().catch(() => '') : '';
    if (res.status === 401 || res.status === 403) throw new InvalidApiKeyError(body || 'unauthorized');
    throw new ApiError(res.status, body || '');
  }
  const obj = typeof res.json === 'function' ? await res.json() : JSON.parse(typeof res.text === 'function' ? await res.text() : '{}');
  const list = Array.isArray(obj) ? obj : (Array.isArray(obj?.data) ? obj.data : []);
  const ids = [];
  for (const item of list) {
    if (typeof item === 'string') ids.push(item);
    else if (item && typeof item.id === 'string') ids.push(item.id);
    else if (item && typeof item.name === 'string') ids.push(item.name);
  }
  return Array.from(new Set(ids)).sort((a, b) => a.localeCompare(b));
}

export { InvalidApiKeyError, ApiError, AbortError, RateLimitError };
