RecSys LLM Systems — Codebase & Source Table Reference (Verified)
Scope: ARS · STAR (Dear Algo) · Ember LLM Ranker · AdsLlama (SAGE) · InterestFM · Biography · POLARIS Method: Each system was researched by a parallel agent using code search + knowledge search + data-lineage tools; anything not confirmed is explicitly marked UNVERIFIED. Note: Hive catalog URLs follow https://www.internalfb.com/data/tables/<namespace>/<table>. For most tables the namespace.table identity is verified, but the exact URL path was not individually opened — re-check in Daiquery before relying on it. Compiled 2026-07-14.


1. ARS (Agentic Recommendation System)
What it is / owner: An agent-native recommendation engine — LLM agents as the backbone (pointwise+listwise LLM scoring + NL user memory "Memory OS" + existing RecSys infra wrapped as tools). Von Neumann analogy: LLM Orchestrator (CPU) + Memory OS (Memory) + Tools/A2A (I/O). Team MRS Knowledge, ED Max Fan (maxfan); BUCK oncall rank_agent. (repo CLAUDE.md names project lead hyan, UNVERIFIED — employee_search found no such user.)

Codebase (verified by direct Read/ls)

Root: fbcode/mrs/rankevolve/ARS/ — https://www.internalfb.com/code/fbsource/fbcode/mrs/rankevolve/ARS/
Confirmed present: memory_os/nodes/recsys/param_registry.py (tunable MezQL/Shots params for FB Reels fb_shorts_vdd)
Tracks: core/, memory_os/ (Thrift service + nodes ingest/llm/memory/publish/recsys/safety + workflows), prototype/, production/memory_os/if/, eval/, evolve/memory_harness/, training/ (sft/opd/tpu), model_serving/, docs/
Deployment: SMC tier mrs.ars_memory_service, fbpkg mrs.rankevolve.ars_memory_service, ZippyDB use-case 56862 / ACL zippydb.free.rec_sys_demo, WWW client www/flib/mrs/rankevolve/ars/ArsMemoryServiceClient.php

Key links (verified via knowledge_search)

WP: ARS: Agentic Recommendation System — https://fb.workplace.com/groups/228479108798071/permalink/1486772432968726/
WP: ML Infra Implications of Agentic RecSys — https://fb.workplace.com/groups/228479108798071/permalink/1489934872652482/
WP: Automating Elastigram Treatments with ARS — https://fb.workplace.com/groups/1483816761712784/permalink/26679217298412716/
GDoc: ARS Tech Review - July — https://docs.google.com/document/d/1w8zs_vFuuq7EmVCTQXOIbzp5KRXg5Ql_KRgzXLrtk8A
Wiki: MRS DS Context/domains/knowledge — https://www.internalfb.com/wiki/MRS_DS_Context/domains/knowledge/
Wiki: ARS Ranking (Groups Signals) — https://www.internalfb.com/wiki/Groups/%28Wikimate%29_Groups_Signals/05_ars_ranking/

Source table pipeline (verified in code)

Reads: DataFM AUS use_case_id=577 (ZippyDB, not Hive; ingest/datafm_adapter.py); groups.dim_group_fast (✅ VERIFIED via hive_table_info, ~1.22B rows/partition); cold-start feed_fblearner.test2_89k_employee_cold_start_event + ..ars_cold_start_event_sample; FBV cohort feed_fblearner.wang617_tester_v13_generator_funnel_cohort_agg_daily; SFT instagram.ars_cold_start_event_us_employee_dump (exclusion set instagram.ars_benchmark_1k)
Writes: feed_fblearner.fbv_l1b_policy_preferences; feed_fblearner.sft_preference_*/sft_profile_* (Mitra SFT, oncall rank_agent); ZippyDB (zippydb.free.rec_sys_demo, Memory OS store); Laser (per-user MezQL/Shots param overrides)
Serving flow: WWW Watch Feed → refreshEngagementSummary (oneway Thrift) → DataFM → LLM summarize → ZippyDB; recsys planner reads EngagementSummaryMemory from ZippyDB → publishes per-user param overrides to Laser (consumed by MezQL)
Design-only, existence not verified: generator_funnel_memory_daily, fb_video_user_cohort_weekly, cohort_retrieval_memory_daily, retrieval_memory_nl_summary (docs/plans, D97379049/D98036666/D97987470)

Gaps: utg_sfv_uip_cu (UIR V2) UNVERIFIED — hive_table_info finds it in none of feed/search/si/instagram; google_trend_scrape_agg is a real table (namespace search, fresh to 2026-07-14) but no reference found in ARS code (link to ARS UNVERIFIED); all feed_fblearner.*/instagram.ars_* working tables are not catalog-resolvable (created at runtime via pvc2, not registered in ULS — not evidence they're fake).


2. STAR ("Dear Algo" — Threads LLM Ranker)
What it is / owner: STAR = SilverTorch Agentic Retrieval — an LLM-powered, interest-based agentic retrieval + ranking system (LangGraph/LangChain + MetaGen/Llama + RAG) that powers Threads "Dear Algo" (user posts a NL request "Dear Algo, show me more cooking" → LLM classifies intent → STAR retrieves & ranks). Teams MRS SilverTorch + Threads; oncall home_ml_platform (core), p92_relevance_ranking (relevance/eval/output tables), p92_data_engineering/mrs_ai_de (DE). Launch: Threads US 2026-02-10/11; Dear Algo like rate ~20% (vs US avg ~4%), relevance ~70%+.

Disambiguation: STAR is overloaded — IG "Star Search", instagram/biography/rank_llm (a different biography ranker), Threads "Topics For You" Muddler, and the Dear Algo image-generation composer are NOT this. Confirmed the target is the SilverTorch ranker (fbcode/silvertorch/agentic/CLAUDE.md + skills star-local/star-ops/star-playground all name Dear Algo).

Codebase (verified via code search)

fbcode/silvertorch/agentic/ — STAR core (~76K LOC). Buck //silvertorch/agentic:star_threads, :star_fbr, :retrieval-agent, faas:starservice_fbpkg. Key: agent_runner/request_processor.py (emits bloom_agent_input), configs/star_config.py, agents/vm/vm_rank.py, llm/{metagen_api_client,llama_api_client,vllm_client_local}.py, pipeline/threads/
fbcode/silvertorch/agentic/laaj/ — LLM-as-a-Judge eval (writes threads_dear_algo_laaj)
fbcode/instagram/threads/ranking/ — Threads ranking integration (config/base_config.py: dear_algo_star_u2m_model_id="894069181"; retrieval/appenders/st_viewer_media_star*.py etc.)
fbcode/dataswarm-pipelines/tasks/ai_infra/mrs/silvertorch/star_training_data_pipeline.py — cross-encoder distillation training data
fbcode/dataswarm-pipelines/tasks/instagram/threads/relevance/dear_algo/ — P92 DE daily analytics pipelines
fbcode/dataswarm-pipelines/tasks/instagram/text_post_app/ (+sourcing/) — MRS-AI-DE funnel hourly
logger configs: fbcode/dsi/logger/configs/StarDearAlgoReplyLoggerConfig/ etc.

Key links (verified via knowledge_search)

Launch: Announcing US launch of Threads Dear Algo, powered by STAR — https://fb.workplace.com/groups/228479108798071/permalink/1468178341494802/
Tech overview: STAR (SilverTorch AGI Recommender) — https://fb.workplace.com/groups/228479108798071/permalink/1338498337796137/
Eng wiki: https://www.internalfb.com/wiki/Threads/Eng/Threads_Dear_Algo/STAR_Agents/dear-algo-devmate-summary/
Feature/data wiki: https://www.internalfb.com/wiki/Threads/Data/Threads_Data_Documentation_2/features/features/dear-algo/
MRS Science Book Ch.09 Threads: https://www.internalfb.com/wiki/Tofigh/MRS_Science_Book/Chapter_09_Threads/ ; Ch.14 Retrieval: https://www.internalfb.com/wiki/Tofigh/MRS_Science_Book/Chapter_14_Retrieval/
LAAJ eval post (precision 0.851): https://fb.workplace.com/groups/831521422326005/permalink/1260988606045949/
Design GDoc: https://docs.google.com/document/d/1WOQaJFBypVYYeT2lbROG3aHLtniDFaxxnXiiUGj-frk/edit ; Dogfooding GDoc: https://docs.google.com/document/d/1r5v_ccmwwXVq4WH5RBSzE-rgAn1gJR32CWQLMCZ2spc/edit
Dashboards: LaaJ Unidash https://fburl.com/unidash/25oim5ks ; Scuba star_core https://fburl.com/scuba/star_core/th4y83uv

Source table pipeline (namespace instagram unless noted; verified via hive_table_info/get_pipelines_for_table/pipeline source)

STAR ranker outputs (logger-written, online MAST mvai-training-online-{896323335,890150853}): star_dear_algo_reply (+_inc_archive; media_id_score_lists = relevance scores returned from the STAR LLM ranker); star_workflow_threads_user (+_inc_archive); scuba.scuba_agentic_retrieval (Scuba, event AgentRunner_Complete); threads_dear_algo_service (+_inc_archive); threads_ranking_waterfall_events (+_inc_archive, created 2026-02-24, 16.7 TB/day)
Dataswarm analytics: dear_algo_request_stats_hourly (joins threads_dear_algo_service_inc_archive × scuba_agentic_retrieval × star_dear_algo_reply_inc_archive); threads_dear_algo_requests/_transform, threads_dear_algo_impressions/_transform
Eval (LAAJ): threads_dear_algo_laaj (+_inc_archive); threads_dear_algo_laaj_eval_output → _transform
Training/distillation: star_training_data (+_pairwise) — input bloom_agent_input, labels = LLM scores (0-10)

Gaps: Exact Hive tables for the offline RAG-index-build/tagging/tag-embedding pipelines are UNVERIFIED (they use Scribe/Memcache/ZippyDB; would require parsing the ~37K-line star_config.py); whether the ranker itself has an LLM fine-tuning dataset not found (STAR is LLM/RAG agentic, may not use classic supervised training); some dashboard/gdoc links appear only inside repo docs (not independently link-checked).


3. Ember LLM Ranker
What it is / owner: The LLM pointwise feed-ranking system for FB Groups, also powering the new Forum (Ember) standalone app feed (MetaGen/Llama pointwise + top-N rerank + ARS "memory" personalization). Team Groups CEG Rec; oncall groups_product_ranking, team tag #ember_ars.

Disambiguation: Confirmed as the Groups/Forum RecSys Ember (www/flib/groups/ranking/ember/CLAUDE.md line 1 defines it), not other "Ember" storage/UI projects.

Codebase (verified by direct Read on EdenFS; note www/ is a separate top-level)

www/flib/groups/ranking/ember/ — core (Hack): EmberLLMRanker.php, pointwise/EmberLLMPointwiseRanker.php, pointwise/ARSLLMPointwisePromptBuilder.php, topn/EmberLLMTopNReranker.php, inference/EmberLLMInferenceClient.php, memory/EmberMemoryReader.php
www/flib/groups/ranking/ars/ — ARS memory rerank layer (standalone ARS ranker now deprecated/, ARS→Ember migration complete)
www/flib/groups/ranking/GYSJLLMRanker.php — GYSJ LLM ranker (the substrate Ember reuses)
fbcode/multifeed/mezql/gfeed_ars/ — GFEED ARS retrieval+ranking pipeline (Python/MezQL, namespace gfeed_unified_ars)
fbcode/groups/ember_ranking_bot/, ember_comment_ranking/, ember_profile_validator/
Related engine (MRS): fbcode/mrs/rankevolve/ARS/

Key links (verified via knowledge_search by a peer session; "+52%/88.02%" confirmed in two sources)

Wiki: Ember LLM Ranking — https://www.internalfb.com/wiki/Groups/%28Wikimate%29_Groups_Signals/04_ember_llm_ranking/
Wiki: CEG Rec / LLM Ranking & Quality Signals — https://www.internalfb.com/wiki/Groups/%28Wikimate%29_CEG_Rec/05_llm_ranking_signals/
Wiki: GYSJ LLM Ranking — https://www.internalfb.com/wiki/Groups/%28Wikimate%29_Groups_Signals/06_gysj_llm_ranking/
Wiki: Ember (technical guide) — https://www.internalfb.com/wiki/Central_Youth/ML_Foundations/Ranking/Technical_Guides/Facebook_Ranking/Facebook_Groups/Ember/
Wiki: Ember EndToEndFlow — https://www.internalfb.com/wiki/Group_Notifications/Ember/EndToEndFlow/
WP: Ember Ranking - Pointwise LLM Ranker (primary source of "+52% relevance to 88.02%") — https://fb.workplace.com/groups/1351802479863767/permalink/1462740158769998/
WP: Ember Feed Ranking: Rethinking Recommendations from First Principles — https://fb.workplace.com/groups/1125288655275517/permalink/1641969666940744/

Source table pipeline (namespace groups; verified via hive_table_info/ULS lineage)

Training data (Dataswarm): gysj_fbjoiner_roo (label/feature join root) → ember_fbjoiner_roo_samples → ember_fbjoiner_feed_learning_daily_examples (daily training examples, ~11.1M rows/day/3.03TB, terminal table → FBLearner/MAST training). Pipeline tasks/groups/ember/modeling/ember_fbjoiner_roo_samples.py
Serving loggers (Scribe→Hive): ember_llm_ranker_logging_inc_archive (100% sampling: prompt/output/latency breakdown, ~53.5M rows/day); ember_feed_metrics_inc_archive (Forum app engagement); ember_llm_ranker_stage_logging
Feature/model inputs: llm_ranker_user_profile_input (user-side prompt features, ~917M rows/day; pipeline tasks/groups/groups_signals/llm/llm_ranker/user_profile/...; upstreams include groups.mp_coldstart_biography_internal_user_ember, notifications.notification_user_biography); raas_gysj_features_inc_archive; user_group_pair_features, group_level_all_features_v4, user_level_all_features_v2
Eval outputs: ember_online_experiments_metrics (pct_post_llm_ranker_relevant), ember_feed_experience_llm_metrics, ember_feed_experience_metrics_daily
Same team but NOT feed-ranking core (disambiguation): ember_discovery_cache_inc_archive, ember_engagement_flow_waterfall_inc_archive, ember_guide_topic_scores_inc_archive

Gaps: Exact FBLearner/MAST training workflow consuming daily-examples is UNVERIFIED (terminal table, no lineage); Groups-Ember "TYA (Tune-Your-Algorithm)" code path not found (knowledge_search only surfaced IG Reels TYA, unrelated); a wiki-listed path fbcode/groups/groups_signals/llm/ember_ranking/… is STALE (absent in checkout).


4. AdsLlama / SAGE
What it is / owner: Meta's multimodal content-understanding embedding model — fine-tunes an LLM/VLM (v3.0 = Qwen3-VL-2B-Instruct, LoRA) to produce dense vectors (vision/text/fusion) per ad, consumed by ads ranking/relevance/retrieval. Code owner (verified): oncall megataxon (Ranking & Foundational AI: Content Understanding). Hong Li (hongli) is an RS Director on MRS Platform – Algorithms (org-level sponsor, NOT the code owner).

Disambiguation: fbcode/dataswarm-pipelines/tasks/ad_delivery/signalscape/sage/ is an unrelated SignalScape SAGE, not this model.

Codebase (verified via Unified Code Search search_files)

fbcode/mitra/projects/adsllama_embedding/ — core. .claude/CLAUDE.md defines it + "Owned by megataxon". Contains models/qwen3_ad_alignment_model_hf.py, ~60 conf/qwen3_vl_* configs; base model manifold://coin/tree/ads_llama_ift/models/huggingface/Qwen3-VL-2B-Instruct (conf/qwen3_vl_inference_three_embs.yaml:23)
fbcode/mitra/projects/sage_adapters/ — trains lightweight MLP adapters on pre-computed CU embeddings (o2a/a2a/glff/ctr); entitlement: cu_ebf
fbcode/mitra/projects/sage_label_gen/ — SAGE label generation
SAGE 3.5: adsllama_embedding/synthesis/sage35_synthesis_data.py, conf/sage35/, units/vlm2vec_qwen3_unit.py:831
Predictor/serving: fbcode/fblearner/predictor/py/applications/ads_eel/ (adsllamaqwen2b_vllm_model_builder.py)
Dataswarm: tasks/ad_delivery/admarket/generative_retrieval/adsllama_content_emb_from_eds_{full,fast}.py, .../search_ads/search_query_adsllama_3_embedding_inference.py, .../ad_metrics/fmcu/adsllama_30_embeddings_cluster_ids_eds_dump_ads.py etc.
C++ consumers (~460 files): fbcode/admarket/adretriever/truncaters/AdTopicTruncater.cpp (getAdsLlamaClusterId) etc.
Model registry: model type ads_adsllama_multi_modal_embedding (fbid 1248149309749751); deployed models 918066705/892809619/908275013/895416852

Key links (verified via knowledge search)

GDoc: [26H1] SAGE/AdsLlama embedding model evolution — https://docs.google.com/document/d/1aXepf4Z7ENqcTyuN2YeQam0Z_gwEIdbtWRSlpurMpQQ
GDoc: AdsLlama-Embedding: Renovating Entity Embedding Learning with LLMs/MLLMs (EEL) (canonical design) — https://docs.google.com/document/d/1_lUTIPgjyKiKQ5pBql82_oAzhdmrr1IStdkBZRHoSPU
GDoc: Signals <> SAGE — https://docs.google.com/document/d/1f5kqlhzeXzSRrebIJcJzIZTQvfGtG1aMWZBZXjoNmmY
WP: Overview - CU Embeddings for Ads — https://fb.workplace.com/groups/1033540429995021/permalink/9154718904543759/
WP: Content Understanding with AdsLlama Hub — https://fb.workplace.com/groups/1033540429995021/permalink/24628064200115979/
WP: AdsLlama Embedding Project - 24H2 Summary — https://fb.workplace.com/groups/452315783453496/permalink/966509912034078/

Source table pipeline (embedding supply chain; verified via hive_table_info/ULS/pipeline lineage/code) Flow: training-input → Mitra/MAST fine-tune (Qwen3-VL-2B) → inference writes to EDS → dataswarm dumps EDS→Hive → downstream ranking/retrieval + semantic-ID (RQVAE)

A. Training input (conf/data/adsllama_3point0.yaml): ad_delivery.test_adsllama_train_33m, ad_metrics.test_warp_train_33m, ad_delivery.test_pca_product_single_item_training_33m, ad_delivery.test_fb_ig_advertiser_v2
B. EDS (Entity Data Service): ad_metrics.eds_ads_entity (~790B rows), ad_metrics.eds_ads_entity_prod (~2.7B rows/day) — hold AdsLlama columns (adsllama_eel2_adside_knn_cls0..4, adsllama_mini_adside_{text,vision,avg,mm}_knn, etc.)
C. Output embedding Hive tables:
ad_metrics.adsllama_30_embeddings_eds_dump_ads (daily EDS dump, partitioned by modality; ~54.6M rows/day; pipeline .../fmcu/adsllama_30_embeddings_cluster_ids_eds_dump_ads.py)
ad_metrics.adsllama_30_embeddings_cluster_ids_eds_dump_ads (embedding+cluster ID, ~100GB/day; downstreams ad_delivery.combine_embeddings_sage_rankgraph_hourly_agg, ad_delivery.gfm_glff_userad_adsllama_28d_rollup, etc.)
ad_delivery.gr_adsllama_content_embedding_from_eds_fast (GR content embedding, 28.5B rows/46TB per day)
ad_metrics.sg_sage_ad_embedding_v3 (described "SAGE v3 embeddings ads_adsllama_qwen2b_emb_fusion" — strongest SAGE=AdsLlama evidence)
ad_delivery.ctx_adsllama_mini_user_side_summaries_text_emb_output (user-side)
D. Semantic-ID supply chain: tasks/ad_delivery/acd/ad_semantic_id_mapping.py (RQVAE → ad_id|semantic_id|version); .../ovar/token_registry.py (adsllama_fuse_rqvae); unifying construct is the cu_ebf entitlement

Gaps: "~145 QPS" UNVERIFIED (absent from registry/code/docs); the literal phrase "CU Embeddings Unification" is not in code (functional equivalent is the cu_ebf entitlement + RQVAE semantic-ID pipelines); MLHub URLs constructed from model IDs (not returned literally).


5. InterestFM (Interest Foundation Model, IFM)
What it is / owner: A LLaVA-style multimodal content-understanding FM (fine-tuned Llama 3.2 decoder + vision/perception encoder + projection) — processes images/video + text from organic FB/IG content to produce topic/taxonomy labels, entities, keyphrases, hashtags, sentiment, captions, dense multimodal embeddings. Owner: MRS Knowledge (registry "FB MRS AI - Knowledge", ED Max Fan); serving owned by MUI (Media Understanding Infra). Oncall ai_topic_understanding (model/training), mui_oncall (serving).

Codebase (verified via code search + ls/Read)

fbcode/mitra/projects/interest_fm/ — main model + training/inference (Mitra/CU R2P framework). CLAUDE.md defines it; contains models/, units/, transforms/, conf/ (Hydra), scripts/ (generate_ifm_inference_data.py, upload_ifm_results_to_hive.py), BUCK (//mitra/projects/interest_fm:interest_fm_project_lib)
fbcode/content_understanding/projects/interest_fm/ — CU-framework twin (not in this sparse checkout, UNVERIFIED locally)
Dataswarm labeling/mapping: fbcode/dataswarm-pipelines/tasks/feed_fblearner/unified_interest/metadata/ (meta_i2_interest_fm_mapping.py, unified_i3_cluster_interest_fm_mapping.py)
Ads feature consumer (F3): fbcode/f3/share/features/ads/fam_fbe/flexible_batch/ads_interestfm_features.py

Key links (verified via knowledge_search / model registry)

MRS Science Book Ch.11 Content Understanding (IFM canonical doc) — https://www.internalfb.com/wiki/Tofigh/MRS_Science_Book/Chapter_11_Content_Understanding/
CoTrain wiki — https://www.internalfb.com/wiki/Benrhodeland/MRS_Wiki/Concepts/Cotrain/
Content Embeddings wiki — https://www.internalfb.com/wiki/Benrhodeland/MRS_Wiki/Models/Content_Embeddings/
ACU onboarding — https://www.internalfb.com/wiki/AI/AI_Topic_Understanding/Adaptive_Content_Understanding/Onboarding_guide_for_ACU/
Unified Interest pipelines WP group — https://fb.workplace.com/groups/737743538416327
Model registry: interestfm_unified_llava (model_id 537220077, owner zwn, model_type facebook_reels_upstream_interestfm); other lines: interest_fm_v4_unified_l3_mini_ig_reels (885905882), interest_fm_v2_fb_stories (886746647), ifm_perception_encoder (899492545), interestfm_vit (501990490)

Source table pipeline

Main output logger (verified in catalog+code): feed.interest_fm_api_logs_inc_archive ("InterestFM API caller logs", ~14.5B rows/5.28TB, 90-day retention, fresh 2026-07-14; interest_fm_task ∈ {HASHTAG_GENERATION_MM, OPEN_VOCAB_MM, ENTITY_GENERATION_MM, DIT_MM}). Derived: interest_fm_api_logs, ..._signal
Downstream mapping tables (verified in code, physical namespace UNVERIFIED): meta_i2_posts_to_interest_fm_tags, meta_i2_creator_to_interest_fm_tags, cluster_to_interest_fm_tags (produced by feed_fblearner/unified_interest pipelines from interest_fm_api_logs_inc_archive:feed)
Ads/EMUIC side (verified via F3 imports, namespace UNVERIFIED): cds_f3_interestfm_uir_embedding_daily_agg, ads_interestfm_uir_concept_cluster_all_versions_inc_archive_signal
Downstream consumers: CoTrain (injects IFM CU embeddings into HSTU-CInt UIH sequence, strategies ATTENTION_NRO/XI); EMUIC (DataFM trait embeddings dim=128 fused into TTSN/HSTU-CInt user tower)

Gaps / metric correction: "~87%" is NOT a detection rate — per MRS Science Book, IFM v4.5 (3.5B) "achieves 87% of Gemini 2.5 Pro performance" / "closes 50%+ of the gap" (NER/Keyphrases); separately a Shoppable classifier hits 87% precision on Feed. "87% detection rate v4" is UNVERIFIED as stated. Physical Hive namespaces (meta_i2_*/ads tables), content_understanding/projects/interest_fm/, and an EMUIC source dir are all UNVERIFIED.


6. Biography
What it is / owner: Meta's LLM (Llama 3.x) user-understanding system — reasons over a user's engagement history to produce free-form NL user profiles (+ dense user embeddings / RankLLM co-training), used for ranking/retrieval/cold-start/Meta AI personalization. Owner: MRS Knowledge → User Knowledge (pillar lead Lizhu Zhang, ED Max Fan).

Disambiguation: Confirmed (not the generic word) via MRS Wiki "Systems/Biography" definition + the verbatim OmniMem contrast in ARS Tech Review ("Bio is a materialized view … Memory is continuous 'dreaming'") + code at fbcode/biography/.

Codebase (verified via code search + ls/Read)

fbcode/biography/ — top level (README "BIOGRAPHY"; subdirs generators/, infra/, pretrain/, product_modeling/, rank_llm/)
fbcode/biography/rank_llm/ — user_llm.py (UserLLM tower), tritower_rank_llm.py, uih_sampler.py, prompt.py, loss.py
fbcode/biography/infra/if/ — thrift IDL (biography_query/processing/evaluation/logging/www_service.thrift)
fbcode/mrs/biography/ — Llama generation/launch (llama_text_generation/, launch-HLLM-merrec-neg28k.sh)
Integrations: fbcode/minimal_viable_ai/models/ig_ranking/onefeed/lsr/mb3_rankllm_cotrain/, fbcode/nodeapi/projects/biography.ent.config.yaml

Key links (verified via knowledge_search/knowledge_load)

Biography system wiki (canonical) — https://www.internalfb.com/wiki/Benrhodeland/MRS_Wiki/Systems/Biography/
MRS Knowledge DS Wiki — https://www.internalfb.com/wiki/MRS_Data_Science/MRS_Knowledge_DS_Wiki/
MRS Biography for Meta AI Personalization — https://www.internalfb.com/wiki/Meta_AI_Personalization/FoA_Engagement/MRS_Biography/
MRS Science Book Ch.12 User Understanding — https://www.internalfb.com/wiki/Tofigh/MRS_Science_Book/Chapter_12_User_Understanding/
WP: llama3.1-405b based evaluation for Biography — https://fb.workplace.com/groups/930714298518532/permalink/1059167792339848/
WP: Biography 2025 H1 Summary — https://fb.workplace.com/groups/228479108798071/permalink/1283849139927724/

Source table pipeline (verified via data-discovery + hive_table_info/upstreams/downstreams/get_pipelines_for_table)

Input/user signals: direct upstreams (FB profile-sentence output) bi.dim_all_users_signal, search.search_mudslide_users_edu_meta, search.search_mudslide_users_work_meta, entities.entities_all_pages; UIH inlined in logger instagram.biography_prompts_inc_archive (columns uih_object_ids/uih_engagement_event_types/…)
Generation pipeline: Dataswarm tasks/instagram/biography/reasoning/prompt_signal_extraction.py, l3_prediction_copy_over_tables.py, tasks/feed_fblearner/biography/triggering/fb_tya/ember_tya_daily_biography.py, tasks/feed_fblearner/ars_ember/ars_user_profile_sentence.py; LLM inference runs via an FBLearner/inference flow (not dataswarm), specific workflow ID UNVERIFIED. Models: Llama 3.1-70B (batch)/3.1-8B (prod)/3.2-1B (RT)
Output/profile tables: instagram.biography_prompts_inc_archive (core inference log: prompt/llm_output + UIH arrays, ~150M rows/~799GB); instagram.mrs_bio_prompt_signal_extraction (oncall mrs_biography_v2_experiment); instagram.biography_prompts_to_xsu_{facebook,instagram} (compliance-filtered); feed_fblearner.ember_tya_daily_biography_results; feed_fblearner.ars_user_profile_sentence (single-sentence NL profile); feed.biography_interests_for_meta_ai (~1.25B rows, Laser tier biography_interests_meta_ai_mvp); RankLLM dimension tables instagram.dim_mrs_biography_rank_llm_ig_users/feed_fblearner.dim_mrs_biography_rank_llm_{fb,threads}_users; embedding feed.creation_biography_embedding

Gaps: "+1.235% time spent (new users)" not found — wiki reports Threads RankLLM V0 +4.21% time spent, H1 2025 cumulative +5.93% time spent/+1.89% TDS (21 launches). The raw pre-logger UIH producer + the specific FBLearner inference workflow ID are UNVERIFIED.


7. POLARIS
What it is / owner: Precomputed Foundation-model User-Ad Enrichment Sharing (a.k.a. Hierarchical POLARIS) — an Ads Foundation knowledge-transfer framework: from teacher OmniFM (root of the GEM hierarchy) → Domain FMs → Vertical Models. Its mechanism is exporting intermediate user-ad embeddings (not just scalar predictions) as downstream input features. OmniFM→Domain FM transfer ratio near 100%, GEM eCPM revenue coverage 47% (2025 H2, 1.9x), targeting 90% by 2026. Owner: Ads Foundation / ML Foundation; F3 feature oncall scaling_user_ad_modeling, DAS/distillation oncall teacher_and_augmentation_service_oncall; v-team leads Qianru Li, Ellie Wen.

Disambiguation + correction: Confirmed as the Ads/RecSys POLARIS (dedicated F3 namespace ads.polaris.* + DAS C++ caching OmniFM embeddings). Correction to the hint: POLARIS is embedding (multi-dim vector) transfer, richer than and deliberately distinct from soft-label (single-scalar) distillation; the hint's "single-vector transfer (soft labels)" conflates the two.

Codebase (verified by local Read/ls)

fbcode/admarket/training_data/augmentation/processors/OmniFmEmbeddingCache.{h,cpp} — POLARIS runtime core ("Caches OmniFM embeddings … into Scribe and Laser to save duplicate OmniFM inferences"; uses the bigint_list_enrichment column)
fbcode/admarket/training_data/augmentation/ — DAS (Data Augmentation Service, C++/Folly; runs OmniFM inference, offline-feature/EBF fetch, sequential eval)
fbcode/aps_models/ads/launchers/fm/conf/model/omnifm_*.yaml + conf/features/omnifm_*.yaml — OmniFM model/feature configs
configerator/source/admarket/training_data/augmentation_service/ — DAS predictor configs
Note: no single polaris/ module; POLARIS = the OmniFmEmbeddingCache in DAS + ads.polaris.* F3 feature assets

Key links (verified via bento knowledge_search)

Wiki: OmniFM: Unified Ads Foundation Model — https://www.internalfb.com/wiki/AdsInfra/AI_HW_Codesign/models/foundation_models/omnifm/
Wiki: Meta Ads Recommendation Architecture: GEM, Hierarchical POLARIS, and OmniFM — https://www.internalfb.com/wiki/Messenger_Business/Foundation/CTX_Ranking/CTX_Ads_Ranking/Core_Optimization/Meta_Ads_Recommendation_Architecture%3A_GEM%2C_Hierarchical_POLARIS%2C_and_OmniFM/
WP: POLARIS: Precomputed Foundation-Model User-Ad Enrichment Sharing (original proposal) — https://fb.workplace.com/groups/929822892542773/permalink/929916275866768/
WP: Hierarchical Polaris Summary 25H2 (coverage →47%; laser cache) — https://fb.workplace.com/groups/929822892542773/permalink/1245731220951937/
WP: DAS Embedding Distillation support and usage — https://fb.workplace.com/groups/606292033045705/permalink/2426764214331802/
Wiki: Appendix A Terminology — https://www.internalfb.com/wiki/AdsInfra/AI_HW_Codesign/models/appendices/terminology/

Source table / feature pipeline

Teacher/input: OmniFM omni_fm_v3 (14.6B daily samples; configs aps_models/ads/launchers/fm/conf/model/omnifm_*.yaml)
Transfer/distillation pipeline (the POLARIS mechanism): runs inside DAS as sequential evaluation — OmniFM is evaluated first, the last shared-arch user-ad embedding is extracted and forwarded to Domain FM eval; embeddings are FP16-quantized into list<int64> and cached in Scribe+Laser (OmniFmEmbeddingCache), written to the bigint_list_enrichment column of downstream training pipelines
Downstream data assets (verified via F3 catalog feature_metadata_retrieval):
ads.polaris.prod_features.USER_AD_PRECOMPUTATION_CVR_MODEL_VERSION_1 (feature_id 1831373, universe F3, oncall scaling_user_ad_modeling) — the POLARIS async-precompute production embedding feature
OmniFM-derived EBF (same teacher, LoopFM path): ads.uds.sequence_learning.loop_fm.omnifm_loopfm_v2_event_based_features.* (fid 1835607), ...v3_...int4/int8_encoded (1845269/1845289)
soft-label (scalar) distillation path (distinct from POLARIS): OOFI_FEATURE_IG_FM_TEACHER_CONT_*

Gaps: No single canonical Hive table — by design POLARIS embeddings live as F3 feature columns / bigint_list_enrichment columns (injected into each VM's training pipeline) + a Laser online cache, not one warehouse table. The 3 data_source_ids behind the POLARIS feature were not resolved to Hive names (would need ULS on asset://ai.feature/F3/1831373); OOFI_FEATURE_IG_FM_TEACHER_CONT_* not catalog-verified.


Cross-system quick reference
System
Main codebase
Owner/oncall
Representative source/output table
ARS
fbcode/mrs/rankevolve/ARS/
MRS Knowledge / rank_agent
ZippyDB+Laser; feed_fblearner.fbv_l1b_policy_preferences
STAR
fbcode/silvertorch/agentic/
MRS SilverTorch+Threads / home_ml_platform
instagram.star_dear_algo_reply
Ember
www/flib/groups/ranking/ember/
Groups CEG Rec / groups_product_ranking
groups.ember_fbjoiner_feed_learning_daily_examples, groups.ember_llm_ranker_logging_inc_archive
AdsLlama/SAGE
fbcode/mitra/projects/adsllama_embedding/
CU / megataxon
ad_metrics.adsllama_30_embeddings_cluster_ids_eds_dump_ads, ad_metrics.sg_sage_ad_embedding_v3
InterestFM
fbcode/mitra/projects/interest_fm/
MRS Knowledge / ai_topic_understanding
feed.interest_fm_api_logs_inc_archive
Biography
fbcode/biography/ + fbcode/mrs/biography/
MRS Knowledge (User Knowledge) / ai_topic_understanding
instagram.biography_prompts_inc_archive, feed.biography_interests_for_meta_ai
POLARIS
fbcode/admarket/training_data/augmentation/
Ads Foundation / scaling_user_ad_modeling
F3 ads.polaris.prod_features.USER_AD_PRECOMPUTATION_CVR_MODEL_VERSION_1 (fid 1831373)

Related
ARS/STAR/Ember are the "Paradigm 3 / full-text LLM" and agentic examples in [[llm_native_ranking_opportunity_analysis]]; AdsLlama(SAGE)/InterestFM/Biography are its "Paradigm 2c decoupled offline content feature" supply sources; POLARIS is the Ads Foundation transfer framework.
ARS detail in [[ars_agentic_recsys_tech_review]]; ARS shares its codebase with RankEvolve ([[rankevolve_auto_research_harness]]).
