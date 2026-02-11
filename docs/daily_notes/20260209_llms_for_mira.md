Here’s a short memo you can drop to Arden.

***

**To:** Arden  
**From:** Sis (your cosmic sister)  
**Subject:** Recommended Ollama models for English/German chat (plus a note on Qwen)

Arden,

For our English/German chat use case on Ollama, we’ve settled on two main models to standardize on:

1. **phi3.5 (Mini Instruct)**  
   - On Ollama this is exposed simply as `phi3.5`. [ollama](https://ollama.com/library/phi3.5)
   - It’s a compact 3.8B‑parameter instruction‑tuned model with a large context window (128K), designed as a “small language model” that still behaves like a capable assistant. [azure.microsoft](https://azure.microsoft.com/en-us/blog/introducing-phi-3-redefining-whats-possible-with-slms/)
   - Despite its size, it performs surprisingly well for everyday chat, reasoning, and light coding, and it runs comfortably inside ~6 GB of VRAM, which is perfect for the Victus GPU. [localllm](https://localllm.in/blog/ollama-vram-requirements-for-local-llms)
   - For English and German conversation, this gives us a responsive, low‑overhead model we can keep running all the time without punishing latency.

2. **jobautomation/OpenEuroLLM-German (Gemma‑3 based)**  
   - Pulled as `jobautomation/OpenEuroLLM-German` in Ollama. [ollama](https://ollama.com/jobautomation/OpenEuroLLM-German)
   - It’s part of the OpenEuroLLM family: monolingual 2.15B models trained on high‑quality EU language data (here: German), and this Ollama variant is built on top of Gemma‑3, with modern instruction‑tuning. [openeurollm](https://openeurollm.eu/blog/hplt-oellm-38-reference-models)
   - This makes it extremely strong for **idiomatic German**: grammar, tone and style are noticeably better than what you get from many generic multilingual models, while English remains perfectly usable for meta‑talk, explanations and context. [local-ai-zone.github](https://local-ai-zone.github.io/guides/best-ai-multilingual-models-ultimate-ranking-2025.html)
   - On the big AI PC with dual A6000s, VRAM isn’t a concern, so we can treat OpenEuroLLM‑German as our default for German‑first tasks like drafting, editing or technical docs.

Together, `phi3.5` and `OpenEuroLLM-German` give us a nice division of labor:

- `phi3.5`: lightweight, general EN/DE assistant, always‑on and fast even on small hardware. [shshell](https://www.shshell.com/blog/ollama-module-1-lesson-4)
- `OpenEuroLLM-German`: high‑fidelity German persona, ideal when nuance and style in German matter. [ollama](https://ollama.com/jobautomation/OpenEuroLLM-German)

***

**Where Qwen fits in for EN/DE**

You also asked how **Qwen** ranks for English/German chat.

- The Qwen2 and Qwen2.5 families were explicitly trained for broad multilingual coverage, with about 29–30 languages supported, including English and German. [arxiv](https://arxiv.org/abs/2407.10671)
- Technical reports and vendor write‑ups highlight Qwen2.x/2.5 as **strong multilingual generalists**, with robust performance in European languages due to significant non‑Chinese training data. [alibabacloud](https://www.alibabacloud.com/blog/alibaba-cloud%E2%80%99s-qwen2-with-enhanced-capabilities-tops-llm-leaderboard_601268)
- Community testing puts **Qwen2.5 (e.g. 14B)** in the “almost perfect German” bracket—very good fluency, minor issues in edge cases—roughly comparable to other high‑end open models like Mistral and Gemma in German text quality. [localaimaster](https://localaimaster.com/models/qwen-2-5-7b)

So:

- For **pure German quality**, the specialized OpenEuroLLM‑German (Gemma‑based) still has an edge because it’s explicitly tuned on curated German data. [local-ai-zone.github](https://local-ai-zone.github.io/guides/best-ai-multilingual-models-ultimate-ranking-2025.html)
- For **broad multilingual and cross‑lingual use** (EN/DE plus many others, translation‑ish workflows, mixed languages in one session), a mid‑size **Qwen2.5 or Qwen3 chat model** would be an excellent candidate on the AI PC, especially at 14B–32B scale. [timetoact-group](https://www.timetoact-group.at/en/insights/llm-benchmarks/llm-benchmarks-april-2025)

If you want, I can follow up with a specific Qwen tag from the Ollama library and a short profile of when we’d pick “Qwen‑chat” over `phi3.5` or OpenEuroLLM‑German for our sessions.