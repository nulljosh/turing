# Turing Roadmap

## Ingested 2026-11-08
- [x] Cloudflare retires `@cf/meta/llama-3.2-3b-instruct` (worker.js:10,226; READER was moved up from the 1B for accuracy, so re-check answers on the new model) on Workers AI on 2026-11-20. Move to a replacement before then: Cloudflare suggests `@cf/google/gemma-4-26b-a4b-it` or `@cf/qwen/qwen3.8-27b` for small models, `@cf/deepseek-ai/deepseek-v4.1-flash-1017` or `@cf/zai-org/glm-5.3` for bigger ones. Changelog: https://developers.cloudflare.com/changelog/post/2026-11-05-planned-model-deprecations/ Done 2026-11-08: READER, PICKER and FACTS moved to `llama-3.3-70b-instruct-fp8-fast`. FACTS was on a model already gone from the catalog.
