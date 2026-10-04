# Interface request for Agent 1

Owner of this request: public HTTP/API (Agent 6). Do not treat this file as a license to edit `apps/web/app/data/page.tsx` from the API branch.

## What changed

`GET /api/v1/...` no longer sends `Last-Modified`. Dataset import time is not a validator. `If-Modified-Since` is ignored. A strong `ETag` is the SHA-256 of the response body. `Cache-Control` is unchanged: `public, max-age=60, stale-while-revalidate=300`.

The contract is `docs/PUBLIC_API.md`.

## Copy to replace

`apps/web/app/data/page.tsx` still says responses send `Last-Modified` from the dataset import time. That sentence is now false.

Replace it with: responses send `ETag` and `Cache-Control`. `Last-Modified` is not sent. `If-Modified-Since` does not change the response. A 304 is returned only when `If-None-Match` matches the current body.

## Not requested

Do not change review visibility, pagination, or the data page's other claims. Server-rendered pages do not use this HTTP cache. If a page query hits the snapshot admission limit, the existing accessible error page is the current behavior; a dedicated retry message is optional and not required for the API change.
