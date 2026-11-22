# Zenodo feature catalog

Every feature, entry point and user path in Zenodo, with who can use it and how to check it works. It is meant for end-to-end testing against the all-in-one mini image (`docker/mini/Dockerfile` on `slint/zenodo-rdm` `mini-stack`).

*Built in the* [*Zenodo feature catalog*](https://ampcode.com/threads/T-01a202f7-0585-70f0-a4a4-62e050d03271) *thread. The checks live in* `e2e/` *on branch* [`feature-catalog`](https://github.com/slint/zenodo-rdm/tree/feature-catalog)*.*

## How to read and update this

- **Source.** Routes come from the live Flask URL maps of the built image (211 UI rules, 324 API rules), CLI groups from `flask.commands` entry points, jobs from `CELERY_BEAT_SCHEDULE` and `invenio_jobs.jobs`, admin pages from `invenio_administration.views`. API paths are under `/api`.
- **ID.** Each row has an ID such as `records.export`. Automated checks put the ID in their test title (`[records.export] ...`), so `e2e/` results map back to rows.
- **Status.** One of `untested`, `passing`, `failing`, `can't run on mini`. A status other than untested names its evidence: the run date and image commit, or the reason it can't run.
- **Who.** `anon` anyone; `user` any logged-in user; `owner` the record or draft owner (and users the owner shares edit access with); `curator`, `manager`, `owner (community)`, `reader` community roles; `admin` the `admin` role (superuser); `administration` and `administration-moderation` admin panel roles; `media-files-uploader` and `files-manager` Zenodo roles.
- **Mini image.** Fixture users `admin@zenodo.org` (role `admin`) and `eu@zenodo.org` (no role), the `eu` community, vocabularies and OAI sets. No demo records. Emails are not delivered. Search runs on ParadeDB: ranking order and some loose autocomplete matches differ from OpenSearch, so checks assert membership, not order.
- **Docs.** The Docs column links the help.zenodo.org pages (`help:`) and developers.zenodo.org sections (`dev:`) that cover the feature. **none** means a public feature with no docs; internal means staff or operator features the public docs don't need to cover. The source is `e2e/docs/map.json`; see *Docs comparison* below.
- **Agents.** Edit only the sections your thread owns, change only the Status column and add rows for features you find, and record failures under the area's *Findings* line.

## Accounts and users

| ID | Feature and user paths | Entry point | Who | How to check | Docs | Status |
|---|---|---|---|---|---|---|
| `accounts.login` | Log in with email and password; log out | `/login/`, `/logout/`, `POST /api/login`, `/api/logout` | anon | Log in as fixture user, land off `/login`; `/api/me` returns the user | [help: Logging in and logging out](https://help.zenodo.org/docs/get-started/logging-in/) | passing (2026-11-22) |
| `accounts.signup` | Sign up, confirm email, resend confirmation | `/signup/`, `/confirm/<token>`, `POST /api/register`, `/api/confirm-email`, `/api/send-confirmation-email` | anon | Register, read the confirm link from the container log, confirm, log in | [help: Create an account](https://help.zenodo.org/docs/get-started/create-an-account/) | untested |
| `accounts.password` | Forgot and reset password; change password | `/lost-password/`, `/lost-password/<token>/`, `/account/settings/password/`, `POST /api/forgot-password`, `/api/reset-password`, `/api/change-password` | anon, user | Change password, log in with the new one; reset link from the container log | [help: Change password](https://help.zenodo.org/docs/profile/change-password/), [help: Reset password](https://help.zenodo.org/docs/profile/reset-password/) | untested |
| `accounts.profile` | Edit profile (name, affiliation, ORCID-free fields), visibility, preferences | `/account/settings/profile` | user | Save the form, value shows on reload and in `/api/users/<id>` | [help: Edit profile](https://help.zenodo.org/docs/profile/editing-your-profile/), [help: Change profile visibility](https://help.zenodo.org/docs/profile/changing-profile-visibility/) | untested |
| `accounts.security` | List and revoke sessions | `/account/settings/security`, `/api/sessions`, `POST /account/settings/sessions/revoke` | user | Two contexts log in; revoking one logs it out | [help: View logged in devices](https://help.zenodo.org/docs/profile/viewing-devices/) | untested |
| `accounts.tokens` | Create, view, edit scopes and revoke personal access tokens | `/account/settings/applications/tokens/new/`, `.../tokens/<id>/`, `.../revoke/` | user | Create a token, call `/api/me` with it; revoke, call fails with 401 | [dev: Creating a personal access token](https://developers.zenodo.org/#creating-a-personal-access-token), [dev: Using access tokens](https://developers.zenodo.org/#using-access-tokens) | passing for create and use (2026-11-22); revoke untested |
| `accounts.oauth-apps` | Register an OAuth2 client app, reset its secret | `/account/settings/applications/clients/new/`, `.../clients/<id>/reset/` | user | Create a client, run the authorize and token flow (see `integrations.oauth2-provider`) | **none** | untested |
| `accounts.notifications` | Notification preferences (email on/off) | `/account/settings/notifications/` | user | Toggle, value persists | [help: Manage notification preferences](https://help.zenodo.org/docs/profile/managing-notifications/) | untested |
| `accounts.quota` | See storage quota | `/account/settings/quota/` | user | Page shows quota and usage after an upload | [help: Manage storage quota](https://help.zenodo.org/docs/deposit/manage-quota/) | untested |
| `accounts.linked` | Link and unlink external accounts | `/account/settings/linkedaccounts/`, `/oauth/login/<app>/`, `/oauth/disconnect/<app>/` | user | Page lists ORCID, GitHub, OpenAIRE AAI, EOSC AAI | [help: Linking your GitHub/ORCID/OpenAIRE account](https://help.zenodo.org/docs/profile/linking-accounts/), [help: Manage multiple accounts](https://help.zenodo.org/docs/profile/manage-multiple-accounts/) | can't run on mini: needs the providers' OAuth apps; only the page render runs |
| `accounts.oauth-login` | Log in or sign up through ORCID, GitHub, OpenAIRE AAI, EOSC AAI | `/oauth/login/<app>/`, `/oauth/authorized/<app>/`, `/oauth/signup/<app>/` | anon | Redirect to the provider starts | [help: Create an account](https://help.zenodo.org/docs/get-started/create-an-account/), [help: Logging in and logging out](https://help.zenodo.org/docs/get-started/logging-in/) | can't run on mini: external identity providers |
| `users.api` | Read users, avatars, user search | `/api/users`, `/api/users/<id>`, `/api/users/<id>/avatar.svg`, `/api/me` | anon (public profiles), user | Public user readable; private profile hidden from anon | **none** | untested |
| `users.dashboard` | My dashboard: uploads, communities, requests | `/me/uploads`, `/me/communities`, `/me/requests`, `/api/user/records`, `/api/user/communities`, `/api/user/requests` | user | Lists show the user's items only | [help: Navigating Zenodo](https://help.zenodo.org/docs/get-started/navigating-zenodo/), [help: Manage records](https://help.zenodo.org/docs/deposit/manage-records/), [help: View my communities](https://help.zenodo.org/docs/communities/view-my-communities/) | passing for uploads (2026-11-22); communities and requests untested |
| `site.ready` | Fresh image becomes usable | `/ping`, `/api/vocabularies/resourcetypes` | anon | Fixture vocabularies readable and indexed | internal | passing (2026-11-22), after a wait: see Findings |
| `users.ai-waitlist` | Join or dismiss the AI-assist features waitlist | `/ai-assist-features-waitlist`, `.../dismiss` | user | Join, banner hidden | **none** | untested |

Findings:
- On a fresh volume `/ping` answers about 7 minutes after start, but the worker still has about 11,000 fixture vocabulary tasks queued (solo pool), which take another 10 to 15 minutes on 2 CPUs. Until then publishing fails with `Invalid value dataset.` The checks wait for it in `site.ready`.

## Deposit

| ID | Feature and user paths | Entry point | Who | How to check | Docs | Status |
|---|---|---|---|---|---|---|
| `deposit.ui.login-required` | New upload asks anonymous users to log in | `/uploads/new` | anon | Redirect to `/login/?next=` | [help: Logging in and logging out](https://help.zenodo.org/docs/get-started/logging-in/) | passing (2026-11-22) |
| `deposit.ui.publish` | Fill the deposit form, upload a file, publish | `/uploads/new`, `/uploads/<id>` | user | Record landing page shows the title | [help: Quick start](https://help.zenodo.org/docs/get-started/quickstart/), [help: Create new upload](https://help.zenodo.org/docs/deposit/create-new-upload/), [help: Describe records](https://help.zenodo.org/docs/deposit/describe-records/) +1 | passing (2026-11-22) |
| `deposit.ui.save-preview` | Save draft, preview, resume editing, discard | `/uploads/<id>`, `/records/<id>?preview=1` | owner | Draft saved, preview renders, discard removes it | [help: Create new upload](https://help.zenodo.org/docs/deposit/create-new-upload/) | untested |
| `deposit.ui.dashboard` | My uploads lists drafts and records | `/me/uploads` | user | New draft appears | [help: Manage records](https://help.zenodo.org/docs/deposit/manage-records/) | passing (2026-11-22) |
| `deposit.ui.community-upload` | Upload straight into a community | `/communities/<slug>/upload` | user | Form preselects the community; publish opens a submission request | [help: Submit to community](https://help.zenodo.org/docs/share/submit-to-community/), [help: Submitting content](https://help.zenodo.org/guides/eu/submit/) | untested |
| `deposit.api.publish` | Create draft, upload files (init, content, commit), publish | `POST /api/records`, `/api/records/<id>/draft/files...`, `.../actions/publish` | user | 202 and status `published` | **none** | passing (2026-11-22) |
| `deposit.api.validation` | Publish rejects missing required fields | `.../actions/publish` | owner | 400 with errors on title and creators | [dev: Errors](https://developers.zenodo.org/#errors) | passing (2026-11-22) |
| `deposit.api.edit` | Edit a published record and republish | `POST /api/records/<id>/draft`, `PUT .../draft`, publish | owner | New revision, changed title | [help: Manage records](https://help.zenodo.org/docs/deposit/manage-records/) | passing (2026-11-22) |
| `deposit.api.new-version` | New version, import files from the previous one, publish | `POST /api/records/<id>/versions`, `.../files-import` | owner | `versions.index` 2, same parent | [help: Manage versions](https://help.zenodo.org/docs/deposit/manage-versions/) | passing (2026-11-22) |
| `deposit.api.delete-draft` | Discard a draft | `DELETE /api/records/<id>/draft` | owner | 204, then 404 | **none** | passing (2026-11-22) |
| `deposit.api.pids` | Reserve or discard a DOI on a draft; external DOI | `POST/DELETE /api/records/<id>/draft/pids/doi` | owner | Reserved DOI `10.5281/zenodo.<id>` on the draft | [help: Digital Object Identifier (DOI)](https://help.zenodo.org/docs/deposit/describe-records/reserve-doi/) | untested |
| `deposit.api.multipart` | Multipart upload of large files | `PUT .../draft/files/<key>/content/<part>` | owner | Upload in parts, commit, checksum matches | **none** | untested |
| `deposit.api.media-files` | Media files (thumbnails, IIIF sources) on drafts | `/api/records/<id>/draft/media-files...` | `media-files-uploader` | Upload as that role; denied for a plain user | **none** | untested |
| `deposit.review` | Submit a draft to a community for review | `PUT/GET/DELETE /api/records/<id>/draft/review`, `.../actions/submit-review` | owner | Request created in the community (see `requests.*`) | [help: Submit for review](https://help.zenodo.org/docs/share/submit-for-review/) | untested |
| `deposit.permissions` | Drafts are private to their owner | `GET /api/records/<id>/draft` | owner, admin | anon 403, admin 200 | [help: About collaboration and sharing](https://help.zenodo.org/docs/share/about/) | passing (2026-11-22) |
| `deposit.restricted-files` | Public metadata with restricted files | `access.files = restricted` | owner | anon can read the record, not the file | [help: Manage files](https://help.zenodo.org/docs/deposit/manage-files/) | passing (2026-11-22) |
| `deposit.embargo` | Embargoed access lifts on its date | `access.embargo`, beat `update_expired_embargos` | owner | Embargo in the past lifts after the task runs | [help: Create new upload](https://help.zenodo.org/docs/deposit/create-new-upload/) | untested |
| `deposit.quota` | Quota increase: immediate for eligible users, request otherwise | `POST /api/records/<id>/quota-increase`, `/api/records/<id>/quota`, `/api/users/<id>/quota` | owner, admin | Quota grows; request created when not eligible | [help: Manage storage quota](https://help.zenodo.org/docs/deposit/manage-quota/) | untested |
| `deposit.file-modification` | Change files of a published record (immediate within grace period, else request) | `POST /api/records/<id>/file-modification` | owner, `files-manager` (external DOI) | Files unlocked for edit | [help: Manage files](https://help.zenodo.org/docs/deposit/manage-files/) | untested |
| `deposit.legacy` | Legacy Zenodo deposit API: create, upload to bucket, set metadata, publish | `/api/deposit/depositions...`, `/api/files/<bucket>/<key>` | user (`deposit:write`, `deposit:actions` scopes) | `state` done, `submitted` true | [dev: Quickstart - Upload](https://developers.zenodo.org/#quickstart-upload), [dev: Depositions](https://developers.zenodo.org/#depositions), [dev: Deposition files](https://developers.zenodo.org/#deposition-files) +1 | passing (2026-11-22) |
| `deposit.legacy.actions` | Legacy edit, discard, new version, files list and delete, extra formats | `/api/deposit/depositions/<id>/actions/{edit,discard,newversion}`, `.../files`, `.../formats` | owner | Each action returns the documented legacy JSON | [dev: Deposition actions](https://developers.zenodo.org/#deposition-actions), [dev: Deposition files](https://developers.zenodo.org/#deposition-files) | untested |
| `deposit.orcha` | AI assistance on the deposit form (ORCHA workflow, feedback, files) | `POST /uploads/<id>/orcha`, `.../feedback`, `/orcha-proxy/...` | owner with `orcha-access` | Stream URL returned | **none** | can't run on mini: external ORCHA service |

Findings:
- RDM publish needs `metadata.publisher`, or it fails with 400 `Missing publisher field required for DOI registration.`. The deposit form leaves the publisher empty, and the form also needs an answer to "Do you already have a DOI?", or it fails with `Missing DOI for required field.`. The legacy API fills in both.
- Anonymous reads of someone else's draft answer 404, not 403.

## Records

| ID | Feature and user paths | Entry point | Who | How to check | Docs | Status |
|---|---|---|---|---|---|---|
| `records.landing` | Landing page: metadata, files, citation, versions, communities, stats | `/records/<id>` | anon | Title, creators and file list render | [help: About records](https://help.zenodo.org/docs/deposit/about-records/) | passing (2026-11-22) |
| `records.api.read` | Read a record, its versions and latest version | `/api/records/<id>`, `.../versions`, `.../versions/latest`, `/records/<id>/latest` | anon | JSON with title; versions total | [dev: Records](https://developers.zenodo.org/#records) | passing (2026-11-22) |
| `records.export` | Export formats: json, json-ld, csl, datacite-json, datacite-xml, dublincore, marcxml, bibtex, dcat-ap, codemeta, cff, geojson, datapackage | `/records/<id>/export/<fmt>`, `Accept` on `/api/records/<id>` | anon | Each returns 200 with format-specific content | **none** | passing (2026-11-22) |
| `records.citation` | Citation in a CSL style | `/api/records/<id>?style=<style>` with `Accept: text/x-bibliography` | anon | APA citation contains the author | [help: FAQ](https://help.zenodo.org/faq/) | passing (2026-11-22) |
| `records.api.legacy-json` | Plain `application/json` on `/api/records` returns the legacy Zenodo format (`doi`, `recid`, no `pids`); RDM JSON needs `Accept: application/vnd.inveniordm.v1+json` | `/api/records/<id>` | anon | Legacy body has the record's DOI | [dev: Records](https://developers.zenodo.org/#records) | passing (2026-11-22) |
| `records.pid-resolve` | Resolve by DOI or OAI id | `/doi/<doi>`, `/oai/<id>` | anon | Redirect to the landing page | **none** | untested |
| `records.revisions` | Revision history | `/api/records/<id>/revisions` | admin | Revisions listed after an edit | **none** | untested |
| `records.delete` | Delete a record (tombstone), restore it; deletion request | `DELETE /api/records/<id>/delete`, `POST .../restore`, `POST .../request-deletion` | admin; owner (immediate deletion within the grace period) | Tombstone page 410; restore brings it back | [help: Manage records](https://help.zenodo.org/docs/deposit/manage-records/) | untested |
| `records.tombstone` | Tombstone landing page for deleted records | `/records/<id>` | anon | 410 with tombstone text | **none** | untested |
| `records.communities` | Add, remove, list a record's communities; suggestions | `/api/records/<id>/communities`, `.../communities-suggestions` | owner, community curators | Inclusion request created; removal works | [help: Submit to community](https://help.zenodo.org/docs/share/submit-to-community/), [help: Curate records](https://help.zenodo.org/docs/communities/curate/) | untested |
| `records.redirects` | Legacy Zenodo URLs redirect: `/record/<id>`, exports (`hx`, `xd`, `xm`, `dcite4`, `dcat`), `/deposit/...`, `/collection/...`, `/communities/about/...`, static pages | `invenio_redirector.*` | anon | Each answers 301/302 to the RDM URL | **none** | untested |
| `records.badges` | DOI badges (svg, png) | `/badge/doi/<doi>.svg` | anon | SVG with the DOI | **none** | untested |

Findings:
- Sending a legacy-format body back to `PUT /api/records/<id>/draft` answers 500 (`TypeError: pop expected at most 1 argument, got 2` in schema load) instead of a 400. It's easy to hit, since plain JSON GETs return the legacy format.

## Files and previews

| ID | Feature and user paths | Entry point | Who | How to check | Docs | Status |
|---|---|---|---|---|---|---|
| `records.files.download` | Download a public file (UI and API) | `/records/<id>/files/<key>?download=1`, `/api/records/<id>/files/<key>/content` | anon | Bytes match the upload | **none** | passing (2026-11-22) |
| `files.archive` | Download all files as zip | `/api/records/<id>/files-archive`, `.../draft/files-archive` | anon (public files) | Zip lists every file | **none** | untested |
| `files.preview` | Previewers: PDF, images, CSV, JSON/XML, text, Markdown, Jupyter, zip listing, video, web archives | `/records/<id>/preview/<key>` | anon | Preview frame renders for each type | [help: Manage files](https://help.zenodo.org/docs/deposit/manage-files/) | untested |
| `files.container` | Browse inside zip containers | `/records/<id>/files/<key>/container/<path>`, `/api/records/<id>/files/<key>/container` | anon | Listing and one inner file | **none** | untested |
| `files.iiif` | IIIF manifest, image API, thumbnails | `/api/iiif/record:<id>/manifest`, `/api/iiif/.../info.json`, `/records/<id>/thumb<size>` | anon | Manifest JSON; a tile is an image | **none** | untested |
| `files.media` | Media files on records | `/records/<id>/media-files/<key>`, `/api/records/<id>/media-files` | anon | Listed and downloadable | **none** | untested |
| `files.legacy-files-rest` | Legacy files REST buckets | `/api/files/<bucket>`, `/api/legacy-files/...` | owner | Covered by `deposit.legacy` bucket upload | [dev: Deposition files](https://developers.zenodo.org/#deposition-files) | untested |
| `files.offload` | XRootD/EOS offload, X-Sendfile | `XROOTD_ENABLED`, `ZENODO_EOS_OFFLOAD_ENABLED` | anon | Download is redirected or offloaded | internal | can't run on mini: CERN storage |
| `files.integrity` | Checksum verification and integrity report | beat `file-checks` | system | Task runs, files marked checked | internal | untested |

Findings: none yet.

## Search

| ID | Feature and user paths | Entry point | Who | How to check | Docs | Status |
|---|---|---|---|---|---|---|
| `search.api` | Record search with query, facets (aggregations) | `/api/records?q=` | anon | New record found; aggregations present | [dev: Records](https://developers.zenodo.org/#records) | passing (2026-11-22) |
| `search.ui` | Search page with facets, sort, pagination | `/search` | anon | New record listed | [help: Search guide](https://help.zenodo.org/guides/search/), [help: Navigating Zenodo](https://help.zenodo.org/docs/get-started/navigating-zenodo/) | passing (2026-11-22) |
| `search.sort-filter` | Sort and filter by facet | `/api/records?sort=&resource_type=` | anon | Filtered hits all match | [help: Search guide](https://help.zenodo.org/guides/search/), [dev: Records](https://developers.zenodo.org/#records) | passing (2026-11-22) |
| `search.query-syntax` | Zenodo query parser: field queries, DOIs, ranges, boolean | `zenodo_rdm.queryparser` | anon | Each query type returns the expected record | [help: Search guide](https://help.zenodo.org/guides/search/) | untested |
| `search.communities` | Community search and featured | `/communities-search`, `/api/communities`, `/api/communities/featured` | anon | `eu` community found | [help: Navigating Zenodo](https://help.zenodo.org/docs/get-started/navigating-zenodo/) | untested |
| `search.user-records` | Search own drafts and records | `/api/user/records?q=` | user | Own draft found, others' not | [help: Manage records](https://help.zenodo.org/docs/deposit/manage-records/) | untested |
| `search.vocabularies` | Autocomplete for licenses, funders, awards, affiliations, names, subjects | `/api/vocabularies/<type>?suggest=`, `/api/funders`, `/api/awards`, ... | anon, user | Known fixture term suggested (loose matches differ on ParadeDB) | [help: Funding information](https://help.zenodo.org/docs/deposit/describe-records/funding/), [help: Keywords and subjects](https://help.zenodo.org/docs/deposit/describe-records/keywords-and-subjects/), [help: Licenses and rights](https://help.zenodo.org/docs/deposit/describe-records/licenses/) +1 | untested |
| `search.help` | Search help page | `/help/search` | anon | Page renders | [help: Search guide](https://help.zenodo.org/guides/search/) | untested |

Findings:
- Anonymous searches are capped at 25 results per page (400 above that); authenticated ones at 100.

## Communities

| ID | Feature and user paths | Entry point | Who | How to check | Docs | Status |
|---|---|---|---|---|---|---|
| `communities.create` | Create a community; rename; delete and restore | `/communities-new`, `POST /api/communities`, `.../rename`, `DELETE /api/communities/<id>`, `.../restore` | user; admin for restore | Community page loads at its slug | [help: Create new community](https://help.zenodo.org/docs/communities/creating-a-community/), [help: Delete community](https://help.zenodo.org/docs/communities/manage-community-settings/delete-community/) | untested |
| `communities.pages` | Home, about, curation policy, browse, records, custom pages | `/communities/<slug>/`, `.../about`, `.../curation-policy`, `.../browse`, `.../records`, `.../pages/<slug>` | anon (public) | `eu` pages render | [help: Add about/curation policy pages](https://help.zenodo.org/docs/communities/manage-community-settings/add-pages/), [help: About communities](https://help.zenodo.org/docs/communities/about-communities/) | untested |
| `communities.settings` | Settings: profile, logo, privileges, submission policy, pages, theme | `/communities/<slug>/settings...`, `PUT /api/communities/<id>`, `/api/communities/<id>/logo` | owner (community), manager | Changes persist | [help: Manage community settings](https://help.zenodo.org/docs/communities/manage-community-settings/), [help: Edit community profile](https://help.zenodo.org/docs/communities/manage-community-settings/edit-profile/), [help: Set submission policy](https://help.zenodo.org/docs/communities/manage-community-settings/review-policy/) +1 | untested |
| `communities.members` | Invite members, change roles, remove; public members list | `/communities/<slug>/members`, `.../invitations`, `/api/communities/<id>/members`, `.../invitations` | owner, manager | Invitee accepts, gets the role | [help: Manage members](https://help.zenodo.org/docs/communities/manage-members/), [help: Invite member](https://help.zenodo.org/docs/communities/manage-members/invite-member/), [help: Change member role](https://help.zenodo.org/docs/communities/manage-members/change-role/) +7 | untested |
| `communities.membership-requests` | Request to join an open community | `POST /api/communities/<id>/actions/join-request`, `.../membership-requests` | user | Request appears for managers; accept adds the member | [help: Navigating EU Open Research Repository](https://help.zenodo.org/guides/eu/navigation/) | untested |
| `communities.records` | List and remove community records | `/api/communities/<id>/records` | anon (list), curator (remove) | Included record listed; removal works | [help: Curate records](https://help.zenodo.org/docs/communities/curate/) | untested |
| `communities.featured` | Feature a community on the front page | `/api/communities/<id>/featured` | admin | Shows in `/api/communities/featured` | internal | untested |
| `communities.subcommunities` | Create a subcommunity or join a parent (request, checks) | `/communities/<slug>/subcommunities/new`, `.../browse/subcommunities`, `/api/communities/<id>/subcommunities` | owner (community) | Request created; accepted child listed (EU flow runs metadata checks) | [help: Request an EU Project Community](https://help.zenodo.org/guides/eu/requesting-a-community/), [help: Project checks](https://help.zenodo.org/guides/eu/requesting-a-community/project-checks/) | untested |
| `communities.collections` | Collection trees and collections with queries | `/api/communities/<id>/collection-trees...`, `/communities/<slug>/collections/...` | manager | Collection lists records matching its query | [help: Browse collections](https://help.zenodo.org/guides/eu/browse/) | untested |
| `communities.theme` | Branded communities (EU, horizon theme) | `/communities/<slug>/community-theme-<rev>.css` | anon | `eu` renders with its theme CSS | [help: Curate records](https://help.zenodo.org/docs/communities/curate/), [help: What's new?](https://help.zenodo.org/docs/about/whats-new/) | untested |

Findings: none yet.

## Requests and notifications

| ID | Feature and user paths | Entry point | Who | How to check | Docs | Status |
|---|---|---|---|---|---|---|
| `requests.submission` | Community submission: submit, accept, decline, cancel | `/api/records/<id>/draft/review`, `/api/requests/<id>/actions/{accept,decline,cancel}` | owner, curator | Accepted draft is published into the community | [help: Review submissions](https://help.zenodo.org/docs/communities/review-submissions/), [help: Cancel/withdraw submission](https://help.zenodo.org/docs/share/manage-submissions/cancel-submissions/) | untested |
| `requests.inclusion` | Include a published record in a community | `POST /api/records/<id>/communities` | owner, curator | Accept adds the community to the record | [help: Submit to community](https://help.zenodo.org/docs/share/submit-to-community/) | untested |
| `requests.timeline` | Comment, reply, edit and delete comments; attach files; timeline | `/api/requests/<id>/comments...`, `.../timeline`, `/api/requests/<id>/files/upload/<key>` | request participants | Comment visible to the other party | [help: Reply/edit/delete comments](https://help.zenodo.org/docs/share/manage-submissions/reply-comments/), [help: Review submissions](https://help.zenodo.org/docs/communities/review-submissions/) | untested |
| `requests.locking` | Lock and unlock conversations | `/api/requests/<id>/lock`, `.../unlock` | receiver | Locked request rejects new comments | **none** | untested |
| `requests.dashboard` | Request pages for users and communities | `/me/requests/<id>`, `/communities/<slug>/requests/<id>` | participants | Page renders with actions | [help: View submissions](https://help.zenodo.org/docs/share/manage-submissions/view-submissions/) | untested |
| `requests.expiry` | Expire old requests | beat `expire_requests` | system | Expired invitation closes | **none** | untested |
| `requests.checks` | Rerun automated checks on a request | `POST /checks/<run_id>/rerun` | curator | Check run restarts | [help: Metadata checks](https://help.zenodo.org/guides/eu/submit/metadata-checks/), [help: File format checks](https://help.zenodo.org/guides/eu/submit/file-checks/), [help: Funding checks](https://help.zenodo.org/guides/eu/submit/funding-checks/) +1 | untested |
| `notifications.email` | Emails for requests, invitations, access requests | invenio-notifications | system | Mail logged by the app | [help: Manage notification preferences](https://help.zenodo.org/docs/profile/managing-notifications/) | can't run on mini: no mail delivery; read the container log instead |

Findings: none yet.

## Access and sharing

| ID | Feature and user paths | Entry point | Who | How to check | Docs | Status |
|---|---|---|---|---|---|---|
| `access.links` | Share links (view, preview, edit) | `/api/records/<id>/access/links...` | owner | Link token opens the draft for anon | [help: Link sharing](https://help.zenodo.org/docs/share/link-sharing/) | untested |
| `access.grants` | Share with users and groups | `/api/records/<id>/access/grants`, `.../access/users`, `.../access/groups` | owner | Grantee can read or edit | [help: User sharing](https://help.zenodo.org/docs/share/user-sharing/) | untested |
| `access.request` | Request access to restricted files (user or guest with email confirm) | `POST /api/records/<id>/access/request`, `/access/requests/confirm`, `/access/requests/<id>` | anon, user | Request reaches the owner; accept grants access | [help: Request access](https://help.zenodo.org/docs/share/access-requests/request-access/) | untested |
| `access.settings` | Access request settings on a record | `PUT /api/records/<id>/access` | owner | Toggle accept-requests | [help: Allow access requests](https://help.zenodo.org/docs/share/access-requests/allow-requests/) | untested |
| `access.resource-tokens` | Resource access tokens for files | `RDM_RESOURCE_ACCESS_TOKENS_ENABLED`, `tokens:generate` scope | owner | Token downloads a restricted file | **none** | untested |

Findings: none yet.

## Stats and metrics

| ID | Feature and user paths | Entry point | Who | How to check | Docs | Status |
|---|---|---|---|---|---|---|
| `stats.counts` | Views and downloads counted and shown on the record | beat `stats-process-events`, `stats-aggregate-events`, `reindex-stats` | system | Visit, download, run tasks, `stats` in `/api/records/<id>` grows | [help: FAQ](https://help.zenodo.org/faq/) | untested |
| `stats.api` | Stats query API | `POST /api/stats` | anon | `record-view` query returns counts | **none** | untested |
| `stats.metrics` | Zenodo metrics (OpenAIRE Nexus) | `/api/metrics/openaire-nexus` | anon | JSON with counts | **none** | untested |
| `stats.export` | Export events to OpenAIRE Matomo | `zenodo_rdm.stats.tasks.export_stats` | system | Not scheduled in local dev | internal | can't run on mini: external Matomo, disabled when `IS_LOCAL_DEV` |
| `stats.help` | Statistics help page | `/help/statistics` | anon | Page renders | [help: FAQ](https://help.zenodo.org/faq/) | untested |

Findings: none yet.

## Integrations

| ID | Feature and user paths | Entry point | Who | How to check | Docs | Status |
|---|---|---|---|---|---|---|
| `integrations.datacite` | DOI minting on publish and DataCite registration | `RDM_PERSISTENT_IDENTIFIERS`, DataCite test mode | system | Record gets `pids.doi`; registration task | [help: Digital Object Identifier (DOI)](https://help.zenodo.org/docs/deposit/describe-records/reserve-doi/), [dev: Testing](https://developers.zenodo.org/#testing) | can't run on mini for registration: needs DataCite credentials; local DOI minting runs |
| `integrations.github` | Enable repositories, sync, release webhooks create versions, badges | `/account/settings/github/`, `/api/user/github/...`, `/api/hooks/receivers/github/events/` | user with GitHub linked | Release payload creates a record | [help: Enable a repository](https://help.zenodo.org/docs/github/enable-repository/), [help: Archive a release from GitHub](https://help.zenodo.org/docs/github/archive-software/github-upload/), [help: CITATION.cff file](https://help.zenodo.org/docs/github/describe-software/citation-file/) +3 | can't run on mini: needs a GitHub app; a signed fake webhook could exercise the receiver |
| `integrations.oauth2-provider` | Zenodo as OAuth2 provider: authorize, token, ping, info | `/oauth/authorize`, `/oauth/token`, `/oauth/info` | user | Client from `accounts.oauth-apps` gets a token | [dev: Authentication](https://developers.zenodo.org/#authentication) | untested |
| `integrations.openaire` | Direct indexing to OpenAIRE, retry failures | `zenodo_rdm.openaire.tasks` | system | — | internal | can't run on mini: external OpenAIRE API |
| `integrations.swh` | Software Heritage deposits | `invenio_swh`, beat `cleanup-swh-depositions` | system | — | **none** | can't run on mini: external SWH |
| `integrations.support` | Support and contact form | `/support` | anon, user | Form renders; submission goes to Zammad | [help: FAQ](https://help.zenodo.org/faq/) | can't run on mini for submission: needs Zammad; form render runs |
| `integrations.exporter` | Bulk record exports for download | `/api/exporter`, `/api/exporter/<key>`, job `export_records`, `invenio exporter export-records` | anon | Export file listed and downloadable after the job | [dev: Metadata Dumps](https://developers.zenodo.org/#metadata-dumps), [dev: List available dumps](https://developers.zenodo.org/#list-available-dumps), [dev: Download a dump](https://developers.zenodo.org/#download-a-dump) | untested |

Findings: none yet.

## OAI-PMH, sitemap and static pages

| ID | Feature and user paths | Entry point | Who | How to check | Docs | Status |
|---|---|---|---|---|---|---|
| `oai.identify` | Identify, ListMetadataFormats | `/oai2d?verb=Identify` | anon | Valid responses with `oai_dc`, `datacite`, `oai_datacite` | [dev: OAI-PMH](https://developers.zenodo.org/#oai-pmh), [dev: Get information about the OAI-PMH API](https://developers.zenodo.org/#get-information-about-the-oai-pmh-api), [dev: Metadata formats](https://developers.zenodo.org/#metadata-formats) | passing (2026-11-22) |
| `oai.getrecord` | GetRecord for a new record | `/oai2d?verb=GetRecord` | anon | Record metadata returned | [dev: OAI-PMH](https://developers.zenodo.org/#oai-pmh), [dev: Harvesting with a different metadata format](https://developers.zenodo.org/#harvesting-with-a-different-metadata-format) | passing (2026-11-22) |
| `oai.sets` | ListSets, ListRecords and ListIdentifiers by set (communities as `user-<slug>`) | `/oai2d`, `/api/oaipmh/sets` | anon | Record in a community is in its set | [dev: Sets](https://developers.zenodo.org/#sets), [dev: Selective harvesting](https://developers.zenodo.org/#selective-harvesting), [dev: Resumption tokens](https://developers.zenodo.org/#resumption-tokens) | untested |
| `site.sitemap` | Sitemaps and robots.txt | `/sitemap.xml`, `/sitemap_<n>.xml`, `/robots.txt`, beat `update-sitemap` | anon | Record URL appears after the task | **none** | untested |
| `site.frontpage` | Front page, featured communities, recent uploads | `/`, beat `frontpage-cache-warmup` | anon | Page renders | [help: Navigating Zenodo](https://help.zenodo.org/docs/get-started/navigating-zenodo/) | untested |
| `site.pages` | Static pages from `app_data/pages.yaml` and help pages | `invenio_pages` routes, `/help/versioning` | anon | Each page renders | **none** | untested |
| `site.i18n` | Language switch | `invenio_i18n` | anon | Page renders in another locale | **none** | untested |
| `site.ping` | Health check | `/ping`, `/api/ping` | anon | 200 | internal | untested |

Findings: none yet.

## Administration

| ID | Feature and user paths | Entry point | Who | How to check | Docs | Status |
|---|---|---|---|---|---|---|
| `admin.access` | Admin panel only for admin roles | `/administration/` | administration, admin | user gets 403, admin 200 | internal | untested |
| `admin.users` | List, create, view users; activate, deactivate, approve, block, restore, impersonate; groups; quota | `/administration/users...`, `/api/users/<id>/{activate,deactivate,approve,block,restore,impersonate,quota}` | administration, administration-moderation | Block hides the user's records; restore undoes | internal | untested |
| `admin.moderation` | Moderation requests and user moderation | `/administration/moderation`, `/administration/requests`, `/api/administration/moderation/requests` | administration-moderation | New-user spam request appears and resolves | internal | untested |
| `admin.records` | Records and drafts admin: delete, restore, view revisions | `/administration/records`, `/administration/drafts` | administration | Delete via admin creates a tombstone | internal | untested |
| `admin.communities` | Communities admin: feature, delete, restore | `/administration/communities...` | administration | Actions apply | internal | untested |
| `admin.domains` | Email domain block and allow list | `/administration/domains...`, `/api/domains` | administration | Blocked domain cannot sign up | internal | untested |
| `admin.roles` | Roles CRUD | `/administration/roles...` | admin | Role created and assignable | internal | untested |
| `admin.banners` | Site banners | `/administration/banners...`, `/api/banners` | administration | Active banner shows on pages | internal | untested |
| `admin.pages` | Static pages CMS | `/administration/pages...`, `/api/pages` | administration | Edited page renders | internal | untested |
| `admin.oai-sets` | OAI sets CRUD | `/administration/oai-pmh...`, `/api/oaipmh/sets` | administration | New set listed in ListSets | internal | untested |
| `admin.vocabularies` | Vocabulary types list and entries | `/administration/vocabulary-types`, `/api/vocabularies` | administration | Types listed | internal | untested |
| `admin.jobs` | Jobs: create, schedule, run, stop, logs | `/administration/jobs...`, `/api/jobs`, `/api/jobs/<id>/runs`, `/api/logs/jobs` | administration | A run of `update_expired_embargos` finishes with logs | internal | untested |
| `admin.audit-logs` | Audit log | `/administration/audit-logs`, `/api/audit-logs` | administration | Publish appears as an audit event | internal | untested |
| `admin.moderation-queries` | Spam queries and domain lists for moderation | `invenio moderation queries add`, `invenio moderation domains add` | admin (CLI) | Matching record flagged | internal | failing (2026-11-22): the percolator index is missing, see Findings |

Findings:
- Every publish logs `index_not_found_exception` for `zenodo-moderation-queries-rdmrecords-records-record-v7.0.0`. `wipe_recreate.sh` never runs `invenio moderation queries create-index`, so moderation query rules don't run on a fresh instance (any fresh local setup, not only mini). Publishing still succeeds. `invenio moderation queries create-index` works on the mini image (ParadeDB accepted the percolator index); whether matching works there is untested.

## Background and scheduled jobs

Beat schedule on the mini image (`IS_LOCAL_DEV` is true, so stats export and blocklist imports are off). Each row checks that the task runs and does its job.

| ID | Task (schedule name) | What it does | How to check | Docs | Status |
|---|---|---|---|---|---|
| `jobs.indexer` | `manage_indexer_queues` (`indexer`) | Bulk indexing from queues | New record searchable (covered by `search.api`) | internal | passing (2026-11-22) |
| `jobs.drafts-cleanup` | `cleanup_drafts` | Removes soft-deleted drafts | Discarded draft gone from DB after run | internal | untested |
| `jobs.embargo` | `update_expired_embargos` | Lifts embargoes | See `deposit.embargo` | internal | untested |
| `jobs.requests-expiry` | `check_expired_requests` | Expires requests | See `requests.expiry` | internal | untested |
| `jobs.accounts` | `clean_session_table`, `delete_ips`, `update_domain_status` | Session and IP hygiene, domain stats | Task succeeds | internal | untested |
| `jobs.stats` | `process_events`, `aggregate_events`, `reindex_stats` | Stats pipeline | See `stats.counts` | internal | untested |
| `jobs.communities-cache` | `invenio_communities.tasks.clear_cache` | Clears community identity cache | Task succeeds | internal | untested |
| `jobs.access-tokens` | `clean_expired_request_access_tokens` | Drops expired guest tokens | Task succeeds | internal | untested |
| `jobs.job-logs` | `delete_logs` | Prunes job logs | Task succeeds | internal | untested |
| `jobs.collections-size` | `update_collections_size` | Collection counts | Count updates | internal | untested |
| `jobs.sitemap` | `update_sitemap_cache` (scheduled twice: `update_sitemap` and `update-sitemap`) | Sitemap cache | See `site.sitemap` | internal | untested |
| `jobs.metrics` | `calculate_metrics` | Metrics cache | See `stats.metrics` | internal | untested |
| `jobs.frontpage` | `warm_frontpage_cache` | Front page cache | Task succeeds | internal | untested |
| `jobs.file-checks` | `schedule_checksum_verification` | File integrity | See `files.integrity` | internal | untested |
| `jobs.checks-cleanup` | `cleanup_stale_check_runs` | Stale check runs | Task succeeds | internal | untested |
| `jobs.openaire-retry`, `jobs.swh-cleanup` | `retry_openaire_failures`, `cleanup_depositions` | External services | — | internal | can't run on mini: external services |
| `jobs.registered` | Admin jobs: `update_expired_embargos`, vocabulary imports (ORCID, ROR, EDMO, CORDIS, OpenAIRE awards, EuroSciVoc), `eu_records_curation`, `export_records` | Run from `/administration/jobs` | Embargo and export jobs finish; imports need downloads | internal | untested; vocabulary imports can't run on mini (external downloads) |

Findings: two beat entries run the sitemap update (`update_sitemap` from invenio-app-rdm, `update-sitemap` from `invenio.cfg`).

## CLI

| ID | Commands | Who | How to check | Docs | Status |
|---|---|---|---|---|---|
| `cli.setup` | `db`, `index`, `files location`, `roles`, `access`, `rdm-records fixtures`, `rdm-records custom-fields`, `communities custom-fields`, `vocabularies import`, `queues declare` | operator | `wipe_recreate.sh` on first start (the image boots) | internal | passing (2026-11-22) |
| `cli.users` | `users create/activate/deactivate`, `roles add/remove`, `tokens create`, `domains` | operator | Created user can log in | internal | untested |
| `cli.rdm` | `rdm` (rebuild indices, ...), `rdm-records` (demo, rebuild, ...), `communities`, `identity-cache`, `stats`, `jobs`, `i18n`, `collect` | operator | Each subcommand exits 0 on the mini image | internal | untested |
| `cli.zenodo` | `zenodo-admin delete <recid>`, `moderation queries create-index/add`, `moderation domains add`, `exporter export-records` | operator | Deleted record disappears; export file created | internal | untested |

Findings: none yet.

## Permissions and roles

What changes what a user can do. Each area's rows name the role; this table lists the role sources to cover.

| ID | Rule | Source | How to check | Docs | Status |
|---|---|---|---|---|---|
| `perms.records` | Record and draft policy: owners, shared access, communities, `media-files-uploader`, `files-manager` | `zenodo_rdm.permissions`, `zenodo_rdm.generators` | Matrix of anon / user / owner / curator / admin over read, edit, publish, delete, files | [help: About collaboration and sharing](https://help.zenodo.org/docs/share/about/), [help: User sharing](https://help.zenodo.org/docs/share/user-sharing/) | untested |
| `perms.communities` | Community policy: owner, manager, curator, reader; open or closed membership, record and review policies | `ZenodoCommunityPermissionPolicy` | Same matrix over community actions | [help: About communities](https://help.zenodo.org/docs/communities/about-communities/), [help: Change member role](https://help.zenodo.org/docs/communities/manage-members/change-role/) | untested |
| `perms.admin` | `superuser-access`, `administration-access`, `administration-moderation` roles | `wipe_recreate.sh` roles | See `admin.access` | internal | untested |
| `perms.scopes` | OAuth scopes: `deposit:write`, `deposit:actions`, `user:email`, `tokens:generate`, `webhooks:event` | `invenio_oauth2server.scopes` entry points | Token without the scope is refused on legacy deposit | [dev: Scopes](https://developers.zenodo.org/#scopes) | untested |
| `perms.rate-limits` | Rate limits (Postgres-backed on mini) | `RATELIMIT_*` | Burst of anonymous requests gets 429 | [dev: Rate Limiting](https://developers.zenodo.org/#rate-limiting), [dev: Rate limit](https://developers.zenodo.org/#rate-limit) | untested |
| `perms.spam` | New-user moderation and spam checks on publish | `RDM_USER_MODERATION_ENABLED`, `zenodo_rdm.moderation` | Spammy record from a new user is flagged | internal | untested; query rules are off on a fresh instance (see `admin.moderation-queries`) |

## Docs comparison

Built from crawling help.zenodo.org (105 pages) and developers.zenodo.org (67 sections) on 2026-11-22, mapped by hand in `e2e/docs/map.json`. Browse it per feature, with playbooks and filters, at the [feature catalog site](https://t-03ha70mz297fsi61sdutywgoh-p20119.onamp.dev/).

**Coverage.** Of 150 features, 44 are internal (admin, jobs, CLI, operations). Of the 106 public features:

| Documented in | Features |
|---|---|
| help and developers | 4 |
| help only | 59 |
| developers only | 15 |
| neither | 28 |

The 28 undocumented public features are mostly API-level or secondary paths: the RDM REST API (`/api/records` drafts, delete draft, multipart, media files), export formats, files archive, zip containers, IIIF, badges, DOI/OAI resolve, tombstones, legacy URL redirects, revisions, stats API and metrics, OAuth app registration, request locking and expiry, resource access tokens, sitemap, static pages, language switch, Software Heritage, the AI-assist waitlist and ORCHA.

**The biggest gap.** developers.zenodo.org documents only the legacy `/api/deposit/depositions` API. Its changelog ends on 2017-10-04, and nothing covers the InvenioRDM REST API (`/api/records` drafts, communities, requests, access and sharing), which the app itself uses.

**Docs that describe things the catalog lacks:**
- [help /docs/deposit/describe-records/](https://help.zenodo.org/docs/deposit/describe-records/): Field-by-field metadata docs (titles, creators, contributors, descriptions, funding, subjects, licenses, EDTF dates, resource types, publisher). The catalog has no per-field rows; suggest adding deposit.metadata.* rows, including 'Add authors from file', which the form has and the docs don't mention.
- [help /docs/profile/manage-multiple-accounts/](https://help.zenodo.org/docs/profile/manage-multiple-accounts/): Merging accounts. No merge feature exists in the code or the routes; the page describes a manual process.
- [help /docs/communities/manage-members/transfer-ownership/](https://help.zenodo.org/docs/communities/manage-members/transfer-ownership/): Transfer community ownership, covered only implicitly by communities.members; worth its own row.
- [help /docs/github/archive-software/manual-upload/](https://help.zenodo.org/docs/github/archive-software/manual-upload/): Manual software deposit, a deposit path with software metadata (custom_fields.code:*); no software-specific row.
- [help /guides/eu/submit/](https://help.zenodo.org/guides/eu/submit/): Direct EU submission vs via project community; EU-specific flows (eu_records_curation job, subcommunity checks) are only partly cataloged.
- [help /guides/nih/](https://help.zenodo.org/guides/nih/): NIH DMSP guidance (7 pages). Policy guidance, no app feature.
- [help /faq/](https://help.zenodo.org/faq/): FAQ (general, account, upload, sharing, communities, statistics, citations, content, GitHub, policies, API). No anchors, so features can only link to the whole page.
- [help /docs/about/whats-new/](https://help.zenodo.org/docs/about/whats-new/): Release notes for the RDM migration.
- [help /docs/about/whats-changed/](https://help.zenodo.org/docs/about/whats-changed/): Changes from legacy Zenodo.
- [developers #versioning](https://developers.zenodo.org/#versioning): API versioning policy.
- [developers #changes](https://developers.zenodo.org/#changes): API changelog.

**Docs that are outdated, incomplete or wrong against the code or the image:**
- [developers #rate-limiting](https://developers.zenodo.org/#rate-limiting) (differs from code): Docs say guests get 60/min and 2000/h and thumbnails 20/min; invenio.cfg sets RATELIMIT_GUEST_USER '8000 per hour;133 per minute' and the thumbnail endpoint 20 per second. Production may override this; check the deployed values.
- [developers #scopes](https://developers.zenodo.org/#scopes) (incomplete): Lists deposit:write and deposit:actions only; the app also offers user:email, tokens:generate and webhooks:event.
- [developers #available-metadata-formats](https://developers.zenodo.org/#available-metadata-formats) (incomplete): The image's ListMetadataFormats also offers marcxml, datacite4 and oai_datacite4, which aren't documented.
- [developers #changes](https://developers.zenodo.org/#changes) (outdated): Last entry is 2017-10-04, before the move to InvenioRDM; the RDM REST API (/api/records drafts, communities, requests, access) has no developer docs at all.
- [developers #records](https://developers.zenodo.org/#records) (outdated wording): Says 'Elasticsearch query string syntax'; search runs on OpenSearch (or ParadeDB on mini).
- [developers #records](https://developers.zenodo.org/#records) (unverified on mini): Documented status=draft and bounds= filters change nothing on the mini image (same total as no filter). Could be ParadeDB; check on OpenSearch.
- developers.zenodo.org (broken anchors): Section ids repeat (#list x4, #representation, #create, #retrieve, #update, #delete), so links to e.g. #list land on the first one.
- [help /docs/about/whats-changed/](https://help.zenodo.org/docs/about/whats-changed/) (broken link): Links to https://help.zenodo.org/deposit/ (404).
- [help /docs/about/](https://help.zenodo.org/docs/about/) (broken link): Links to a relative 'about.zenodo.org' (404); missing https://.

## Proof run

**Approach.** Playwright in `e2e/` on branch `feature-catalog`, for both kinds of checks: the browser for UI paths, and its `request` client for the REST, legacy and OAI-PMH APIs, so one runner, one report and one login setup cover both. `auth.setup.ts` waits for the fixtures, logs in both fixture users through the login form, and creates a personal token for each through the token settings page. Each test creates its own records, so runs don't depend on each other or on demo data. Test titles start with catalog IDs, and `npm run report` turns the JSON results into one status per ID.

**Run.** Image built from `mini-stack` 25fc388 in this orb, on a fresh volume, at 2026-11-22. The suite is at [`3747deb`](https://github.com/slint/zenodo-rdm/commit/3747deb). **37 of 37 tests pass, covering 25 catalog IDs, in 44 s** (once the fixtures are loaded).

| Area | IDs | Result |
|---|---|---|
| Accounts | `accounts.login`, `accounts.tokens`, `site.ready` | passing |
| Deposit UI | `deposit.ui.login-required`, `deposit.ui.publish` (form, upload, resource type, author modal, DOI question, publish), `deposit.ui.dashboard` | passing |
| Deposit API | `deposit.api.publish`, `.validation`, `.edit`, `.new-version`, `.delete-draft`, `deposit.permissions`, `deposit.restricted-files`, `deposit.legacy` | passing |
| Records | `records.landing`, `records.files.download`, `records.api.read`, `records.api.legacy-json`, `records.export` (13 formats), `records.citation` | passing |
| Search and OAI | `search.api`, `search.ui`, `search.sort-filter`, `oai.identify`, `oai.getrecord` | passing |

On the way to green, the failures were all wrong guesses in my tests (selectors, response shapes, the required publisher and DOI answer), and each now shows up as a finding in its area. The checks found no broken user path in these two areas. They did find the missing moderation index, the 500 on a legacy-format `PUT`, and the slow first start.

## Proposed split and continuous runs

**Split.** Each thread owns whole sections of this document and one spec file per section in `e2e/tests/`, so no two threads edit the same rows or files. All of them reuse `auth.setup.ts` and `lib/`. A thread that needs a new helper or fixture user adds it in its own file. Each runs its own mini container (its own volume) and records its status per row with the date and image commit.

| Thread | Owns (sections) | Spec files | Notes |
|---|---|---|---|
| 1 | Deposit (rest), Files and previews | `deposit.spec.ts`, `files.spec.ts` | Save, preview, community upload, PIDs, multipart, media files, embargo, quota, file modification, legacy actions, previewers, IIIF, zip |
| 2 | Communities, Requests and notifications | `communities.spec.ts`, `requests.spec.ts` | Needs a second plain user to play curator and submitter (create with `invenio users create` in setup). Emails come from the container log |
| 3 | Accounts and users, Access and sharing | `accounts.spec.ts`, `access.spec.ts` | Signup, confirm, reset (links from the log), sessions, profile, OAuth2 provider flow, share links, grants, access requests |
| 4 | Administration, Permissions and roles | `admin.spec.ts`, `permissions.spec.ts` | Role matrix anon/user/owner/curator/admin as table-driven tests. Owns the moderation findings |
| 5 | Search (rest), Stats and metrics, OAI-PMH/sitemap/static pages, Integrations | `search.spec.ts`, `stats.spec.ts`, `site.spec.ts`, `integrations.spec.ts` | Stats need tasks to run on demand (`docker exec ... invenio shell` calling the tasks). Mark ParadeDB-only differences in search |
| 6 | Background jobs, CLI | `jobs.spec.ts`, `cli.spec.ts` | Runs `docker exec <container> invenio ...` from Node and asserts the effect through HTTP |

Threads 1 to 5 are independent. Thread 6 overlaps with others' rows only by reference ("See `deposit.embargo`"), so it updates only its own rows.

**Continuous runs.**
- **Per PR:** a GitHub Actions job builds the mini image (cache the app image layers), starts it, waits for `site.ready`, runs `npx playwright test`, uploads the HTML report and traces, and fails the PR on any failing check. The first start is slow because of fixture loading. Two fixes help: bake a pre-initialised data volume into a `zenodo-mini-all:seeded` image on `master` pushes and start PR runs from it, or run the vocabulary fixtures synchronously in `wipe_recreate.sh` for the mini stack.
- **Nightly:** the same job on a schedule against `master` with the full suite, and `report.mjs` output posted to a run summary. An Amp thread subscribed to the workflow can then update the Status column of this document from the report, so the catalog stays current without anyone editing it by hand.
- **Agents for the gaps:** a scheduled Amp thread picks `untested` rows in its assigned sections, writes checks, and records results here. That keeps the catalog moving toward full coverage while CI keeps the covered rows honest.
