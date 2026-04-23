/** Extract the TOTP shared secret from an ``otpauth://`` provisioning URI (browser-safe, no ``new URL()``). */
export function totpSecretFromOtpauthUri(uri: string): string | null {
  const q = uri.indexOf("?");
  if (q === -1) return null;
  try {
    return new URLSearchParams(uri.slice(q + 1)).get("secret");
  } catch {
    return null;
  }
}
