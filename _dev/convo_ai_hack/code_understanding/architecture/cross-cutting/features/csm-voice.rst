.. _feature-csm-voice:

==================================================================
CSM Voice — Voice-mode customer support via Twilio + OpenAI
==================================================================

:Verification date: 2026-05-02
:Source commit: ``9151ac1341583a0a1ba81d5742f904ff2c43d62b``
:Footprint: ~1,200 LoC across CSM + platform audio + REST WebSocket layer
:Triage score: **21/25 — explicit user surface; high strategic importance**
:Modules: ``product/csm/csm-{api,impl}/`` + ``platform/service/service-{api,impl}/audio/``

.. contents:: On this page
   :local:
   :depth: 2

What CSM Voice IS (in one paragraph)
========================================

CSM Voice is the **voice-mode AI agent for Customer Support Management**
— a real-time speech pipeline where a customer **calls a phone number**,
the call is routed through **Twilio Conversation Relay** as a WebSocket
connection to the convoai backend, the user's spoken words are
transcribed by Twilio's STT and dispatched to the **standard Rovo agent
execution pipeline** (same as text chat), the agent's text response is
synthesized to speech by **OpenAI Text-to-Speech** (with 6 voices
available: alloy/echo/fable/onyx/nova/shimmer), and played back to the
caller. **Voice callers are synthetic users** identified by Twilio's
call SID, not Atlassian accounts. Phone-number-to-agent mapping is
configured via **Statsig dynamic config** (``csm_voice_ai_config``).
The pipeline supports silence detection, language switching, DTMF
input, interruption handling — and notably **does NOT have visible
human-handoff** (callers exit via the call-end message).

Anatomy — where the code lives
=================================

**4 distinct locations** spanning CSM and platform tiers:

.. list-table::
   :header-rows: 1
   :widths: 36 12 14 38

   * - Location
     - LoC
     - Files
     - Role
   * - **csm-impl/.../service/voice/**
     - ~1,019
     - 7
     - **Main service** — session manager, agent resolver, STT-to-agent dispatch, TTS dispatch
   * - **csm-impl/.../rest/voice/**
     - moderate
     - ~3
     - **REST/WebSocket entry** — WebSocket handler, config, Twilio request validator
   * - **csm-api/.../api/voice/**
     - 141
     - 1
     - **DTOs** — Twilio Conversation Relay message envelope shapes
   * - **platform/service/service-api/.../audio/**
     - ~62
     - 4
     - TTS/STT contracts (interfaces)
   * - **platform/service/service-impl/.../audio/**
     - moderate
     - ~2
     - TTS/STT implementations (OpenAI integration)

The 4 main service files (csm-impl/.../service/voice/)
=========================================================

.. list-table::
   :header-rows: 1
   :widths: 32 12 56

   * - File
     - LoC
     - Role
   * - ``VoiceAiService.kt``
     - **846**
     - **The main service.** WebSocket session manager, message dispatch (setup/prompt/dtmf/interrupt/info/error), AI execution orchestration, TTS output streaming
   * - ``VoiceMessage.kt`` (api)
     - 141
     - Twilio Conversation Relay message DTOs (sealed class)
   * - ``VoiceAgentResolver.kt``
     - 103
     - Phone-number → (agentId, cloudId) routing via Statsig dynamic config
   * - ``VoiceAIConfigProvider.kt``
     - moderate
     - Pulls per-tenant voice config from Statsig dynamic config
   * - ``VoiceAIConfig.kt``
     - 29
     - Data classes — phone-agent mappings, voice config knobs
   * - ``VoiceCallerUser.kt``
     - 41
     - **Synthetic user identity** — caller has no Atlassian account; ``accountId = "voice:$callSid"``
   * - ``VoiceTextNormaliser.kt``
     - moderate
     - Normalize text for TTS (e.g., expand abbreviations, fix pronunciation)
   * - ``SilenceHandler.kt``
     - moderate
     - Detects caller silence; emits ``SetSilenceDetection`` outgoing message

The Twilio Conversation Relay protocol
==========================================

The system implements **Twilio's Conversation Relay** WebSocket protocol:

**Incoming message types** (caller → backend), defined in ``VoiceMessage.kt``:

.. list-table::
   :header-rows: 1
   :widths: 24 76

   * - Type
     - Meaning
   * - ``Setup``
     - Initial setup with ``callSid`` and ``customParameters`` (called once at connection)
   * - ``Prompt``
     - Caller spoke; STT-transcribed text in ``voicePrompt`` field; ``lang`` field for language
   * - ``Dtmf``
     - Caller pressed phone key (touch-tone)
   * - ``Interrupt``
     - Caller interrupted agent's speech mid-utterance; carries ``utteranceUntilInterrupt``
   * - ``Info``
     - Informational message from Twilio
   * - ``Error``
     - Error from Twilio side

**Outgoing message types** (backend → caller), defined in same file:

.. list-table::
   :header-rows: 1
   :widths: 24 76

   * - Type
     - Meaning
   * - ``Text``
     - Text for Twilio to speak to caller (Twilio-side TTS)
   * - ``Play``
     - Pre-synthesized audio to play (likely from OpenAI TTS)
   * - ``SendDigits``
     - Dial DTMF digits (e.g., navigate IVR)
   * - ``Language``
     - Switch caller's language
   * - ``End``
     - Terminate call
   * - ``SetSilenceDetection``
     - Configure silence detection thresholds

This is **standard Twilio Conversation Relay protocol** — a WebSocket
specification that abstracts phone-line integration. The convoai
backend doesn't directly handle telephony; Twilio does the SIP /
PSTN side.

The OpenAI TTS integration
=============================

**TTS provider**: OpenAI (verified in ``OpenAITextToSpeechProvider.kt``)

**TTS request contract** (``TextToSpeechRequest.kt``, 43 LoC):

.. list-table::
   :header-rows: 1
   :widths: 20 20 60

   * - Field
     - Type
     - Notes
   * - ``model``
     - ``AudioModel``
     - OpenAI audio model (likely TTS-1 or TTS-1-HD)
   * - ``text``
     - String
     - Text to synthesize
   * - ``voice``
     - ``OpenAIVoice``
     - **6 options**: alloy, echo, fable, onyx, nova, shimmer
   * - ``responseFormat``
     - ``OpenAIResponseFormat``
     - **6 formats**: mp3, opus, aac, flac, wav, pcm
   * - ``speed``
     - Double (default 1.0)
     - Speech speed (0.25-4.0 typically)

**STT contract** (``SpeechToTextRequest.kt``, 8 LoC) is minimal —
suggests STT is **NOT done by convoai backend** but by Twilio's side
(verified by ``Prompt.voicePrompt`` already containing transcribed
text). The convoai backend may use OpenAI STT for non-Twilio voice
paths (e.g., the rovo-impl voiceMessage REST endpoint).

End-to-end flow — voice call lifecycle
==========================================

1. **Caller dials** the customer-support phone number
2. **Twilio answers** the PSTN call, opens a **WebSocket** to convoai backend
3. **WebSocket connection** lands on ``VoiceAiWebSocketHandler.kt`` in csm-impl/.../rest/voice/
4. **TwilioRequestValidationInterceptor** validates the request signature (HMAC against Twilio account secret)
5. **VoiceAiService.handleSession()** starts:

   a. Awaits ``Setup`` message; extracts ``callSid``, ``customParameters``
   b. Creates ``VoiceCallerUser`` (synthetic user, accountId = ``voice:$callSid``)
   c. Calls ``VoiceAgentResolver.resolveAgent(phoneNumber)`` to look up:
      * Statsig dynamic config ``csm_voice_ai_config``
      * Returns ``(agentId, cloudId)`` for this phone number
   d. Initializes voice session state

6. **Caller speaks**: Twilio's STT transcribes; sends ``Prompt`` WebSocket message with ``voicePrompt`` text
7. **VoiceAiService** dispatches:

   a. Constructs a ``RovoChatService`` request (same as text chat) with:
      * The transcribed prompt
      * ``VoiceCallerUser`` as user identity
      * Resolved (agentId, cloudId)
   b. Invokes the **standard agent execution pipeline** — same orchestrator (Marathon/SAIN) as text chat
   c. Receives streaming response from agent

8. **Each text chunk** from agent → ``VoiceTextNormaliser`` → ``OpenAITextToSpeechProvider`` (synthesize as audio) → emit ``Play`` outgoing message
9. **Twilio** plays audio to caller
10. **Caller interrupts** → ``Interrupt`` message arrives → ``VoiceAiService`` cancels in-flight TTS, processes new prompt
11. **Silence detected** → ``SilenceHandler`` may emit ``SetSilenceDetection`` to adjust thresholds, or terminate
12. **Caller hangs up** OR backend emits ``End`` → WebSocket closes → cleanup

Sequence diagram
==================

.. mermaid::

   sequenceDiagram
       autonumber
       participant Caller
       participant T as Twilio<br/>(PSTN bridge)
       participant WS as VoiceAiWebSocket<br/>Handler
       participant Sec as TwilioRequest<br/>ValidationInterceptor
       participant Svc as VoiceAiService<br/>(846 LoC)
       participant Res as VoiceAgent<br/>Resolver
       participant Statsig as Statsig<br/>(csm_voice_ai_config)
       participant Chat as RovoChatService
       participant Orch as Marathon/SAIN<br/>Orchestrator
       participant Norm as Voice<br/>TextNormaliser
       participant TTS as OpenAI TTS

       Caller->>T: dial 1-800-XXX-XXXX
       T->>WS: open WebSocket
       WS->>Sec: validate signature
       Sec-->>WS: PASS
       WS->>Svc: handleSession(ws)

       T->>Svc: Setup(callSid, customParameters)
       Svc->>Svc: create VoiceCallerUser(callSid)
       Svc->>Res: resolveAgent(phoneNumber)
       Res->>Statsig: getDynamicConfig("csm_voice_ai_config")
       Statsig-->>Res: PhoneAgentMappingConfig list
       Res-->>Svc: (agentId, cloudId)

       loop conversation
           Caller-->>T: speak
           T-->>Svc: Prompt(voicePrompt="hello")
           Svc->>Chat: createMessage(voicePrompt, VoiceCallerUser, agentId)
           Chat->>Orch: orchestrate(...)

           loop streaming response
               Orch-->>Chat: AnswerPart("Hi there")
               Chat-->>Svc: AnswerPart
               Svc->>Norm: normalize("Hi there")
               Norm-->>Svc: "Hi there." (with proper TTS hints)
               Svc->>TTS: synthesize(text, voice=alloy, speed=1.0)
               TTS-->>Svc: audio bytes
               Svc->>T: Play(audio)
               T->>Caller: play audio
           end

           opt caller interrupts
               Caller-->>T: speak over agent
               T-->>Svc: Interrupt(utteranceUntilInterrupt)
               Svc->>Svc: cancel in-flight TTS
           end
       end

       Caller->>T: hang up
       T->>Svc: WebSocket close
       Svc->>Svc: cleanup session

External system fan-out
==========================

.. list-table::
   :header-rows: 1
   :widths: 24 28 48

   * - System
     - How
     - Used for
   * - **Twilio Conversation Relay**
     - WebSocket (PSTN bridge)
     - Phone call ingress + STT + outgoing audio playback
   * - **OpenAI TTS**
     - HTTP call per text chunk
     - Speech synthesis (6 voices)
   * - **Statsig dynamic config**
     - ``csm_voice_ai_config``
     - Phone-number → agent routing
   * - **RovoChatService**
     - same code path as text chat
     - Standard agent execution
   * - **Marathon / SAIN orchestrators**
     - via RovoChatService
     - Actual AI logic
   * - **AI Gateway**
     - via orchestrator
     - LLM inference

Smells and concerns
=====================

.. list-table::
   :header-rows: 1
   :widths: 6 32 16 46

   * - Sev
     - Issue
     - Where
     - Notes
   * - 🔴
     - **846-LoC ``VoiceAiService.kt``**
     - voice/
     - Single largest file. WebSocket handling + dispatch + TTS streaming + state management all in one. Should split: SessionManager, MessageDispatcher, TTSStreamer, InterruptHandler.
   * - 🔴
     - **No human-handoff path visible**
     - voice/
     - For genuine customer support, falling back to a human is critical. The ``End`` message terminates the call — no transfer-to-human flow visible.
   * - 🔴
     - **Voice callers are synthetic users** (``accountId = "voice:$callSid"``)
     - VoiceCallerUser
     - Limits per-caller permissions, history, and personalization. Once call ends, identity gone.
   * - 🟡
     - **Statsig dynamic config for routing** (single point of failure)
     - VoiceAgentResolver
     - If Statsig is unreachable, no calls can route. Worth a fallback to default config.
   * - 🟡
     - **Phone-number-based routing only**
     - VoiceAgentResolver
     - No support for menu-based selection ("press 1 for billing"). All routing happens at call setup.
   * - 🟡
     - **No FF gate for voice mode itself** (none found by grep ``VOICE.*ENABLED``)
     - voice/
     - If voice goes wrong, no "kill switch" to disable.
   * - 🟡
     - **TwilioRequestValidationInterceptor uses HMAC** (assumed; need to verify shared-secret rotation flow)
     - rest/voice/
     - Twilio account secret rotation procedure unclear.
   * - 🟡
     - **OpenAI dependency** (only TTS provider)
     - audio/
     - No fallback if OpenAI TTS is down or rate-limited. CSM voice would fail entirely.
   * - 🟡
     - **No per-call cost tracking visible**
     - architecture
     - OpenAI TTS bills per character; per-call cost is variable. Worth tracking.
   * - 🟢
     - **WebSocket-based** (not HTTP polling) is the right choice
     - design
     - Low latency, full duplex.
   * - 🟢
     - **Standard agent pipeline reuse** (no voice-specific orchestrator)
     - design
     - Same code path as text chat — agent improvements benefit voice automatically.

Refactoring opportunities
============================

1. **Split ``VoiceAiService.kt``** (M, 🔴 high) — 846 LoC into 3-4 files. ~2-3 days.

2. **Add human-handoff flow** (XL, 🔴 high) — call transfer-to-human integration via Twilio's Dial verb or SIP REFER. ~1-2 weeks; requires coordination with CS ops.

3. **Add a kill-switch FF** (XS, 🔴 high) — ``VOICE_MODE_ENABLED`` per-tenant. ~30 min.

4. **Add OpenAI TTS fallback** (M, 🟡 medium) — second TTS provider (Google Cloud TTS, AWS Polly) for redundancy. ~3-5 days.

5. **Document Twilio secret rotation** (XS, 🟡 medium) — how to rotate the Twilio account auth token without dropping calls. ~1 day.

6. **Add per-call cost tracking** (S, 🟡 medium) — emit metric per-(call, voice, character_count). ~1 day.

7. **Add menu-based routing** (M, 🟢 low) — IVR-style "press 1 for X". Could leverage ``Dtmf`` incoming + ``SendDigits`` outgoing already in protocol.

8. **Add per-language support** (M, 🟢 low) — leverage existing ``Language`` outgoing message for runtime switching.

9. **Add voice analytics dashboard** (S, 🟢 low) — call duration, interrupt frequency, silence rate.

10. **Persist voice transcripts to memory** (M, 🟢 low) — let voice-mode contribute to the agent's collection memory for future text interactions.

What you would change here
============================

* **Add a new outgoing voice message type** (e.g., ``Hold`` for hold music):
   1. Add to ``VoiceMessage.kt`` sealed class
   2. Update ``VoiceAiService`` dispatch to emit it
   3. Verify Twilio Conversation Relay supports it

* **Change which OpenAI voice is used** → ``VoiceAIConfig.kt`` config

* **Add a new phone-agent mapping** → Statsig dynamic config ``csm_voice_ai_config``
   * Update ``PhoneAgentMappingConfig`` list with new ``(phoneNumber, cloudId, agentId)``

* **Tune TTS speed / format** → ``TextToSpeechRequest`` defaults in ``VoiceAiService``

* **Modify silence detection threshold** → ``SilenceHandler.kt``

* **Add new voice-only agent behavior** → modify ``VoiceCallerUser`` or add voice-specific FF gates

What you would NOT change here
================================

* Telephony (PSTN) — owned by Twilio
* TTS provider integration — owned by ``platform/service/service-impl/audio/``
* Agent orchestrators — owned by Marathon/SAIN modules
* Statsig dynamic config — owned by ops/release
* Speech recognition — owned by Twilio (in this path)

Verification audit log
========================

✅ **Personally verified with bash:**

* ``VoiceAiService.kt`` is 846 LoC (find + wc)
* ``VoiceMessage.kt`` is 141 LoC; sealed class with 6 incoming + 6 outgoing message types
* ``VoiceAgentResolver.kt`` is 103 LoC; uses Statsig ``csm_voice_ai_config``
* ``VoiceCallerUser.kt`` is 41 LoC; ``accountId = "voice:$callSid"``, ``getUserOrgId()`` returns null
* ``VoiceAiWebSocketHandler.kt`` exists in csm-impl/.../rest/voice/ — confirms WebSocket entry point
* ``VoiceAiWebSocketConfig.kt`` exists — Spring WebSocket configuration
* ``TwilioRequestValidationInterceptorTest.kt`` exists — confirms Twilio integration with signature validation
* ``OpenAITextToSpeechProvider.kt`` exists in service-impl/audio/ — confirms OpenAI as TTS provider
* ``TextToSpeechRequest.kt`` is 43 LoC; has ``OpenAIVoice`` enum (6 voices) and ``OpenAIResponseFormat`` enum (6 formats)
* ``SpeechToTextRequest.kt`` is only 8 LoC — minimal STT contract (suggests STT is mostly done by Twilio)

⚠️ **Inferred from naming + sub-agent reports**:

* End-to-end flow ordering (Caller → Twilio → WebSocket → VoiceAiService → ...) — based on file responsibilities
* The "TTS-1 vs TTS-1-HD" model selection — naming inference; not source-verified
* The "no human-handoff" claim — sub-agent didn't find Genesys/Vonage imports; could exist via different naming
* The "no kill-switch FF" claim — sub-agent didn't search exhaustively
* Voice → memory persistence (claimed not implemented; unverified)

❌ **UNVERIFIED:**

* The exact Twilio webhook URL routing (need to read ``VoiceAiWebSocketConfig.kt``)
* The HMAC validation algorithm details (Twilio's standard X-Twilio-Signature)
* Per-call cost (OpenAI TTS pricing per character × typical chars per call)
* Silence detection threshold defaults
* Voice prompt extraction (does it always come from Twilio's STT or sometimes from convoai's?)
* Concurrent call capacity per backend instance
* WebSocket reconnect behavior on connection drop
* Per-tenant voice config schema (how is ``customParameters`` from Twilio used?)

Open questions for institutional knowledge
=============================================

1. **Why no visible human-handoff path?** Is this a planned future feature, intentional design choice, or implemented elsewhere?
2. **What Twilio account secret rotation procedure exists?**
3. **What's the per-call cost** in OpenAI TTS dollars?
4. **Why no ``VOICE_MODE_ENABLED`` FF?** Risk seems high to ship without one.
5. **Is ``VoiceAiService`` 846 LoC because of inherent complexity** or refactoring debt?
6. **Are there plans for STT in convoai** (not just relying on Twilio)?
7. **Per-tenant voice quotas** — how are runaway calls prevented from billing nightmares?
8. **Memory integration** — does voice-mode produce/consume Collection memories?
9. **What does ``customParameters`` from Twilio Setup contain?** — likely caller metadata
10. **Backend reconnect strategy** — what happens if the WebSocket drops mid-call?

