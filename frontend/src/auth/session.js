const STORAGE_KEY = "rideshield.session";

export function readStoredSession() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export function writeStoredSession(value) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(value));
}

export function clearStoredSession() {
  localStorage.removeItem(STORAGE_KEY);
}

export function getStoredToken() {
  return readStoredSession()?.token || null;
}
