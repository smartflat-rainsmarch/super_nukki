"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";
import ko from "@/lib/locales/ko.json";
import en from "@/lib/locales/en.json";

export const SUPPORTED_LOCALES = [
  "ko", "en", "ar", "bg", "bo", "ca", "ckb", "cs", "da", "de",
  "el", "eo", "es", "et", "fa", "fi", "fr", "he", "hr", "hu",
  "id", "it", "ja", "ka", "kk", "lt", "nl", "no", "nqo", "pl",
  "pt", "pt-BR", "ro", "ru", "rue", "sk", "sl", "sq", "sr", "sv",
  "ta", "th", "tl", "tr", "uk", "vi", "zh-CHT", "zh-CN",
] as const;

export type Locale = (typeof SUPPORTED_LOCALES)[number];

export const LOCALE_NAMES: Record<string, string> = {
  ko: "한국어", en: "English", ar: "العربية", bg: "Български", bo: "བོད་སྐད",
  ca: "Català", ckb: "کوردی", cs: "Čeština", da: "Dansk", de: "Deutsch",
  el: "Ελληνικά", eo: "Esperanto", es: "Español", et: "Eesti", fa: "فارسی",
  fi: "Suomi", fr: "Français", he: "עברית", hr: "Hrvatski", hu: "Magyar",
  id: "Bahasa Indonesia", it: "Italiano", ja: "日本語", ka: "ქართული", kk: "Қазақша",
  lt: "Lietuvių", nl: "Nederlands", no: "Norsk", nqo: "ߒߞߏ", pl: "Polski",
  pt: "Português", "pt-BR": "Português (BR)", ro: "Română", ru: "Русский",
  rue: "Русиньскый", sk: "Slovenčina", sl: "Slovenščina", sq: "Shqip",
  sr: "Српски", sv: "Svenska", ta: "தமிழ்", th: "ไทย", tl: "Tagalog",
  tr: "Türkçe", uk: "Українська", vi: "Tiếng Việt", "zh-CHT": "繁體中文", "zh-CN": "简体中文",
};

type Messages = Record<string, Record<string, string>>;

const BUNDLED: Record<string, Messages> = { ko, en };

const cache: Record<string, Messages> = { ko, en };

async function loadLocale(locale: string): Promise<Messages> {
  if (cache[locale]) return cache[locale];

  try {
    const mod = await import(`@/lib/locales/${locale}.json`);
    cache[locale] = mod.default;
    return mod.default;
  } catch {
    return ko;
  }
}

function getValue(messages: Messages, key: string): string {
  const parts = key.split(".");
  if (parts.length === 2) {
    return messages[parts[0]]?.[parts[1]] ?? "";
  }
  return "";
}

interface I18nContextValue {
  locale: string;
  setLocale: (locale: string) => void;
  t: (key: string) => string;
}

const I18nContext = createContext<I18nContextValue>({
  locale: "ko",
  setLocale: () => {},
  t: (key) => key,
});

export function useTranslation() {
  return useContext(I18nContext);
}

export function I18nProvider({ children }: { children: React.ReactNode }) {
  const [locale, setLocaleState] = useState("ko");
  const [messages, setMessages] = useState<Messages>(ko);

  useEffect(() => {
    const saved = localStorage.getItem("ui2psd_locale");
    if (saved && SUPPORTED_LOCALES.includes(saved as Locale)) {
      setLocaleState(saved);
      loadLocale(saved).then(setMessages);
    }
  }, []);

  const setLocale = useCallback((newLocale: string) => {
    setLocaleState(newLocale);
    localStorage.setItem("ui2psd_locale", newLocale);
    loadLocale(newLocale).then(setMessages);
  }, []);

  const t = useCallback(
    (key: string): string => {
      const val = getValue(messages, key);
      if (val) return val;
      return getValue(ko, key) || key;
    },
    [messages],
  );

  return (
    <I18nContext.Provider value={{ locale, setLocale, t }}>
      {children}
    </I18nContext.Provider>
  );
}
