.. _mod-auth-and-context:

========================
Auth & Request Context
========================

:Files: ``src/slauth/user_context.py`` (155 LoC), ``src/tenant_context/tenant_context_client.py`` (104 LoC), ``src/service/moderation/moderation_request_context.py`` (~80 LoC), ``src/service/moderation/validate_header.py`` (~50 LoC)
:Importance: **P1 — every request goes through this**

SLAuth Header Parsing (``slauth/user_context.py``)
====================================================

``SlauthUserContextStatus`` (StrEnum):

* ``Missing = "none"``
* ``Invalid = "invalid"``
* ``Valid = "valid"``
* ``_missing_()``: logs error + returns ``Invalid`` for unrecognized values

``SlauthUserContextHeaders`` class:

* Parses all ``X-Slauth-*`` headers from Flask ``request``
* Fields: ``status``, ``context``, ``account_id``, ``request_principal``,
  ``issuer``, ``slauth_principal``
* ``is_valid() -> bool``: returns ``status == Valid``
* ``valid_user_context() -> ValidSlauthUserContextHeaders``: raises ``ValueError``
  if status is not Valid

``ValidSlauthUserContextHeaders`` dataclass:

All fields required (raises ``ValueError`` in ``__post_init__`` if missing):
``context``, ``account_id``, ``request_principal``, ``issuer``, ``slauth_principal``.

Tenant Context Client (``tenant_context/tenant_context_client.py``)
=====================================================================

``TenantContextClient``:

* HTTP client for TCS sidecar (``http://localhost:50050``)
* ``resolve_cloud_id(cloud_id: str) -> TenantContext``
* Returns: ``TenantContext(cloud_id, org_id, product, region, ...)``.
* Used when downstream services need full tenant metadata beyond just ``cloud_id``

Moderation Request Context (``moderation_request_context.py``)
===============================================================

``ModerationRequestContext`` — central identity bundle for all moderation operations:

.. code-block:: python

   @dataclass
   class ModerationRequestContext:
       cloud_id: Optional[str]
       user_id: Optional[str]           # from SLAuth account_id
       use_case_id: Optional[str]       # from X-Atlassian-Use-Case-Id
       issuer: Optional[str]            # from X-Slauth-Issuer
       slauth_principal: Optional[str]  # from X-Slauth-Principal
       slauth_context_headers: Optional[SlauthUserContextHeaders]
       user_context_token: Optional[str]
       staff_context_token: Optional[str]

   @classmethod
   def from_incoming_http_request(cls) -> "ModerationRequestContext":
       # Reads from Flask request.headers
       # Parses SlauthUserContextHeaders
       # Resolves user_id from slauth or X-Atlassian-User-Context-Account-Id
       # Returns populated context

``resolve_user_ids() -> ResolvedUserIdentifiers``:

* Returns ``{user_id: Optional[str], anonymous_user_id: Optional[str]}``
* If authenticated user: sets ``user_id``, leaves ``anonymous_user_id=None``
* If anonymous: sets ``anonymous_user_id`` (hash of request), leaves ``user_id=None``
* XOR semantics: exactly one must be non-None for GASv3 analytics

Header validation (``validate_header.py``)
============================================

``@required_headers(required: List[str], one_of: List[List[str]])`` decorator:

Applied as ``@prompt_moderation_blueprint.before_request``:

.. code-block:: python

   @required_headers(
       required=[HeaderNames.X_ATLASSIAN_CLOUD_ID,
                 HeaderNames.X_ATLASSIAN_USE_CASE_ID],
       one_of=one_of_headers,   # one of: SLAuth context OR staff context token
   )
   def handle_etag():
       ...

Returns HTTP 400 with descriptive error if required headers missing.

``HeaderNames`` (StrEnum):

* ``X_ATLASSIAN_CLOUD_ID = "X-Atlassian-Cloud-Id"``
* ``X_ATLASSIAN_USE_CASE_ID = "X-Atlassian-Use-Case-Id"``
* ``X_SLAUTH_USER_CONTEXT = "X-Slauth-User-Context"``
* ``X_ATLASSIAN_STAFF_CONTEXT_TOKEN = "X-Atlassian-Staff-Context-Token"``
