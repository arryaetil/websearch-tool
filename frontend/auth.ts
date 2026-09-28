import { createHmac, createHash, timingSafeEqual } from "node:crypto";

export const SESSION_COOKIE = "kycx_session";
export const ADMIN_EMAIL = "admin@etil.nl";
const SESSION_SECONDS = 8 * 60 * 60;

function secret(): string | null {
  return process.env.KYCX_SESSION_SECRET && process.env.KYCX_ACCESS_PASSWORD
    ? process.env.KYCX_SESSION_SECRET
    : null;
}

export function authConfigured(): boolean {
  return Boolean(secret());
}

export function credentialsMatch(email: string, candidate: string): boolean {
  const expected = process.env.KYCX_ACCESS_PASSWORD;
  if (!expected || !secret()) return false;
  if (email.trim().toLowerCase() !== ADMIN_EMAIL) return false;
  const a = createHash("sha256").update(candidate).digest();
  const b = createHash("sha256").update(expected).digest();
  return timingSafeEqual(a, b);
}

export function createSession(): string {
  const key = secret();
  if (!key) throw new Error("KYCX authentication is not configured");
  const expires = String(Math.floor(Date.now() / 1000) + SESSION_SECONDS);
  const signature = createHmac("sha256", key).update(expires).digest("hex");
  return `${expires}.${signature}`;
}

export function validSession(value?: string): boolean {
  const key = secret();
  if (!key || !value) return false;
  const parts = value.split(".");
  if (parts.length !== 2 || !/^\d+$/.test(parts[0]) || !/^[a-f0-9]{64}$/.test(parts[1])) return false;
  const expires = Number(parts[0]);
  if (!Number.isSafeInteger(expires) || expires < Math.floor(Date.now() / 1000)) return false;
  const signature = createHmac("sha256", key).update(parts[0]).digest("hex");
  return timingSafeEqual(Buffer.from(parts[1], "hex"), Buffer.from(signature, "hex"));
}

export const sessionMaxAge = SESSION_SECONDS;
