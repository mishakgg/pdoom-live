-- Transcript hosts are participants on a source item.
-- Canonical import schema 1.0.0 does not add host to its participant enum.
-- Staging writes the role directly so a host is not stored as a speaker or as the guest's blog.
ALTER TABLE source_participants DROP CONSTRAINT source_participants_role_check;
ALTER TABLE source_participants ADD CONSTRAINT source_participants_role_check
  CHECK (role IN ('author', 'speaker', 'guest', 'host', 'interviewer', 'publisher', 'mentioned'));
