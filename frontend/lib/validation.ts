/**
 * Client-side validation mirroring the backend Pydantic rules in
 * backend/schemas/server.py. These are UX helpers only — the backend remains
 * the authoritative validator.
 */

// IPv4 (with range check) or a basic IPv6 shape.
const IPV4 = /^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$/;
const IPV6 = /^(([0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}|::|([0-9a-fA-F]{1,4}:){1,7}:|(:[0-9a-fA-F]{1,4}){1,7}|([0-9a-fA-F]{1,4}:){1,6}:[0-9a-fA-F]{1,4}|([0-9a-fA-F]{1,4}:){1,5}(:[0-9a-fA-F]{1,4}){1,2}|([0-9a-fA-F]{1,4}:){1,4}(:[0-9a-fA-F]{1,4}){1,3}|([0-9a-fA-F]{1,4}:){1,3}(:[0-9a-fA-F]{1,4}){1,4}|([0-9a-fA-F]{1,4}:){1,2}(:[0-9a-fA-F]{1,4}){1,5}|[0-9a-fA-F]{1,4}:(:[0-9a-fA-F]{1,4}){1,6})$/;
const USERNAME = /^[A-Za-z_][A-Za-z0-9._-]{0,31}$/;

export function isValidIp(value: string): boolean {
  const v = value.trim();
  if (IPV4.test(v)) {
    return v.split(".").every((o) => {
      const n = Number(o);
      return n >= 0 && n <= 255 && String(n) === o.replace(/^0+(?=\d)/, "");
    });
  }
  return IPV6.test(v);
}

export function isValidPort(value: number | string): boolean {
  const n = Number(value);
  return Number.isInteger(n) && n >= 1 && n <= 65535;
}

export function isValidUsername(value: string): boolean {
  return USERNAME.test(value.trim());
}

export function isValidPemKey(value: string): boolean {
  return /-----BEGIN (?:[A-Z0-9 ]+ )?PRIVATE KEY-----[\s\S]*-----END (?:[A-Z0-9 ]+ )?PRIVATE KEY-----/.test(
    value.trim(),
  );
}

export function isValidWhitelist(value: string): boolean {
  const v = value.trim();
  if (!v) return true; // optional
  return v.split(",").every((entry) => {
    const item = entry.trim();
    if (!item) return false;
    const [addr] = item.split("/");
    return isValidIp(addr);
  });
}

export interface ServerFormValues {
  name: string;
  ip_address: string;
  ssh_port: number;
  ssh_username: string;
  ssh_auth_method: "password" | "key";
  ssh_password: string;
  ssh_key: string;
  ssh_key_only_mode: boolean;
  allowed_ip_whitelist: string;
}

/** Returns a map of field -> error message for any invalid inputs. */
export function validateServerForm(
  v: ServerFormValues,
  opts: { requireCredential?: boolean } = { requireCredential: true },
): Record<string, string> {
  const errors: Record<string, string> = {};
  if (!v.name.trim()) errors.name = "Server name is required.";
  if (!isValidIp(v.ip_address)) errors.ip_address = "Enter a valid IPv4 or IPv6 address.";
  if (!isValidPort(v.ssh_port)) errors.ssh_port = "Port must be between 1 and 65535.";
  if (!isValidUsername(v.ssh_username))
    errors.ssh_username =
      "1–32 chars; start with a letter/underscore; only letters, digits, '.', '_', '-'.";
  if (!isValidWhitelist(v.allowed_ip_whitelist))
    errors.allowed_ip_whitelist = "Comma-separated valid IPs or CIDR ranges.";

  if (v.ssh_auth_method === "password") {
    if (v.ssh_key_only_mode)
      errors.ssh_key_only_mode = "Key-only mode cannot be used with password auth.";
    if (opts.requireCredential && !v.ssh_password.trim())
      errors.ssh_password = "Password is required for password authentication.";
  } else {
    if (opts.requireCredential || v.ssh_key.trim()) {
      if (!isValidPemKey(v.ssh_key))
        errors.ssh_key = "Provide a valid PEM-format private key.";
    }
  }
  return errors;
}
