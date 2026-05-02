import { createHash, randomBytes } from "crypto";

const KEY_PREFIX = "ocv3_";

export function generateApiKey(): { plaintext: string; hash: string } {
  const random = randomBytes(24).toString("base64url");
  const plaintext = `${KEY_PREFIX}${random}`;
  return { plaintext, hash: hashApiKey(plaintext) };
}

export function hashApiKey(plaintext: string): string {
  return createHash("sha256").update(plaintext).digest("hex");
}

export function keyDisplaySuffix(plaintext: string): string {
  return plaintext.slice(-4);
}
