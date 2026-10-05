/** User-facing description of GET /api/v1 cache validators. */
export function PublicApiValidatorCopy() {
  return (
    <>
      Responses send <code>ETag</code> and <code>Cache-Control</code>. <code>Last-Modified</code> is not sent. <code>If-Modified-Since</code> does not change the response. A 304 is returned only when <code>If-None-Match</code> matches the current body.
    </>
  );
}
