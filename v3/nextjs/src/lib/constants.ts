export const DEFAULT_TENANT_ID = "default";
export const DEFAULT_USER_ID = "demo";
export const DEFAULT_SESSION_TITLE = "新对话";

/** Prior-turn cap sent to the LLM. Too long → cost + context pollution. */
export const MAX_HISTORY_MESSAGES = 12;

/** Upper bound on messages returned from the /messages list endpoint. */
export const MAX_MESSAGES_PER_SESSION_FETCH = 500;

/** Server-appended marker that tells the LLM (and the sticky-ingest
 *  detector) that the user just uploaded a file. Keep the string identical
 *  across writer/reader — a mismatch silently breaks the post-upload
 *  confirmation flow. */
export const UPLOAD_MARKER = "[文件已上传]";
export const UPLOAD_MARKER_PREFIX = `\n\n${UPLOAD_MARKER}`;
/** Matches the marker block server-side appended to the end of a user message. */
export const UPLOAD_MARKER_RE = /\n\n\[文件已上传\][^]*$/;
