# Changelog

## Unreleased

### Added

- **Octolens → Attio `octolens_mentions` custom-object export.** The Octolens
  webhook now produces a single `UpsertMention` op (`mention_url`-keyed,
  idempotent assert) when `action in {mention_created, mention_updated}`.
  Three CRM-owned fields (`triage_status`, `related_person`,
  `related_company`) are belt-and-suspenders protected from webhook clobber
  (absent from `MentionInput`; assertion guard in
  `build_create_mention_values`). Bootstrap the custom object + 25
  attributes via `scripts/octolens_mentions_bootstrap.py --apply`
  (idempotent; re-run is a no-op).

- **`webhooks/export_to_attio.py` — standalone Modal webhook** that converts a
  source webhook payload into Attio writes via a source-agnostic dispatcher.
  Shipped across three passes:
  - **Pass 1** — `libs/attio/meetings.find_or_create_meeting` adapter,
    `MeetingInput` / `MeetingResult` / `MeetingExternalRef` Pydantic models,
    `build_meeting_payload`, the Modal app shell, and a redacted Fathom call
    fixture. Hardcoded Fathom-call → Attio Meeting path, smoke-tested against
    dev Attio.
  - **Pass 2** — `src/attio/ops.py` Pydantic discriminated-union op vocabulary
    (`UpsertPerson`, `UpsertCompany`, `UpsertMeeting`, `AddNote` +
    `PersonRef` / `CompanyRef` / `MeetingRef` discriminated on `ref_kind`).
    `src/attio/export.py` source-agnostic dispatcher with `LookupTable`,
    `OP_HANDLERS`, fail-fast `execute()` loop, and `ExecutionResult.body()`
    JSON shape (`{"success", "outcomes", optional "fail_index"/"fail_reason"}`).
    `src/fathom/webhook/call.py` rewired to the `attio_*` contract.
  - **Pass 3** — wires the four remaining source webhooks:
    - `src/caldotcom/webhook/booking.py` → `[UpsertMeeting]`, preferring
      Cal.com's real `icsUid` and mapping the booking RSVP status (+
      per-attendee `absent`) to Attio's accepted/tentative/declined/pending
      enum via `_caldotcom_status_to_attio`.
    - `src/attio/export.py::_handle_add_note` implemented against
      `libs/attio/notes.add_note`; resolves `AddNote.parent` through
      `LookupTable` (person→people, company→companies, meeting→meetings) and
      returns a failing envelope with
      `ErrorEntry(code="unresolved_ref", error_type="UnresolvedRefError",
      fatal=True)` when no parent is found.
    - `libs/attio/companies.upsert_company` (new) mirrors
      `libs.attio.people.upsert_person` (search by domain → add or update,
      multi-match picks lexicographically smallest record_id with a
      partial_success warning); used by
      `src/attio/export.py::_handle_upsert_company`.
    - `src/rb2b/webhook/visit.py` → `[UpsertPerson?, UpsertCompany?]`, with
      `extract_domain()` cleaning rb2b's `Website` field; emits only what the
      payload supports (person requires `business_email`, company requires a
      resolvable domain).
    - `src/octolens/webhook/mention.py` and `src/fathom/webhook/message.py`
      get the four `attio_*` methods for protocol uniformity but currently
      return `attio_is_valid_webhook()=False`: Octolens mentions have no
      email/domain to resolve a parent, and Fathom messages don't yet map
      cleanly to Attio.

### Notes

- The Modal app is standalone (`modal deploy webhooks/export_to_attio.py`);
  it does **not** register in `src/app.py` per the webhooks-rule in
  `CLAUDE.md`.
- Linear follow-up: AI-261 — `/v2/meetings/{id}/call_recordings` POST
  (attach Fathom recording URLs to the Meeting record). Out of scope for this
  changeset.
