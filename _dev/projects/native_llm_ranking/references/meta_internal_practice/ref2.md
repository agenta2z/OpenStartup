📎 Addendum: Additional Internal Meta Production Systems
Compiled from Agent 2's comprehensive internal search

Additional Key Production Systems Not in Main Report
LangRank — Direct LLM CTR Prediction
Post: https://fb.workplace.com/groups/1033540429995021/permalink/25985007054421680/

Adapts pre-trained LLMs for direct CTR prediction on production data

Converts structured ads data to text prompts; uses normalized P("YES") as CTR prediction

Key finding: Post-training small LLMs on ads data surpasses much larger non-post-trained LLMs

Performance scales with data quality, model size, in-context examples, and test-time compute

LLaTTE UM-XL — 13,000x Scale User Model
Post: https://fb.workplace.com/groups/1033540429995021/permalink/27030098649912510/

Largest ads recommendation model ever deployed at Meta

Extension of LLaTTE at extreme scale

COFFEE (CoFormer) — LLM-Style Multi-layer Sequence Model
Wiki: https://www.internalfb.com/wiki/COFFEE/general_model_workflow/

Impact: ~1.05% GAS since 24H2, additional 0.67% eGAS in 25H2

LLM-style multi-layer architecture specifically designed for ads

Heavyweight Inference (HWI) / Meta Galileo
Post: https://fb.workplace.com/groups/1033540429995021/permalink/25758740943714960/

LLM-scale inference for ads ranking — O(10 GFLOPs) per example, 35% MFU

Result: 4% increase in conversions on Instagram Feed, Stories, and Reels

Intelligent request routing matching model complexity to user context

Zen Architecture
Wiki: https://www.internalfb.com/wiki/AdsInfra/AI_HW_Codesign/models/building_blocks/zen/

Breaks through Wukong's scaling ceiling

+1.2% NE at 600× FLOPs, +2.2% at 1000× FLOPs

Rec LLM Service (RLS)
Post: https://fb.workplace.com/groups/926708381016660/permalink/2796577447363068/

MRS's unified LLM serving layer (vLLM-powered)

First realtime LLM inference on ranking service — Instagram's Online Relevance Model 3.0

Project PROMPT — Generative Recommendation for Marketplace
Post: https://fb.workplace.com/groups/1115642875273221/permalink/3396056260565193/

LLM-powered recommendation for Marketplace Feed

Key Code Repositories
Path	Description
fbcode/generative_recommenders/research/modeling/sequential/hstu.py	HSTU core model
fbcode/generative_recommenders/dlrm_v3/	DLRMv3 benchmark
fbcode/dper_lib/silvertorch/	RankFM 2.0 architecture
fbcode/minimal_viable_ai/models/main_feed_mtml/	HSTU feature extractors
Key Internal Events
LLMs for Recommendation Systems Forum (June 3, 2026): Meta's inaugural half-day technical summit

Recap: https://fb.workplace.com/groups/1033540429995021/permalink/28291524357103260/

LLM & Agents for RecSys Workshop @ WWW 2026: https://llmandagents4recsys.github.io/

Meta ML Forum 2026: LLM for recommendation posters

Key Workplace Groups for Tracking
Group	URL
Ads Ranking AI FYI	https://fb.workplace.com/groups/1033540429995021/
MRS FYI	https://fb.workplace.com/groups/228479108798071/
RecSys Reading Group	https://fb.workplace.com/groups/9662463790469974/
Ads Infra & Ranking FYI	https://fb.workplace.com/groups/527654686243695/
