type ApiErrorDetailItem = {
  msg?: string;
};

type ApiErrorPayload = {
  detail?: string | ApiErrorDetailItem[];
};

export function getApiErrorMessage(payload: unknown, fallback: string): string {
  if (!payload || typeof payload !== "object") {
    return fallback;
  }

  const { detail } = payload as ApiErrorPayload;
  if (typeof detail === "string" && detail.trim()) {
    return detail;
  }

  if (Array.isArray(detail)) {
    const messages = detail
      .map((item) => {
        if (!item || typeof item !== "object") {
          return "";
        }
        return typeof item.msg === "string" ? item.msg : "";
      })
      .filter(Boolean);

    if (messages.length > 0) {
      return messages.join("\n");
    }
  }

  return fallback;
}
